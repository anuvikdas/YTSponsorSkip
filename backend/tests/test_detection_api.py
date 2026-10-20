"""Full detection HTTP path without network use or held-out labels."""

import asyncio
import json
import time

import pytest
from httpx import ASGITransport, AsyncClient
from ytsponsorskip.config import Settings
from ytsponsorskip.detection_service import DetectionService
from ytsponsorskip.domain import (
    FailureCode,
    Transcript,
    TranscriptAcquisitionError,
    TranscriptSnippet,
)
from ytsponsorskip.main import create_app
from ytsponsorskip.providers.saved import DEFAULT_SAVED_DIR, SavedTuneTranscriptProvider
from ytsponsorskip.service import TranscriptService
from ytsponsorskip.trial_budget import TrialBudget


def saved_app(provider=None, **settings_overrides):
    settings = Settings(
        _env_file=None,
        request_limit_per_minute=100,
        **settings_overrides,
    )
    service = TranscriptService(
        provider or SavedTuneTranscriptProvider(),
        max_concurrent=2,
        timeout_seconds=5,
        cache_ttl_seconds=60,
        cache_max_entries=8,
    )
    detection = DetectionService(
        {"saved": service},
        cache_ttl_seconds=60,
        detector_variant=settings.detector_variant,
    )
    return create_app(settings=settings, detection_service=detection), detection


def path(video_id, mode="conservative", source="saved"):
    return f"/api/v1/detections/{video_id}?mode={mode}&source={source}"


@pytest.mark.asyncio
async def test_saved_positive_negative_and_mode_cache_identity():
    app, detection = saved_app()
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            positive = await client.get(path("094y1Z2wpJg"), headers={"X-Request-ID": "positive-1"})
            repeated = await client.get(path("094y1Z2wpJg"), headers={"X-Request-ID": "positive-2"})
            aggressive = await client.get(
                path("094y1Z2wpJg", "aggressive"), headers={"X-Request-ID": "positive-3"}
            )
            negative = await client.get(path("DTvS9lvRxZ8"), headers={"X-Request-ID": "negative-1"})
        assert positive.status_code == repeated.status_code == aggressive.status_code == 200
        assert positive.json()["intervals"] and negative.json()["intervals"] == []
        assert negative.json()["status"] == "ready"
        assert positive.json()["transcript_source"] == "saved"
        assert positive.json()["timing_provenance"].startswith("derived_")
        assert positive.json()["request_id"] == "positive-1"
        assert repeated.json()["request_id"] == "positive-2"
        assert repeated.json()["transcript_cache_hit"] is True
        assert repeated.json()["detection_cache_hit"] is True
        assert aggressive.json()["transcript_cache_hit"] is True
        assert aggressive.json()["detection_cache_hit"] is False
        assert positive.json()["detector_version"] == repeated.json()["detector_version"]
        assert positive.json()["transcript_sha256"] == repeated.json()["transcript_sha256"]
    finally:
        detection.close()


@pytest.mark.asyncio
async def test_contextual_variant_is_opt_in_and_retains_preview_contract():
    baseline_app, baseline = saved_app()
    changed_app, changed = saved_app(detector_variant="contextual_v1")
    try:
        async with AsyncClient(
            transport=ASGITransport(app=baseline_app), base_url="http://test"
        ) as client:
            old = await client.get(
                path("I9hJ_Rux9y0"), headers={"X-Request-ID": "baseline"}
            )
        async with AsyncClient(
            transport=ASGITransport(app=changed_app), base_url="http://test"
        ) as client:
            new = await client.get(
                path("I9hJ_Rux9y0"), headers={"X-Request-ID": "contextual"}
            )
        assert old.status_code == new.status_code == 200
        assert old.json()["intervals"] == []
        new_ranges = [
            (item["start_seconds"], item["end_seconds"])
            for item in new.json()["intervals"]
        ]
        assert new_ranges == [(683, 715)]
        assert new.json()["intervals"][0]["auto_skip_eligible"] is True
        assert old.json()["detector_version"] != new.json()["detector_version"]
    finally:
        baseline.close()
        changed.close()


@pytest.mark.asyncio
async def test_invalid_request_and_unsupported_saved_video():
    app, detection = saved_app()
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            invalid = await client.get(path("short"), headers={"X-Request-ID": "valid-id"})
            missing_identity = await client.get(path("094y1Z2wpJg"))
            invalid_mode = await client.get(
                path("094y1Z2wpJg", "maybe"), headers={"X-Request-ID": "valid-id"}
            )
            unsupported = await client.get(
                path("dQw4w9WgXcQ"), headers={"X-Request-ID": "valid-id"}
            )
            no_fallback = await client.get(
                path("094y1Z2wpJg", source="supadata"), headers={"X-Request-ID": "valid-id"}
            )
        assert [invalid.status_code, missing_identity.status_code, invalid_mode.status_code] == [
            422,
            422,
            422,
        ]
        assert unsupported.status_code == 404
        assert unsupported.json()["error"]["code"] == "NO_MATCHING_TRANSCRIPT"
        assert no_fallback.status_code == 503
    finally:
        detection.close()


