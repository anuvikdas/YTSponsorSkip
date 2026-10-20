"""Native-caption Supadata client; selectable only after a bounded local probe."""

import math
import re
import time
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any

import requests

from ytsponsorskip.domain import (
    FailureCode,
    Transcript,
    TranscriptAcquisitionError,
    TranscriptSnippet,
)
from ytsponsorskip.trial_budget import TrialBudget

API_ROOT = "https://api.supadata.ai/v1"
VIDEO_ID = re.compile(r"^[A-Za-z0-9_-]{11}$")
JOB_ID = re.compile(r"^[A-Za-z0-9_-]{1,128}$")


@dataclass(frozen=True)
class SupadataObservation:
    phase: str
    status_code: int
    billable_requests: str | None
    body: Any


@dataclass(frozen=True)
class SupadataFetch:
    transcript: Transcript
    observations: tuple[SupadataObservation, ...]
    latency_ms: float


class SupadataProbeError(TranscriptAcquisitionError):
    def __init__(
        self,
        code: FailureCode,
        message: str,
        *,
        retryable: bool,
        observations: Sequence[SupadataObservation],
    ) -> None:
        super().__init__(code, message, retryable=retryable)
        self.observations = tuple(observations)


def normalize_native_transcript(body: Any, video_id: str) -> Transcript:
    """Keep original cue order/text/timing; only convert documented ms units to seconds."""
    if not isinstance(body, dict):
        raise ValueError("response is not an object")
    language = body.get("lang")
    if not isinstance(language, str) or not re.fullmatch(r"en(?:-[A-Za-z0-9]+)*", language, re.I):
        raise LookupError("returned transcript language is not English")
    content = body.get("content")
    if not isinstance(content, list) or not content:
        raise ValueError("content is not a nonempty timed-cue array")
    cues = []
    previous_start = -1.0
    for index, chunk in enumerate(content):
        if not isinstance(chunk, dict):
            raise ValueError("cue is not an object")
        text = chunk.get("text")
        start_ms, duration_ms = chunk.get("offset"), chunk.get("duration")
        chunk_language = chunk.get("lang")
        if chunk_language is not None and (
            not isinstance(chunk_language, str)
            or not re.fullmatch(r"en(?:-[A-Za-z0-9]+)*", chunk_language, re.I)
        ):
            raise LookupError("a cue language is not English")
        if (
            not isinstance(text, str)
            or not text.strip()
            or isinstance(start_ms, bool)
            or isinstance(duration_ms, bool)
            or not isinstance(start_ms, (int, float))
            or not isinstance(duration_ms, (int, float))
            or not math.isfinite(start_ms)
            or not math.isfinite(duration_ms)
            or start_ms < 0
            or duration_ms < 0
            or start_ms < previous_start
        ):
            raise ValueError("cue text or timing is invalid")
        previous_start = start_ms
        cues.append(TranscriptSnippet(index, text, start_ms / 1000, duration_ms / 1000))
    return Transcript(
        video_id=video_id,
        language="English",
        language_code=language,
        is_generated=None,
        snippets=tuple(cues),
        provider="supadata-native",
        provider_version="v1-http-2026-10-19",
    )


