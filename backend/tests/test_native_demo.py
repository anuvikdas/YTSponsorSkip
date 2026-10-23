import json
from concurrent.futures import ThreadPoolExecutor

import pytest
from ytsponsorskip.domain import (
    FailureCode,
    Transcript,
    TranscriptAcquisitionError,
    TranscriptSnippet,
)
from ytsponsorskip.providers.native_demo import NativeDemoBudget, PersistentNativeProvider
from ytsponsorskip.providers.supadata import SupadataFetch, SupadataObservation


class Provider:
    def __init__(self, fail=False):
        self.calls = 0
        self.fail = fail

    def fetch_with_observations(self, video_id, _languages):
        self.calls += 1
        if self.fail:
            raise TranscriptAcquisitionError(
                FailureCode.ACQUISITION_TIMEOUT, "timeout", retryable=True
            )
        return SupadataFetch(
            Transcript(
                video_id,
                "English",
                "en",
                None,
                (
                    TranscriptSnippet(0, "original\ntext", 1, 2),
                    TranscriptSnippet(1, "overlap", 2, 3),
                ),
                "supadata-native",
                "test-native-version",
            ),
            (SupadataObservation("initial", 200, None, {"echo": "test-secret"}),),
            1,
        )


def test_native_success_persists_and_reuses_across_restart_without_an_attempt(tmp_path):
    directory = tmp_path / "native"
    budget = NativeDemoBudget(tmp_path / "budget.sqlite3", directory)
    provider = Provider()
    wrapper = PersistentNativeProvider(
        provider, budget, directory=directory, reuse_directories=[directory], secret="test-secret"
    )
    original = wrapper.fetch("newvideo001", ["en"])
    assert original.snippets[0].text == "original\ntext"
    assert budget.snapshot()["native_attempts_used"] == 1
    assert "test-secret" not in (directory / "newvideo001.attempt.json").read_text()
    restarted = PersistentNativeProvider(
        Provider(fail=True), budget, directory=directory, reuse_directories=[directory]
    )
    cached = restarted.fetch("newvideo001", ["en"])
    assert cached.snippets == original.snippets
    assert cached.is_generated is None
    assert cached.provider == "supadata-native-saved"
    assert budget.snapshot()["native_attempts_used"] == 1


def test_timeout_counts_and_cannot_be_retried(tmp_path):
    budget = NativeDemoBudget(tmp_path / "budget.sqlite3", tmp_path)
    provider = Provider(fail=True)
    wrapper = PersistentNativeProvider(
        provider, budget, directory=tmp_path, reuse_directories=[tmp_path]
    )
    for _ in range(2):
        with pytest.raises(TranscriptAcquisitionError):
            wrapper.fetch("newvideo001", ["en"])
    assert provider.calls == 1
    assert budget.snapshot()["native_attempts_used"] == 1


def test_prior_campaign_seed_and_atomic_distinct_limit(tmp_path):
    (tmp_path / "seeded00001.attempt.json").write_text(json.dumps({"video_id": "seeded00001"}))
    budget = NativeDemoBudget(tmp_path / "budget.sqlite3", tmp_path)
    assert budget.snapshot()["native_attempts_remaining"] == 4

    def reserve(video_id):
        try:
            budget.reserve(video_id)
            return True
        except TranscriptAcquisitionError:
            return False

    with ThreadPoolExecutor(max_workers=8) as pool:
        outcomes = list(pool.map(reserve, [f"video{index:06d}" for index in range(8)]))
    assert sum(outcomes) == 4
    assert budget.snapshot()["native_attempts_remaining"] == 0
    assert not reserve("seeded00001")
