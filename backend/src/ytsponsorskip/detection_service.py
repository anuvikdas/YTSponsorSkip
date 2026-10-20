"""Shared transcript-to-predictions pipeline; no labels or playback side effects."""

import asyncio
import hashlib
import json
import math
import time
from collections import OrderedDict
from dataclasses import dataclass
from pathlib import Path

from ytsponsorskip.detector import DetectionResult, PromotionDetector, Sensitivity
from ytsponsorskip.domain import FailureCode, Transcript, TranscriptAcquisitionError
from ytsponsorskip.service import AcquisitionOutcome, TranscriptService

DETECTOR_PATH = Path(__file__).with_name("detector.py")


def transcript_identity(transcript: Transcript) -> str:
    """Hash exact source metadata, original text, order and timing—not labels."""
    value = {
        "video_id": transcript.video_id,
        "language_code": transcript.language_code,
        "provider": transcript.provider,
        "provider_version": transcript.provider_version,
        "snippets": [
            [cue.index, cue.text, cue.start_seconds, cue.duration_seconds]
            for cue in transcript.snippets
        ],
    }
    return hashlib.sha256(
        json.dumps(value, ensure_ascii=False, separators=(",", ":"), allow_nan=False).encode()
    ).hexdigest()


def validate_transcript(transcript: Transcript, video_id: str) -> None:
    """Fail closed even if a new provider bypasses its own response-shape checks."""
    if (
        transcript.video_id != video_id
        or not transcript.snippets
        or not isinstance(transcript.language_code, str)
        or not transcript.language_code.lower().startswith("en")
    ):
        raise TranscriptAcquisitionError(
            FailureCode.UPSTREAM_CHANGED,
            "The transcript provider returned invalid video data.",
            retryable=False,
        )
    previous_start = -1.0
    for position, cue in enumerate(transcript.snippets):
        if (
            type(cue.index) is not int
            or cue.index != position
            or not isinstance(cue.text, str)
            or not cue.text.strip()
            or isinstance(cue.start_seconds, bool)
            or isinstance(cue.duration_seconds, bool)
            or not isinstance(cue.start_seconds, (int, float))
            or not isinstance(cue.duration_seconds, (int, float))
            or not math.isfinite(cue.start_seconds)
            or not math.isfinite(cue.duration_seconds)
            or cue.start_seconds < previous_start
            or cue.start_seconds < 0
            or cue.duration_seconds < 0
        ):
            raise TranscriptAcquisitionError(
                FailureCode.UPSTREAM_CHANGED,
                "The transcript provider returned malformed timed cues.",
                retryable=False,
            )
        previous_start = cue.start_seconds


@dataclass(frozen=True, slots=True)
class DetectionOutcome:
    acquisition: AcquisitionOutcome
    detection: DetectionResult
    transcript_sha256: str
    detector_version: str
    detection_cache_hit: bool
    detection_coalesced: bool
    detection_latency_ms: float | None


class DetectionService:
    def __init__(
        self,
        sources: dict[str, TranscriptService],
        *,
        cache_ttl_seconds: int = 900,
        cache_max_entries: int = 128,
        max_concurrent: int = 4,
        timeout_seconds: float = 30,
    ) -> None:
        self.sources = sources
        self.detector = PromotionDetector()
        self.detector_version = (
            "rules-sha256:" + hashlib.sha256(DETECTOR_PATH.read_bytes()).hexdigest()[:16]
        )
        self._ttl = cache_ttl_seconds
        self._max_entries = cache_max_entries
        self._semaphore = asyncio.Semaphore(max_concurrent)
        self._timeout = timeout_seconds
        self._lock = asyncio.Lock()
        self._cache: OrderedDict[tuple[str, str, str], tuple[float, DetectionResult]] = (
            OrderedDict()
        )
        self._in_flight: dict[
            tuple[str, str, str], asyncio.Task[tuple[DetectionResult, float]]
        ] = {}

    async def detect(self, video_id: str, source: str, mode: Sensitivity) -> DetectionOutcome:
        service = self.sources.get(source)
        if service is None:
            raise TranscriptAcquisitionError(
                FailureCode.PROVIDER_ERROR,
                "This transcript source is not configured locally; preview is unavailable.",
                retryable=False,
            )
        acquisition = await service.fetch(video_id, ["en"])
        transcript = acquisition.transcript
        validate_transcript(transcript, video_id)
        digest = transcript_identity(transcript)
        key = (digest, self.detector_version, mode.value)
        async with self._lock:
            cached = self._cache.get(key)
            if cached and cached[0] > time.monotonic():
                self._cache.move_to_end(key)
                return DetectionOutcome(
                    acquisition, cached[1], digest, self.detector_version, True, False, None
                )
            if cached:
                del self._cache[key]
            task = self._in_flight.get(key)
            coalesced = task is not None
            if task is None:
                task = asyncio.create_task(self._detect_uncached(key, transcript, mode))
                self._in_flight[key] = task
        detection, latency_ms = await asyncio.shield(task)
        return DetectionOutcome(
            acquisition, detection, digest, self.detector_version, False, coalesced, latency_ms
        )

    async def _detect_uncached(self, key, transcript, mode):
        try:
            async with self._semaphore:
                started = time.perf_counter()
                try:
                    result = await asyncio.wait_for(
                        asyncio.to_thread(self.detector.detect, transcript, mode),
                        timeout=self._timeout,
                    )
                except TimeoutError as error:
                    raise TranscriptAcquisitionError(
                        FailureCode.ACQUISITION_TIMEOUT,
                        "Detection timed out; preview is unavailable.",
                        retryable=True,
                    ) from error
                except Exception as error:
                    raise TranscriptAcquisitionError(
                        FailureCode.PROVIDER_ERROR,
                        "Detection failed; preview is unavailable.",
                        retryable=False,
                    ) from error
                latency_ms = (time.perf_counter() - started) * 1000
            if self._ttl > 0:
                async with self._lock:
                    self._cache[key] = (time.monotonic() + self._ttl, result)
                    self._cache.move_to_end(key)
                    while len(self._cache) > self._max_entries:
                        self._cache.popitem(last=False)
            return result, latency_ms
        finally:
            async with self._lock:
                if self._in_flight.get(key) is asyncio.current_task():
                    del self._in_flight[key]

    def close(self) -> None:
        for service in {id(value): value for value in self.sources.values()}.values():
            service.close()
