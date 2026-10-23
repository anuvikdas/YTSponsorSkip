"""Campaign limits fail before key access or a credit-bearing request."""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from scripts import collect_development_transcript as collector  # noqa: E402


def test_campaign_refuses_same_video_even_after_failed_attempt(tmp_path, monkeypatch):
    monkeypatch.setattr(collector, "OUTPUT", tmp_path)
    (tmp_path / "qf7ws2DF-zk.attempt.json").write_text('{"status":"unavailable"}')
    with pytest.raises(SystemExit, match="no retry"):
        collector.collect("qf7ws2DF-zk")


def test_campaign_refuses_sixth_distinct_video(tmp_path, monkeypatch):
    monkeypatch.setattr(collector, "OUTPUT", tmp_path)
    for number in range(5):
        (tmp_path / f"video00000{number}.attempt.json").write_text("{}")
    with pytest.raises(SystemExit, match="Five additional"):
        collector.collect("newvideo001")


def test_campaign_reuses_an_existing_saved_transcript(tmp_path, monkeypatch):
    monkeypatch.setattr(collector, "ROOT", tmp_path)
    monkeypatch.setattr(collector, "OUTPUT", tmp_path / "results/development-transcripts")
    saved = tmp_path / "data/transcripts/tune/already0001.json"
    saved.parent.mkdir(parents=True)
    saved.write_text("{}")
    with pytest.raises(SystemExit, match="saved transcript"):
        collector.collect("already0001")