class SupadataTranscriptProvider:
    """Synchronous adapter for TranscriptService's bounded worker pool."""

    name = "supadata-native"

    def __init__(
        self,
        api_key: str,
        *,
        total_timeout_seconds: float = 30,
        poll_interval_seconds: float = 1,
        max_polls: int = 20,
        per_request_timeout_seconds: float = 5,
        trial_budget: TrialBudget | None = None,
        enforce_free_credits: bool = False,
        session: requests.Session | None = None,
    ) -> None:
        if not api_key:
            raise ValueError("SUPADATA_API_KEY is required")
        if (
            total_timeout_seconds <= 0
            or poll_interval_seconds <= 0
            or max_polls < 1
            or per_request_timeout_seconds <= 0
        ):
            raise ValueError("polling limits must be positive")
        self._session = session or requests.Session()
        self._session.headers.update({"x-api-key": api_key})
        self._total_timeout_seconds = total_timeout_seconds
        self._poll_interval_seconds = poll_interval_seconds
        self._max_polls = max_polls
        self._per_request_timeout_seconds = per_request_timeout_seconds
        self._trial_budget = trial_budget
        self._enforce_free_credits = enforce_free_credits

    def fetch(self, video_id: str, preferred_languages: Sequence[str]) -> Transcript:
        return self.fetch_with_observations(video_id, preferred_languages).transcript

    def fetch_with_observations(
        self, video_id: str, preferred_languages: Sequence[str]
    ) -> SupadataFetch:
        observations: list[SupadataObservation] = []

        def fail(code: FailureCode, message: str, retryable: bool = False):
            raise SupadataProbeError(code, message, retryable=retryable, observations=observations)

        if not VIDEO_ID.fullmatch(video_id):
            fail(FailureCode.INVALID_VIDEO_ID, "The supplied YouTube video ID is invalid.")
        if not preferred_languages or not preferred_languages[0].lower().startswith("en"):
            fail(FailureCode.NO_MATCHING_TRANSCRIPT, "Supadata probe supports English only.")
        if self._enforce_free_credits:
            self._check_free_credit()
        attempt_id = (
            self._trial_budget.reserve_attempt(video_id, self.name)
            if self._trial_budget is not None
            else None
        )
        started = time.monotonic()
        deadline = started + self._total_timeout_seconds

        def get(url: str, *, phase: str, params: dict[str, str] | None = None):
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                fail(FailureCode.ACQUISITION_TIMEOUT, "Supadata acquisition timed out.", True)
            try:
                response = self._session.get(
                    url, params=params, timeout=min(self._per_request_timeout_seconds, remaining)
                )
            except requests.Timeout:
                fail(FailureCode.ACQUISITION_TIMEOUT, "Supadata request timed out.", True)
            except requests.RequestException:
                fail(FailureCode.PROVIDER_ERROR, "Supadata could not be reached.", True)
            try:
                body = response.json()
            except ValueError:
                body = {"unparseable_body": True, "body_excerpt": response.text[:50_000]}
            observations.append(
                SupadataObservation(
                    phase,
                    response.status_code,
                    response.headers.get("x-billable-requests"),
                    body,
                )
            )
            return response.status_code, body

        status, body = get(
            f"{API_ROOT}/transcript",
            phase="initial",
            params={
                "url": f"https://www.youtube.com/watch?v={video_id}",
                "lang": "en",
                "text": "false",
                "mode": "native",
            },
        )
        polls = 0
        job_id = body.get("jobId") if status == 202 and isinstance(body, dict) else None
        while status == 202:
            if not isinstance(job_id, str) or not JOB_ID.fullmatch(job_id):
                fail(FailureCode.UPSTREAM_CHANGED, "Supadata returned an invalid job ID.")
            if polls >= self._max_polls:
                fail(FailureCode.ACQUISITION_TIMEOUT, "Supadata polling limit reached.", True)
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                fail(FailureCode.ACQUISITION_TIMEOUT, "Supadata acquisition timed out.", True)
            time.sleep(min(self._poll_interval_seconds, remaining))
            if self._trial_budget is not None and attempt_id is not None:
                self._trial_budget.reserve_poll(attempt_id)
            polls += 1
            status, body = get(f"{API_ROOT}/transcript/{job_id}", phase="poll")
            if status == 200 and isinstance(body, dict):
                job_status = body.get("status")
                if job_status in ("queued", "active"):
                    status = 202
                    continue
                if job_status == "failed":
                    self._fail_http(body.get("error", {}), 200, fail)
                if job_status != "completed":
                    fail(FailureCode.UPSTREAM_CHANGED, "Supadata returned an unknown job status.")
                break

        if status != 200:
            self._fail_http(body, status, fail)
        try:
            transcript = normalize_native_transcript(body, video_id)
        except LookupError:
            fail(FailureCode.NO_MATCHING_TRANSCRIPT, "Supadata returned a non-English transcript.")
        except ValueError:
            fail(FailureCode.UPSTREAM_CHANGED, "Supadata returned unusable timed captions.")
        return SupadataFetch(
            transcript=transcript,
            observations=tuple(observations),
            latency_ms=round((time.monotonic() - started) * 1000, 3),
        )

    def _check_free_credit(self) -> None:
        """Local API use fails closed if the free plan or one available credit cannot be shown."""
        try:
            response = self._session.get(f"{API_ROOT}/me", timeout=5)
            body = response.json()
            plan = body.get("plan") if isinstance(body, dict) else None
            maximum = body.get("maxCredits") if isinstance(body, dict) else None
            used = body.get("usedCredits") if isinstance(body, dict) else None
            valid = (
                response.status_code == 200
                and isinstance(plan, str)
                and any(word in plan.lower() for word in ("free", "trial"))
                and isinstance(maximum, (int, float))
                and not isinstance(maximum, bool)
                and isinstance(used, (int, float))
                and not isinstance(used, bool)
                and math.isfinite(maximum)
                and math.isfinite(used)
                and maximum - used >= 1
            )
        except (requests.RequestException, ValueError, TypeError):
            valid = False
        if not valid:
            raise TranscriptAcquisitionError(
                FailureCode.PROVIDER_ERROR,
                "A free Supadata credit could not be confirmed; acquisition was not started.",
                retryable=False,
            )

    @staticmethod
    def _fail_http(body: Any, status: int, fail):
        code = body.get("error") if isinstance(body, dict) else None
        if isinstance(code, dict):
            code = code.get("error")
        if code == "transcript-unavailable" or status == 206:
            fail(FailureCode.NO_MATCHING_TRANSCRIPT, "Supadata has no native transcript.")
        if code == "not-found" or status == 404:
            fail(FailureCode.VIDEO_UNAVAILABLE, "Supadata could not find the video.")
        if status == 429 or code == "limit-exceeded":
            fail(FailureCode.PROVIDER_ERROR, "Supadata rate or credit limit reached.")
        if status == 401 or code == "unauthorized":
            fail(FailureCode.PROVIDER_ERROR, "Supadata authentication failed.")
        if status == 403 or code == "forbidden":
            fail(FailureCode.VIDEO_UNAVAILABLE, "Supadata cannot access the video.")
        fail(FailureCode.PROVIDER_ERROR, "Supadata request failed.", status >= 500)
