import re
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Annotated
from uuid import uuid4

from fastapi import FastAPI, Path, Query, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from ytsponsorskip.config import Settings, get_settings
from ytsponsorskip.domain import FailureCode, TranscriptAcquisitionError
from ytsponsorskip.providers.youtube import YouTubeTranscriptProvider
from ytsponsorskip.schemas import (
    AcquisitionResponse,
    ErrorDetails,
    ErrorResponse,
    HealthResponse,
    TimingMetricsResponse,
    TranscriptMetadataResponse,
    TranscriptSnippetResponse,
)
from ytsponsorskip.service import SlidingWindowRateLimiter, TranscriptService

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
) -> FastAPI:
    settings = settings or get_settings()
    owns_service = transcript_service is None
    if transcript_service is None:
        provider = YouTubeTranscriptProvider(timeout_seconds=settings.request_timeout_seconds)
        transcript_service = TranscriptService(
            provider,
            max_concurrent=settings.max_concurrent_acquisitions,
            timeout_seconds=settings.request_timeout_seconds,
            cache_ttl_seconds=settings.cache_ttl_seconds,
            cache_max_entries=settings.cache_max_entries,
        )
    limiter = SlidingWindowRateLimiter(settings.request_limit_per_minute)

    @asynccontextmanager
    async def lifespan(_: FastAPI) -> AsyncIterator[None]:
        yield
        if owns_service:
            transcript_service.close()

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

        if request.url.path.startswith("/api/v1/transcripts"):
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
        responses={404: {"model": ErrorResponse}, 503: {"model": ErrorResponse}},
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

    return app


app = create_app()
