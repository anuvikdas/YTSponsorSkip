"""Exercise selected local FastAPI provider without any live Supadata request."""

import pytest
from httpx import ASGITransport, AsyncClient
from ytsponsorskip.config import Settings
from ytsponsorskip.main import create_app
from ytsponsorskip.trial_budget import TrialBudget


class FakeResponse:
    status_code = 200
    headers = {}

    def __init__(self, body):
        self.body = body

    def json(self):
        return self.body


class FakeSupadataSession:
    def __init__(self):
        self.headers = {}
        self.account_calls = 0
        self.transcript_calls = 0

    def get(self, url, *, params=None, timeout=None):
        if url.endswith("/me"):
            self.account_calls += 1
            return FakeResponse({"plan": "Free", "maxCredits": 100, "usedCredits": 2})
        assert url.endswith("/transcript")
        assert params["mode"] == "native" and params["text"] == "false"
        self.transcript_calls += 1
        return FakeResponse(
            {
                "lang": "en",
                "content": [
                    {"text": "Original words", "offset": 1500, "duration": 2200, "lang": "en"}
                ],
            }
        )


@pytest.mark.asyncio
async def test_selected_provider_contract_cache_and_budget(monkeypatch, tmp_path):
    fake = FakeSupadataSession()
    monkeypatch.setattr("ytsponsorskip.providers.supadata.requests.Session", lambda: fake)
    settings = Settings(
        _env_file=None,
        environment="local",
        transcript_provider="supadata",
        SUPADATA_API_KEY="test-only-secret",
        request_timeout_seconds=30,
        trial_budget_path=tmp_path / "trial.sqlite3",
        native_cache_directory=tmp_path / "native",
        trial_attempt_limit=3,
    )
    app = create_app(settings=settings)
    async with (
        app.router.lifespan_context(app),
        AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client,
    ):
        first = await client.get("/api/v1/transcripts/dQw4w9WgXcQ?languages=en")
        cached = await client.get("/api/v1/transcripts/dQw4w9WgXcQ?languages=en")
        exhausted = await client.get("/api/v1/transcripts/Vw1Qrko8oTs?languages=en")

    assert first.status_code == 200
    body = first.json()
    assert body["transcript"]["provider"] == "supadata-native"
    assert body["transcript"]["is_generated"] is None
    assert body["snippets"][0]["start_seconds"] == 1.5
    assert body["snippets"][0]["duration_seconds"] == 2.2
    assert first.json()["cache_hit"] is False and cached.json()["cache_hit"] is True
    assert exhausted.status_code == 503
    assert exhausted.json()["error"]["code"] == "TRIAL_BUDGET_EXHAUSTED"
    assert fake.transcript_calls == 1
    assert fake.account_calls == 2
    assert TrialBudget(settings.trial_budget_path, limit=3).snapshot()["attempts_used"] == 3
