import re
import time
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Annotated, Literal
from uuid import uuid4

from fastapi import FastAPI, Path, Query, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from ytsponsorskip.config import Settings, get_settings
from ytsponsorskip.detection_service import DetectionService
from ytsponsorskip.detector import Sensitivity
from ytsponsorskip.domain import FailureCode, TranscriptAcquisitionError
from ytsponsorskip.providers.saved import SavedTuneTranscriptProvider
from ytsponsorskip.providers.supadata import SupadataTranscriptProvider
from ytsponsorskip.providers.youtube import YouTubeTranscriptProvider
from ytsponsorskip.schemas import (
    AcquisitionResponse,
    DetectedIntervalResponse,
    DetectionResponse,
    ErrorDetails,
    ErrorResponse,
    HealthResponse,
    TimingMetricsResponse,
    TranscriptMetadataResponse,
    TranscriptSnippetResponse,
)
from ytsponsorskip.service import SlidingWindowRateLimiter, TranscriptService
from ytsponsorskip.trial_budget import BudgetedTranscriptProvider, TrialBudget

REQUEST_ID_PATTERN = re.compile(r"^[A-Za-z0-9_-]{1,64}$")


def _request_id(request: Request) -> str:
    return getattr(request.state, "request_id", "unknown")


def _error_response(
    request: Request,
    *,
    status_code: int,
    code: str,
    message: str,
    retryable: bool,
) -> JSONResponse:
    body = ErrorResponse(
        error=ErrorDetails(
            code=code,
            message=message,
            retryable=retryable,
            request_id=_request_id(request),
        )
    )
    return JSONResponse(status_code=status_code, content=body.model_dump())


