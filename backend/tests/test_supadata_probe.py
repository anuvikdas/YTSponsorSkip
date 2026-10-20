"""Local native-only Supadata contract tests; all HTTP is faked."""

import sys
from collections import deque
from pathlib import Path

import pytest
from ytsponsorskip.domain import FailureCode, TranscriptAcquisitionError
from ytsponsorskip.providers.supadata import SupadataProbeError, SupadataTranscriptProvider
from ytsponsorskip.trial_budget import TrialBudget

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "tools"))
from supadata_probe import require_free_credit  # noqa: E402


class FakeResponse:
    def __init__(self, status, body, *, billable=None):
        self.status_code = status
        self._body = body
        self.headers = {"x-billable-requests": billable} if billable is not None else {}

    def json(self):
        return self._body


class FakeSession:
    def __init__(self, responses):
        self.headers = {}
        self.responses = deque(responses)
        self.calls = []

    def get(self, url, *, params=None, timeout=None):
        self.calls.append((url, params, timeout))
        return self.responses.popleft()


GOOD = {
    "lang": "en",
    "availableLangs": ["en"],
    "content": [
        {"text": "Original  text", "offset": 8150, "duration": 1200, "lang": "en"},
        {"text": "overlap", "offset": 9000, "duration": 1800, "lang": "en"},
    ],
}


def provider(responses, **kwargs):
    session = FakeSession(responses)
    return SupadataTranscriptProvider(
        "test-only", session=session, poll_interval_seconds=0.001, **kwargs
    ), session


def test_native_parameters_ms_conversion_and_unknown_caption_type():
    adapter, session = provider([FakeResponse(200, GOOD, billable="1")])
    outcome = adapter.fetch_with_observations("dQw4w9WgXcQ", ["en"])
    assert len(session.calls) == 1
    url, params, timeout = session.calls[0]
    assert url == "https://api.supadata.ai/v1/transcript"
    assert params == {
        "url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
        "lang": "en",
        "text": "false",
        "mode": "native",
    }
    assert timeout <= 5
    transcript = outcome.transcript
    assert transcript.is_generated is None
    assert transcript.snippets[0].text == "Original  text"
    assert (transcript.snippets[0].start_seconds, transcript.snippets[0].duration_seconds) == (
        8.15,
        1.2,
    )
    assert transcript.snippets[1].start_seconds == 9.0
    assert transcript.snippets[1].start_seconds < transcript.snippets[0].end_seconds
    assert outcome.observations[0].billable_requests == "1"


def test_async_job_polls_with_bound_and_finishes():
    adapter, session = provider(
        [
            FakeResponse(202, {"jobId": "job-123"}, billable="1"),
            FakeResponse(200, {"status": "queued"}),
            FakeResponse(200, {"status": "completed", **GOOD}),
        ]
    )
    outcome = adapter.fetch_with_observations("dQw4w9WgXcQ", ["en"])
    assert [ob.status_code for ob in outcome.observations] == [202, 200, 200]
    assert len(session.calls) == 3
    assert session.calls[1][0].endswith("/transcript/job-123")
    assert len(outcome.transcript.snippets) == 2


@pytest.mark.parametrize(
    "body",
    [
        {**GOOD, "lang": "fr"},
        {**GOOD, "content": [{**GOOD["content"][0], "lang": "fr"}]},
    ],
)
def test_non_english_is_rejected_without_second_transcript_request(body):
    adapter, session = provider([FakeResponse(200, body)])
    with pytest.raises(SupadataProbeError) as error:
        adapter.fetch_with_observations("dQw4w9WgXcQ", ["en"])
    assert error.value.code is FailureCode.NO_MATCHING_TRANSCRIPT
    assert len(session.calls) == 1


