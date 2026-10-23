"""The trial ledger counts upstream work, survives restarts, and fails closed at its limits."""

import asyncio
import time
from concurrent.futures import ThreadPoolExecutor

import pytest
from ytsponsorskip.domain import (
    FailureCode,
    Transcript,
    TranscriptAcquisitionError,
    TranscriptSnippet,
)
from ytsponsorskip.service import TranscriptService
from ytsponsorskip.trial_budget import BudgetedTranscriptProvider, TrialBudget


def test_seeded_observations_are_idempotent_and_persistent(tmp_path):
    path = tmp_path / "trial.sqlite3"
    first = TrialBudget(path, limit=3, max_polls=2)
    assert first.snapshot() == {
        "attempts_used": 2,
        "attempts_remaining": 1,
        "attempt_limit": 3,
        "polls_used": 0,
        "polls_per_attempt_limit": 2,
    }
    attempt = first.reserve_attempt("Vw1Qrko8oTs", "supadata-native")
    assert first.reserve_poll(attempt) == 1
    assert first.reserve_poll(attempt) == 2
    with pytest.raises(TranscriptAcquisitionError) as poll_error:
        first.reserve_poll(attempt)
    assert poll_error.value.code is FailureCode.TRIAL_POLL_LIMIT
    restarted = TrialBudget(path, limit=3, max_polls=2)
    assert restarted.snapshot()["attempts_used"] == 3
    assert restarted.snapshot()["polls_used"] == 2
    with pytest.raises(TranscriptAcquisitionError) as error:
        restarted.reserve_attempt("anotherVideo", "supadata-native")
    assert error.value.code is FailureCode.TRIAL_BUDGET_EXHAUSTED


def test_concurrent_reservations_cannot_exceed_cap(tmp_path):
    budget = TrialBudget(tmp_path / "trial.sqlite3", limit=5)

    def reserve(_):
        try:
            budget.reserve_attempt("abcdefghijk", "test")
            return True
        except TranscriptAcquisitionError as error:
            assert error.code is FailureCode.TRIAL_BUDGET_EXHAUSTED
            return False

    with ThreadPoolExecutor(max_workers=10) as pool:
        outcomes = list(pool.map(reserve, range(20)))
    assert sum(outcomes) == 3
    assert budget.snapshot()["attempts_used"] == 5


class SlowProvider:
    def __init__(self):
        self.calls = 0

    def fetch(self, video_id, preferred_languages):
        self.calls += 1
        time.sleep(0.03)
        return Transcript(
            video_id,
            "English",
            "en",
            None,
            (TranscriptSnippet(0, "words", 1.0, 2.0),),
            "fake",
            "test",
        )


@pytest.mark.asyncio
async def test_cache_and_coalescing_reserve_only_one_actual_request(tmp_path):
    budget = TrialBudget(tmp_path / "trial.sqlite3", limit=3)
    inner = SlowProvider()
    service = TranscriptService(
        BudgetedTranscriptProvider(inner, budget, source="fake"),
        max_concurrent=2,
        timeout_seconds=1,
        cache_ttl_seconds=60,
        cache_max_entries=8,
    )
    try:
        responses = await asyncio.gather(
            service.fetch("abcdefghijk", ["en"]), service.fetch("abcdefghijk", ["en"])
        )
        assert sorted(response.coalesced for response in responses) == [False, True]
        assert inner.calls == 1
        assert budget.snapshot()["attempts_used"] == 3
        cached = await service.fetch("abcdefghijk", ["en"])
        assert cached.cache_hit is True
        assert budget.snapshot()["attempts_used"] == 3
        with pytest.raises(TranscriptAcquisitionError) as error:
            await service.fetch("different01", ["en"])
        assert error.value.code is FailureCode.TRIAL_BUDGET_EXHAUSTED
        assert inner.calls == 1
    finally:
        service.close()