def create_app(
    *,
    settings: Settings | None = None,
    transcript_service: TranscriptService | None = None,
    detection_service: DetectionService | None = None,
) -> FastAPI:
    settings = settings or get_settings()
    owns_service = transcript_service is None
    if transcript_service is None:
        budget = TrialBudget(
            settings.trial_budget_path,
            limit=settings.trial_attempt_limit,
            max_polls=settings.trial_poll_limit,
        )
        if settings.transcript_provider == "supadata":
            if settings.environment != "local":
                raise ValueError("Supadata trial provider is available locally only")
            if settings.supadata_api_key is None:
                raise ValueError("SUPADATA_API_KEY is required for the Supadata provider")
            provider = SupadataTranscriptProvider(
                settings.supadata_api_key.get_secret_value(),
                total_timeout_seconds=settings.request_timeout_seconds,
                per_request_timeout_seconds=settings.request_timeout_seconds,
                max_polls=settings.trial_poll_limit,
                trial_budget=budget,
                enforce_free_credits=True,
            )
        else:
            provider = BudgetedTranscriptProvider(
                YouTubeTranscriptProvider(timeout_seconds=settings.request_timeout_seconds),
                budget,
                source="youtube-transcript-api",
            )
        transcript_service = TranscriptService(
            provider,
            max_concurrent=settings.max_concurrent_acquisitions,
            timeout_seconds=settings.request_timeout_seconds,
            cache_ttl_seconds=settings.cache_ttl_seconds,
            cache_max_entries=settings.cache_max_entries,
        )
    owns_detection_service = detection_service is None
    if detection_service is None:
        detection_sources = {}
        if settings.environment == "local":
            detection_sources["saved"] = TranscriptService(
                SavedTuneTranscriptProvider(),
                max_concurrent=settings.max_concurrent_acquisitions,
                timeout_seconds=settings.request_timeout_seconds,
                cache_ttl_seconds=settings.cache_ttl_seconds,
                cache_max_entries=settings.cache_max_entries,
            )
            if settings.supadata_api_key is not None:
                detection_sources["supadata"] = TranscriptService(
                    SupadataTranscriptProvider(
                        settings.supadata_api_key.get_secret_value(),
                        total_timeout_seconds=settings.request_timeout_seconds,
                        per_request_timeout_seconds=settings.request_timeout_seconds,
                        max_polls=settings.trial_poll_limit,
                        trial_budget=budget
                        if owns_service
                        else TrialBudget(
                            settings.trial_budget_path,
                            limit=settings.trial_attempt_limit,
                            max_polls=settings.trial_poll_limit,
                        ),
                        enforce_free_credits=True,
                    ),
                    max_concurrent=settings.max_concurrent_acquisitions,
                    timeout_seconds=settings.request_timeout_seconds,
                    cache_ttl_seconds=settings.cache_ttl_seconds,
                    cache_max_entries=settings.cache_max_entries,
                )
        detection_service = DetectionService(
            detection_sources,
            cache_ttl_seconds=settings.cache_ttl_seconds,
            cache_max_entries=settings.cache_max_entries,
            max_concurrent=settings.max_concurrent_acquisitions,
            timeout_seconds=settings.request_timeout_seconds,
            detector_variant=settings.detector_variant,
        )
    limiter = SlidingWindowRateLimiter(settings.request_limit_per_minute)

    @asynccontextmanager
    async def lifespan(_: FastAPI) -> AsyncIterator[None]:
        yield
        if owns_service:
            transcript_service.close()
        if owns_detection_service:
            detection_service.close()

    app = FastAPI(
        title="YTSponsorSkip Transcript API",
        version="0.1.0",
        lifespan=lifespan,
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.allowed_origins,
        allow_credentials=False,
        allow_methods=["GET"],
        allow_headers=["Authorization", "Content-Type", "X-Request-ID"],
    )

    @app.middleware("http")
    async def request_controls(request: Request, call_next):  # type: ignore[no-untyped-def]
        supplied_request_id = request.headers.get("x-request-id", "")
        request.state.request_id = (
            supplied_request_id
            if REQUEST_ID_PATTERN.fullmatch(supplied_request_id)
            else uuid4().hex
        )

        if request.url.path.startswith(("/api/v1/transcripts", "/api/v1/detections")):
            if settings.api_token:
                expected = f"Bearer {settings.api_token}"
                if request.headers.get("authorization") != expected:
                    return _error_response(
                        request,
                        status_code=401,
                        code="UNAUTHORIZED",
                        message="A valid API token is required.",
                        retryable=False,
                    )
            if not await limiter.allow():
                return _error_response(
                    request,
                    status_code=429,
                    code="RATE_LIMITED",
                    message="The backend request limit has been reached.",
                    retryable=True,
                )

        response = await call_next(request)
        response.headers["X-Request-ID"] = request.state.request_id
        return response

    @app.exception_handler(TranscriptAcquisitionError)
    async def transcript_error_handler(
        request: Request, error: TranscriptAcquisitionError
    ) -> JSONResponse:
        not_found_codes = {
            FailureCode.TRANSCRIPTS_DISABLED,
            FailureCode.NO_MATCHING_TRANSCRIPT,
            FailureCode.VIDEO_UNAVAILABLE,
            FailureCode.AGE_RESTRICTED,
        }
        if error.code is FailureCode.INVALID_VIDEO_ID:
            status_code = 422
        else:
            status_code = 404 if error.code in not_found_codes else 503
        return _error_response(
            request,
            status_code=status_code,
            code=error.code,
            message=error.public_message,
            retryable=error.retryable,
        )

    @app.exception_handler(RequestValidationError)
    async def validation_error_handler(request: Request, _: RequestValidationError) -> JSONResponse:
        return _error_response(
            request,
            status_code=422,
            code="INVALID_REQUEST",
            message="The request did not match the API contract.",
            retryable=False,
        )

    @app.get("/health", response_model=HealthResponse)
    async def health() -> HealthResponse:
        return HealthResponse(status="ok", environment=settings.environment)

    @app.get(
        "/api/v1/transcripts/{video_id}",
        response_model=AcquisitionResponse,
        responses={
            404: {"model": ErrorResponse},
            422: {"model": ErrorResponse},
            503: {"model": ErrorResponse},
        },
    )
    async def get_transcript(
        request: Request,
        video_id: Annotated[
            str,
            Path(min_length=1, max_length=32, pattern=r"^[A-Za-z0-9_-]+$"),
        ],
        languages: Annotated[list[str] | None, Query(min_length=1, max_length=3)] = None,
    ) -> AcquisitionResponse:
        language_codes = languages or ["en"]
        if any(
            not re.fullmatch(r"[A-Za-z]{2,3}(?:-[A-Za-z]{2,4})?", code) for code in language_codes
        ):
            return _error_response(  # type: ignore[return-value]
                request,
                status_code=422,
                code="INVALID_REQUEST",
                message="Language codes must use forms such as 'en' or 'en-US'.",
                retryable=False,
            )

        outcome = await transcript_service.fetch(video_id, language_codes)
        transcript = outcome.transcript
        return AcquisitionResponse(
            video_id=transcript.video_id,
            request_id=_request_id(request),
            transcript=TranscriptMetadataResponse(
                language=transcript.language,
                language_code=transcript.language_code,
                is_generated=transcript.is_generated,
                provider=transcript.provider,
                provider_version=transcript.provider_version,
            ),
            snippets=[
                TranscriptSnippetResponse(
                    index=snippet.index,
                    text=snippet.text,
                    start_seconds=snippet.start_seconds,
                    duration_seconds=snippet.duration_seconds,
                )
                for snippet in transcript.snippets
            ],
            provider_latency_ms=outcome.provider_latency_ms,
            cache_hit=outcome.cache_hit,
            coalesced=outcome.coalesced,
            timing=TimingMetricsResponse(
                snippet_count=outcome.timing.snippet_count,
                median_snippet_duration_seconds=(outcome.timing.median_snippet_duration_seconds),
                median_start_gap_seconds=outcome.timing.median_start_gap_seconds,
                overlapping_snippet_count=outcome.timing.overlapping_snippet_count,
                covered_span_seconds=outcome.timing.covered_span_seconds,
            ),
        )

    @app.get(
        "/api/v1/detections/{video_id}",
        response_model=DetectionResponse,
        responses={
            404: {"model": ErrorResponse},
            422: {"model": ErrorResponse},
            503: {"model": ErrorResponse},
        },
    )
    async def get_detection(
        request: Request,
        video_id: Annotated[
            str, Path(min_length=11, max_length=11, pattern=r"^[A-Za-z0-9_-]{11}$")
        ],
        mode: Annotated[Sensitivity, Query()],
        source: Annotated[Literal["saved", "supadata"], Query()],
    ) -> DetectionResponse:
        supplied_id = request.headers.get("x-request-id", "")
        if not REQUEST_ID_PATTERN.fullmatch(supplied_id):
            return _error_response(  # type: ignore[return-value]
                request,
                status_code=422,
                code="INVALID_REQUEST",
                message="A valid X-Request-ID header is required for detection.",
                retryable=False,
            )
        started = time.perf_counter()
        outcome = await detection_service.detect(video_id, source, mode)
        transcript = outcome.acquisition.transcript
        intervals = []
        for item in outcome.detection.intervals:
            if item.start_seconds < 0 or item.end_seconds <= item.start_seconds:
                raise TranscriptAcquisitionError(
                    FailureCode.PROVIDER_ERROR,
                    "Detection returned an invalid interval; preview is unavailable.",
                    retryable=False,
                )
            intervals.append(
                DetectedIntervalResponse(
                    start_seconds=item.start_seconds,
                    end_seconds=item.end_seconds,
                    heuristic_score=item.score,
                    evidence=list(item.evidence),
                    snippet_indices=list(item.snippet_indices),
                    auto_skip_eligible=item.end_seconds - item.start_seconds > 3,
                )
            )
        return DetectionResponse(
            video_id=video_id,
            request_id=supplied_id,
            mode=mode.value,
            transcript_source=source,
            transcript_provider=transcript.provider,
            transcript_sha256=outcome.transcript_sha256,
            detector_version=outcome.detector_version,
            language_code=transcript.language_code,
            caption_type=(
                "generated"
                if transcript.is_generated is True
                else "manual"
                if transcript.is_generated is False
                else "unknown"
            ),
            timing_provenance=(
                "derived_analysis_spans_not_exact_speech_boundaries"
                if source == "saved"
                else "source_cue_duration_ms_converted_to_seconds_not_exact_speech_boundaries"
            ),
            intervals=intervals,
            window_count=outcome.detection.window_count,
            transcript_cache_hit=outcome.acquisition.cache_hit,
            transcript_coalesced=outcome.acquisition.coalesced,
            detection_cache_hit=outcome.detection_cache_hit,
            detection_coalesced=outcome.detection_coalesced,
            provider_latency_ms=outcome.acquisition.provider_latency_ms,
            detection_latency_ms=outcome.detection_latency_ms,
            total_latency_ms=(time.perf_counter() - started) * 1000,
        )

    return app


app = create_app()