@pytest.mark.parametrize(
    "content",
    [
        [],
        "plain text only",
        [{"text": "", "offset": 0, "duration": 1000}],
        [{"text": "words", "offset": 0, "duration": float("nan")}],
        [{"text": "words", "offset": True, "duration": 1000}],
        [GOOD["content"][1], GOOD["content"][0]],
    ],
)
def test_200_requires_usable_ordered_timed_text(content):
    adapter, _ = provider([FakeResponse(200, {**GOOD, "content": content})])
    with pytest.raises(SupadataProbeError) as error:
        adapter.fetch_with_observations("dQw4w9WgXcQ", ["en"])
    assert error.value.code is FailureCode.UPSTREAM_CHANGED


def test_http_206_is_not_success_and_does_not_retry():
    adapter, session = provider([FakeResponse(206, {"error": "transcript-unavailable"})])
    with pytest.raises(SupadataProbeError) as error:
        adapter.fetch_with_observations("dQw4w9WgXcQ", ["en"])
    assert error.value.code is FailureCode.NO_MATCHING_TRANSCRIPT
    assert [ob.status_code for ob in error.value.observations] == [206]
    assert len(session.calls) == 1


def test_poll_limit_stops_queued_job():
    adapter, session = provider(
        [
            FakeResponse(202, {"jobId": "job-123"}),
            FakeResponse(200, {"status": "queued"}),
        ],
        max_polls=1,
    )
    with pytest.raises(SupadataProbeError) as error:
        adapter.fetch_with_observations("dQw4w9WgXcQ", ["en"])
    assert error.value.code is FailureCode.ACQUISITION_TIMEOUT
    assert len(session.calls) == 2


def test_followup_uses_full_deadline_and_counts_polls(tmp_path):
    budget = TrialBudget(tmp_path / "trial.sqlite3", limit=3, max_polls=5)
    adapter, session = provider(
        [
            FakeResponse(202, {"jobId": "job-123"}),
            FakeResponse(200, {"status": "completed", **GOOD}),
        ],
        total_timeout_seconds=30,
        per_request_timeout_seconds=30,
        max_polls=5,
        trial_budget=budget,
    )
    result = adapter.fetch_with_observations("Vw1Qrko8oTs", ["en"])
    assert result.transcript.language_code == "en"
    assert session.calls[0][2] > 29
    assert budget.snapshot()["attempts_used"] == 3
    assert budget.snapshot()["polls_used"] == 1


def test_free_credit_gate_stops_paid_unknown_and_exhausted_accounts():
    free = {"http_status": 200, "plan": "Free", "max_credits": 10, "used_credits": 8}
    require_free_credit(free)
    require_free_credit(free, minimum_remaining=2)
    with pytest.raises(SystemExit, match="no transcript request"):
        require_free_credit(free, minimum_remaining=3)
    for changed in (
        {"plan": "Pro"},
        {"used_credits": 10},
        {"http_status": 401},
        {"max_credits": None},
    ):
        with pytest.raises(SystemExit, match="no transcript request"):
            require_free_credit({**free, **changed})


def test_local_provider_checks_free_balance_before_acquisition(tmp_path):
    budget = TrialBudget(tmp_path / "trial.sqlite3", limit=3)
    adapter, session = provider(
        [
            FakeResponse(200, {"plan": "Free", "maxCredits": 100, "usedCredits": 2}),
            FakeResponse(200, GOOD),
        ],
        trial_budget=budget,
        enforce_free_credits=True,
    )
    assert len(adapter.fetch("dQw4w9WgXcQ", ["en"]).snippets) == 2
    assert session.calls[0][0].endswith("/me")
    assert session.calls[1][0].endswith("/transcript")
    assert budget.snapshot()["attempts_used"] == 3

    blocked, blocked_session = provider(
        [FakeResponse(200, {"plan": "Pro", "maxCredits": 100, "usedCredits": 2})],
        trial_budget=TrialBudget(tmp_path / "blocked.sqlite3", limit=3),
        enforce_free_credits=True,
    )
    with pytest.raises(TranscriptAcquisitionError) as error:
        blocked.fetch("dQw4w9WgXcQ", ["en"])
    assert error.value.retryable is False
    assert len(blocked_session.calls) == 1
