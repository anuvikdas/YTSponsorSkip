import asyncio
import time
from collections import OrderedDict, deque
from collections.abc import Sequence
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from statistics import median

from ytsponsorskip.domain import FailureCode, Transcript, TranscriptAcquisitionError
from ytsponsorskip.providers.base import TranscriptProvider


@dataclass(frozen=True, slots=True)
class TimingMetrics:
    snippet_count: int
    median_snippet_duration_seconds: float | None
    median_start_gap_seconds: float | None
    overlapping_snippet_count: int
    covered_span_seconds: float


@dataclass(frozen=True, slots=True)
class AcquisitionOutcome:
    transcript: Transcript
    provider_latency_ms: float | None
    cache_hit: bool
    coalesced: bool
    timing: TimingMetrics


@dataclass(frozen=True, slots=True)
class _CachedValue:
    expires_at: float
    transcript: Transcript


def calculate_timing_metrics(transcript: Transcript) -> TimingMetrics:
    snippets = transcript.snippets
    if not snippets:
        return TimingMetrics(0, None, None, 0, 0.0)

    durations = [snippet.duration_seconds for snippet in snippets]
    start_gaps = [
        current.start_seconds - previous.start_seconds
        for previous, current in zip(snippets, snippets[1:], strict=False)
    ]
    overlap_count = sum(
        current.start_seconds < previous.end_seconds
        for previous, current in zip(snippets, snippets[1:], strict=False)
    )
    covered_span = max(snippet.end_seconds for snippet in snippets) - min(
        snippet.start_seconds for snippet in snippets
    )
    return TimingMetrics(
        snippet_count=len(snippets),
        median_snippet_duration_seconds=median(durations),
        median_start_gap_seconds=median(start_gaps) if start_gaps else None,
        overlapping_snippet_count=overlap_count,
        covered_span_seconds=covered_span,
    )


class TranscriptService:
    """Adds bounded concurrency, request coalescing, and a TTL cache to a provider."""

    def __init__(
        self,
        provider: TranscriptProvider,
        *,
        max_concurrent: int,
        timeout_seconds: float,
        cache_ttl_seconds: int,
        cache_max_entries: int,
    ) -> None:
        self._provider = provider
        self._timeout_seconds = timeout_seconds
        self._cache_ttl_seconds = cache_ttl_seconds
        self._cache_max_entries = cache_max_entries
        self._semaphore = asyncio.Semaphore(max_concurrent)
        self._executor = ThreadPoolExecutor(
            max_workers=max_concurrent,
            thread_name_prefix="transcript-provider",
        )
        self._lock = asyncio.Lock()
        self._cache: OrderedDict[tuple[str, tuple[str, ...]], _CachedValue] = OrderedDict()
        self._in_flight: dict[
            tuple[str, tuple[str, ...]], asyncio.Task[tuple[Transcript, float]]
        ] = {}

    async def fetch(self, video_id: str, preferred_languages: Sequence[str]) -> AcquisitionOutcome:
        key = (video_id, tuple(preferred_languages))
        now = time.monotonic()

        async with self._lock:
            cached = self._cache.get(key)
            if cached is not None and cached.expires_at > now:
                self._cache.move_to_end(key)
                return self._outcome(
                    cached.transcript,
                    None,
                    cache_hit=True,
                    coalesced=False,
                )
            if cached is not None:
                del self._cache[key]

            task = self._in_flight.get(key)
            coalesced = task is not None
            if task is None:
                task = asyncio.create_task(self._fetch_and_cleanup(key))
                self._in_flight[key] = task

        transcript, latency_ms = await asyncio.shield(task)

        return self._outcome(
            transcript,
            latency_ms,
            cache_hit=False,
            coalesced=coalesced,
        )

    async def _fetch_and_cleanup(
        self, key: tuple[str, tuple[str, ...]]
    ) -> tuple[Transcript, float]:
        try:
            return await self._fetch_uncached(key)
        finally:
            current_task = asyncio.current_task()
            async with self._lock:
                if self._in_flight.get(key) is current_task:
                    del self._in_flight[key]

    async def _fetch_uncached(self, key: tuple[str, tuple[str, ...]]) -> tuple[Transcript, float]:
        video_id, languages = key
        async with self._semaphore:
            loop = asyncio.get_running_loop()
            started = time.perf_counter()
            future = loop.run_in_executor(
                self._executor,
                self._provider.fetch,
                video_id,
                languages,
            )
            try:
                transcript = await asyncio.wait_for(future, timeout=self._timeout_seconds + 1)
            except TimeoutError as error:
                raise TranscriptAcquisitionError(
                    FailureCode.ACQUISITION_TIMEOUT,
                    "Transcript acquisition exceeded the configured timeout.",
                    retryable=True,
                ) from error
            latency_ms = (time.perf_counter() - started) * 1000

        if self._cache_ttl_seconds > 0:
            async with self._lock:
                self._cache[key] = _CachedValue(
                    expires_at=time.monotonic() + self._cache_ttl_seconds,
                    transcript=transcript,
                )
                self._cache.move_to_end(key)
                while len(self._cache) > self._cache_max_entries:
                    self._cache.popitem(last=False)
        return transcript, latency_ms

    @staticmethod
    def _outcome(
        transcript: Transcript,
        latency_ms: float | None,
        *,
        cache_hit: bool,
        coalesced: bool,
    ) -> AcquisitionOutcome:
        return AcquisitionOutcome(
            transcript=transcript,
            provider_latency_ms=latency_ms,
            cache_hit=cache_hit,
            coalesced=coalesced,
            timing=calculate_timing_metrics(transcript),
        )

    def close(self) -> None:
        self._executor.shutdown(wait=False, cancel_futures=True)


class SlidingWindowRateLimiter:
    """Small single-process limiter for accidental request loops in the MVP."""

    def __init__(self, limit: int, window_seconds: float = 60.0) -> None:
        self._limit = limit
        self._window_seconds = window_seconds
        self._timestamps: deque[float] = deque()
        self._lock = asyncio.Lock()

    async def allow(self) -> bool:
        now = time.monotonic()
        cutoff = now - self._window_seconds
        async with self._lock:
            while self._timestamps and self._timestamps[0] <= cutoff:
                self._timestamps.popleft()
            if len(self._timestamps) >= self._limit:
                return False
            self._timestamps.append(now)
            return True