@pytest.mark.asyncio
async def test_malformed_saved_data_and_detection_failure(tmp_path):
    original = json.loads((DEFAULT_SAVED_DIR / "094y1Z2wpJg.json").read_text())
    original["snippets"][0]["duration_seconds"] = float("nan")
    (tmp_path / "094y1Z2wpJg.json").write_text(json.dumps(original))
    app, detection = saved_app(SavedTuneTranscriptProvider(tmp_path))
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            malformed = await client.get(
                path("094y1Z2wpJg"), headers={"X-Request-ID": "bad-source"}
            )
        assert malformed.status_code == 503
        assert malformed.json()["error"]["code"] == "UPSTREAM_CHANGED"
    finally:
        detection.close()

    class MalformedProvider:
        def fetch(self, video_id, _languages):
            return Transcript(
                video_id,
                "English",
                "en",
                None,
                (TranscriptSnippet(0, "words", float("nan"), 2),),
                "bad-provider",
                "test",
            )

    app, detection = saved_app(MalformedProvider())
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            malformed = await client.get(
                path("094y1Z2wpJg"), headers={"X-Request-ID": "bad-provider"}
            )
        assert malformed.status_code == 503
        assert malformed.json()["error"]["code"] == "UPSTREAM_CHANGED"
    finally:
        detection.close()

    app, detection = saved_app()

    class BrokenDetector:
        def detect(self, *_):
            raise ValueError("private implementation detail")

    detection.detector = BrokenDetector()
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            failed = await client.get(path("094y1Z2wpJg"), headers={"X-Request-ID": "bad-detector"})
        assert failed.status_code == 503
        assert failed.json()["error"]["code"] == "PROVIDER_ERROR"
    finally:
        detection.close()


class SlowSavedProvider(SavedTuneTranscriptProvider):
    def __init__(self):
        super().__init__()
        self.calls = 0

    def fetch(self, video_id, preferred_languages):
        self.calls += 1
        time.sleep(0.05)
        return super().fetch(video_id, preferred_languages)


@pytest.mark.asyncio
async def test_duplicate_http_requests_coalesce_transcript_acquisition():
    provider = SlowSavedProvider()
    app, detection = saved_app(provider)
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            left, right = await asyncio.gather(
                client.get(path("094y1Z2wpJg"), headers={"X-Request-ID": "left"}),
                client.get(path("094y1Z2wpJg"), headers={"X-Request-ID": "right"}),
            )
        assert left.status_code == right.status_code == 200
        assert provider.calls == 1
        assert sorted(
            [left.json()["transcript_coalesced"], right.json()["transcript_coalesced"]]
        ) == [False, True]
    finally:
        detection.close()


class FailingProvider:
    def fetch(self, *_):
        raise TranscriptAcquisitionError(
            FailureCode.TRIAL_BUDGET_EXHAUSTED,
            "Trial exhausted; skipping unavailable.",
            retryable=False,
        )


@pytest.mark.asyncio
async def test_exhausted_provider_remains_distinct_from_zero_predictions():
    app, detection = saved_app(FailingProvider())
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get(path("094y1Z2wpJg"), headers={"X-Request-ID": "exhausted"})
        assert response.status_code == 503
        assert response.json()["error"]["code"] == "TRIAL_BUDGET_EXHAUSTED"
    finally:
        detection.close()


@pytest.mark.asyncio
async def test_mocked_supadata_detection_path_cache_and_budget(monkeypatch, tmp_path):
    class Response:
        status_code = 200
        headers = {}

        def __init__(self, body):
            self.body = body

        def json(self):
            return self.body

    class Session:
        def __init__(self):
            self.headers = {}
            self.acquisitions = 0

        def get(self, url, *, params=None, timeout=None):
            if url.endswith("/me"):
                return Response({"plan": "Free", "maxCredits": 100, "usedCredits": 2})
            self.acquisitions += 1
            assert params["mode"] == "native" and params["text"] == "false"
            return Response(
                {
                    "lang": "en",
                    "content": [
                        {
                            "text": "This video is sponsored by Example",
                            "offset": 1000,
                            "duration": 4000,
                            "lang": "en",
                        },
                        {
                            "text": "Visit the link below",
                            "offset": 5000,
                            "duration": 4000,
                            "lang": "en",
                        },
                    ],
                }
            )

    session = Session()
    monkeypatch.setattr("ytsponsorskip.providers.supadata.requests.Session", lambda: session)
    settings = Settings(
        _env_file=None,
        SUPADATA_API_KEY="test-only-key",
        request_timeout_seconds=30,
        trial_budget_path=tmp_path / "trial.sqlite3",
        trial_attempt_limit=3,
        request_limit_per_minute=100,
    )
    app = create_app(settings=settings)
    async with (
        app.router.lifespan_context(app),
        AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client,
    ):
        first = await client.get(
            path("dQw4w9WgXcQ", source="supadata"), headers={"X-Request-ID": "mock-1"}
        )
        repeated = await client.get(
            path("dQw4w9WgXcQ", source="supadata"), headers={"X-Request-ID": "mock-2"}
        )
        exhausted = await client.get(
            path("Vw1Qrko8oTs", source="supadata"), headers={"X-Request-ID": "mock-3"}
        )
    assert first.status_code == repeated.status_code == 200
    assert first.json()["transcript_source"] == "supadata"
    assert first.json()["caption_type"] == "unknown"
    assert first.json()["timing_provenance"].startswith("source_cue_")
    assert repeated.json()["transcript_cache_hit"] is True
    assert repeated.json()["detection_cache_hit"] is True
    assert exhausted.status_code == 503
    assert exhausted.json()["error"]["code"] == "TRIAL_BUDGET_EXHAUSTED"
    assert session.acquisitions == 1
    assert TrialBudget(settings.trial_budget_path, limit=3).snapshot()["attempts_used"] == 3
