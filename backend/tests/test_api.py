import asyncio
import time
from collections.abc import Sequence
from threading import Lock

import pytest
from httpx import ASGITransport, AsyncClient
from ytsponsorskip.config import Settings
from ytsponsorskip.domain import (
    FailureCode,
    Transcript,
    TranscriptAcquisitionError,
    TranscriptSnippet,
)
from ytsponsorskip.main import create_app
from ytsponsorskip.service import TranscriptService


class FakeProvider:
    def __init__(self, *, delay_seconds: float = 0) -> None:
        self.calls = 0
        self.active_calls = 0
        self.max_active_calls = 0
        self.delay_seconds = delay_seconds
        self.error: TranscriptAcquisitionError | None = None
        self._lock = Lock()

    def fetch(self, video_id: str, preferred_languages: Sequence[str]) -> Transcript:
        with self._lock:
            self.calls += 1
            self.active_calls += 1
            self.max_active_calls = max(self.max_active_calls, self.active_calls)
        try:
            if self.delay_seconds:
                time.sleep(self.delay_seconds)
            if self.error:
                raise self.error
            return Transcript(
                video_id=video_id,
                language="English",
                language_code=preferred_languages[0],
                is_generated=True,
                snippets=(
                    TranscriptSnippet(0, "hello", 0.0, 1.5),
                    TranscriptSnippet(1, "world", 1.0, 2.0),
                ),
                provider="fake",
                provider_version="test",
            )
        finally:
            with self._lock:
                self.active_calls -= 1


def make_app(provider: FakeProvider, **setting_overrides):  # type: ignore[no-untyped-def]
    values = {
        "cache_ttl_seconds": 60,
        "request_limit_per_minute": 100,
        **setting_overrides,
    }
    settings = Settings(
        **values,
    )
    service = TranscriptService(
        provider,
        max_concurrent=settings.max_concurrent_acquisitions,
        timeout_seconds=settings.request_timeout_seconds,
        cache_ttl_seconds=settings.cache_ttl_seconds,
        cache_max_entries=settings.cache_max_entries,
    )
    return create_app(settings=settings, transcript_service=service), service


@pytest.mark.asyncio
async def test_success_contract_preserves_timing_and_metadata() -> None:
    provider = FakeProvider()
    app, service = make_app(provider)
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get(
                "/api/v1/transcripts/abcdefghijk?languages=en",
                headers={"X-Request-ID": "request-1"},
            )

        assert response.status_code == 200
        body = response.json()
        assert body["request_id"] == "request-1"
        assert body["transcript"]["is_generated"] is True
        assert body["snippets"][1] == {
            "index": 1,
            "text": "world",
            "start_seconds": 1.0,
            "duration_seconds": 2.0,
        }
        assert body["timing"]["overlapping_snippet_count"] == 1
        assert response.headers["x-request-id"] == "request-1"
    finally:
        service.close()


@pytest.mark.asyncio
async def test_cache_avoids_repeated_provider_work() -> None:
    provider = FakeProvider()
    app, service = make_app(provider)
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            first = await client.get("/api/v1/transcripts/abcdefghijk")
            second = await client.get("/api/v1/transcripts/abcdefghijk")

        assert first.json()["cache_hit"] is False
        assert second.json()["cache_hit"] is True
        assert first.json()["provider_latency_ms"] is not None
        assert second.json()["provider_latency_ms"] is None
        assert provider.calls == 1
    finally:
        service.close()


@pytest.mark.asyncio
async def test_concurrent_duplicate_requests_are_coalesced() -> None:
    provider = FakeProvider(delay_seconds=0.05)
    app, service = make_app(provider)
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            responses = await asyncio.gather(
                client.get("/api/v1/transcripts/abcdefghijk"),
                client.get("/api/v1/transcripts/abcdefghijk"),
            )

        assert provider.calls == 1
        assert sorted(response.json()["coalesced"] for response in responses) == [False, True]
    finally:
        service.close()


@pytest.mark.asyncio
async def test_distinct_requests_respect_provider_concurrency_limit() -> None:
    provider = FakeProvider(delay_seconds=0.05)
    app, service = make_app(
        provider,
        max_concurrent_acquisitions=2,
        cache_ttl_seconds=0,
    )
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            responses = await asyncio.gather(
                *(client.get(f"/api/v1/transcripts/videoid00{index}") for index in range(4))
            )

        assert all(response.status_code == 200 for response in responses)
        assert provider.calls == 4
        assert provider.max_active_calls == 2
    finally:
        service.close()


@pytest.mark.asyncio
async def test_provider_failure_uses_stable_error_contract() -> None:
    provider = FakeProvider()
    provider.error = TranscriptAcquisitionError(
        FailureCode.TRANSCRIPTS_DISABLED,
        "Captions are disabled for this video.",
        retryable=False,
    )
    app, service = make_app(provider)
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get("/api/v1/transcripts/abcdefghijk")

        assert response.status_code == 404
        assert response.json()["error"]["code"] == "TRANSCRIPTS_DISABLED"
        assert response.json()["error"]["retryable"] is False
    finally:
        service.close()


@pytest.mark.asyncio
async def test_provider_invalid_video_id_is_a_client_error() -> None:
    provider = FakeProvider()
    provider.error = TranscriptAcquisitionError(
        FailureCode.INVALID_VIDEO_ID,
        "The supplied YouTube video ID is invalid.",
        retryable=False,
    )
    app, service = make_app(provider)
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get("/api/v1/transcripts/abcdefghijk")

        assert response.status_code == 422
        assert response.json()["error"]["code"] == "INVALID_VIDEO_ID"
        assert response.json()["error"]["retryable"] is False
    finally:
        service.close()


@pytest.mark.asyncio
async def test_invalid_video_id_is_rejected_before_provider_call() -> None:
    provider = FakeProvider()
    app, service = make_app(provider)
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get("/api/v1/transcripts/not%20valid")

        assert response.status_code == 422
        assert response.json()["error"]["code"] == "INVALID_REQUEST"
        assert provider.calls == 0
    finally:
        service.close()


@pytest.mark.asyncio
async def test_rate_limit_rejects_work_before_a_second_provider_call() -> None:
    provider = FakeProvider()
    app, service = make_app(provider, request_limit_per_minute=1, cache_ttl_seconds=0)
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            first = await client.get("/api/v1/transcripts/abcdefghijk")
            second = await client.get("/api/v1/transcripts/lmnopqrstuv")

        assert first.status_code == 200
        assert second.status_code == 429
        assert second.json()["error"]["code"] == "RATE_LIMITED"
        assert provider.calls == 1
    finally:
        service.close()
