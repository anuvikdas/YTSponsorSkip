"""Offline artifact and replay checks. No network clients or acquisition calls."""

import copy
import csv
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))

from build_error_review import render_html, render_markdown, review_video  # noqa: E402
from compare_detectors import (  # noqa: E402
    model_record_intervals,
    paired_quality,
    recorded_intervals,
    replay_mode,
)
from evaluate_detector import summarize_mode  # noqa: E402
from offline_common import (  # noqa: E402
    ROOT,
    load_tune,
    subtract_ranges,
    verify_saved_evaluation,
    write_new,
)
from ytsponsorskip.detector import Sensitivity  # noqa: E402
from ytsponsorskip.evaluation import ranges_duration  # noqa: E402


@pytest.fixture(scope="module")
def corpus():
    return load_tune()


@pytest.fixture(scope="module")
def saved():
    return json.loads((ROOT / "data/evaluation/tune-rules-3c35ceb.json").read_text())


def test_range_difference_preserves_holes_and_adjacent_edges():
    assert subtract_ranges([(0, 10), (10, 20)], [(3, 5), (8, 12), (20, 30)]) == [
        (0, 3),
        (5, 8),
        (12, 20),
    ]
    assert subtract_ranges([(5, 8)], [(0, 30)]) == []


def test_corpus_is_exactly_reviewed_tune(corpus):
    videos, labels, transcripts, _, hashes, excluded = corpus
    assert len(videos) == len(transcripts) == len(hashes) == 14
    assert len([v for v in videos if v["promotion_status"] == "none"]) == 4
    assert all(v["split"] == "tune" and v["review_status"] == "reviewed" for v in videos)
    assert set(labels) == set(transcripts)
    assert not excluded


def test_revised_labels_are_versioned_and_held_out_unchanged():
    original_root = ROOT / "data/validation"
    revised_root = original_root / "revised-2026-10-19"

    def rows(path):
        with path.open(newline="", encoding="utf-8") as source:
            return list(csv.DictReader(source))

    original_videos = {v["video_id"]: v for v in rows(original_root / "videos.csv")}
    revised_videos = {v["video_id"]: v for v in rows(revised_root / "videos.csv")}
    original_segments = rows(original_root / "segments.csv")
    revised_segments = rows(revised_root / "segments.csv")
    assert len(revised_videos) == 24 and len(revised_segments) == 14
    assert [v for v in revised_videos.values() if v["split"] == "held_out"] == [
        v for v in original_videos.values() if v["split"] == "held_out"
    ]
    assert [
        s
        for s in revised_segments
        if s["video_id"]
        in {v["video_id"] for v in revised_videos.values() if v["split"] == "held_out"}
    ] == [
        s
        for s in original_segments
        if s["video_id"]
        in {v["video_id"] for v in original_videos.values() if v["split"] == "held_out"}
    ]
    reviewed_tune = [
        v
        for v in revised_videos.values()
        if v["split"] == "tune" and v["review_status"] == "reviewed"
    ]
    assert len(reviewed_tune) == 14
    assert sum(v["promotion_status"] == "one_or_more" for v in reviewed_tune) == 11
    assert sum(v["promotion_status"] == "none" for v in reviewed_tune) == 3
    assert all(
        revised_videos[v["video_id"]] == v
        for v in original_videos.values()
        if v["review_status"] == "in_progress"
    )


def test_revised_evaluation_changes_labels_not_predictions():
    old = json.loads((ROOT / "data/evaluation/tune-rules-3c35ceb.json").read_text())
    revised = json.loads((ROOT / "data/evaluation/tune-rules-revised-2026-10-19.json").read_text())
    assert old["detector"]["source_sha256"] == revised["detector"]["source_sha256"]
    for mode in Sensitivity:
        old_rows = {r["video_id"]: r for r in old["modes"][mode.value]["per_video"]}
        for row in revised["modes"][mode.value]["per_video"]:
            assert row["predictions"] == old_rows[row["video_id"]]["predictions"]
            assert row["window_count"] == old_rows[row["video_id"]]["window_count"]


def test_replay_metrics_equal_saved_and_fresh_rules(corpus, saved):
    videos, labels, transcripts, _, hashes, _ = corpus
    verify_saved_evaluation(saved, videos, hashes)
    for mode in Sensitivity:
        recorded = saved["modes"][mode.value]
        records = {(mode.value, row["video_id"]): row for row in recorded["per_video"]}
        replay = replay_mode(mode, videos, labels, transcripts, hashes, records)
        fresh = summarize_mode(mode, videos, labels, transcripts)
        for key, value in recorded.items():
            if key not in ("per_video", "detection_runtime_ms"):
                assert replay[key] == fresh[key] == value
        assert replay["detection_runtime_ms"] is None
        assert all(row["detection_runtime_ms"] is None for row in replay["per_video"])


def test_replay_rejects_changed_transcript_or_out_of_scope(corpus, saved):
    videos, _, _, _, hashes, _ = corpus
    altered = dict(hashes)
    altered[videos[0]["video_id"]] = "changed"
    with pytest.raises(ValueError, match="hash mismatch"):
        verify_saved_evaluation(saved, videos, altered)
    altered_saved = copy.deepcopy(saved)
    altered_saved["scope"]["held_out_used"] = True
    with pytest.raises(ValueError, match="reviewed tune"):
        verify_saved_evaluation(altered_saved, videos, hashes)


def test_missing_recordings_are_excluded_not_empty_predictions(corpus, saved):
    videos, labels, transcripts, _, hashes, _ = corpus
    replay = replay_mode(Sensitivity.CONSERVATIVE, videos, labels, transcripts, hashes, {})
    assert replay["evaluated_video_count"] == 0
    assert len(replay["excluded_outputs"]) == 14
    assert replay["missed_promotional_seconds"] is None
    runs = [
        {"name": "missing", "modes": dict.fromkeys([m.value for m in Sensitivity], replay)},
        {"name": "saved", "modes": saved["modes"]},
    ]
    assert paired_quality(runs)["conservative"]["video_ids"] == []


@pytest.mark.parametrize("start,end", [(True, 3), (2, 2), (-1, 2), (0, float("nan"))])
def test_invalid_predictions_fail_closed(start, end):
    with pytest.raises(ValueError, match="Invalid recorded interval"):
        recorded_intervals([{"start_seconds": start, "end_seconds": end}])


def synthetic_record(transcript, digest):
    cues = transcript.snippets[:3]
    request = {
        "video_id": transcript.video_id,
        "request_id": "synthetic-only-test-123",
        "language_code": transcript.language_code,
        "sensitivity": "conservative",
        "prompt_version": "synthetic-v1",
        "snippets": [
            {
                "snippet_id": c.index,
                "text": c.text,
                "start_seconds": c.start_seconds,
                "duration_seconds": c.duration_seconds,
            }
            for c in cues
        ],
    }
    response = {k: request[k] for k in ("video_id", "request_id", "prompt_version")}
    response.update(
        model_version="synthetic-test-no-inference",
        segments=[
            {
                "start_snippet_id": cues[0].index,
                "end_snippet_id": cues[-1].index,
                "ownership": "third_party",
                "kind": "sponsorship",
                "evidence_snippet_ids": [cues[0].index],
                "reason_code": "synthetic_test_only",
            }
        ],
    )
    return {
        "origin": "synthetic_fixture",
        "transcript_sha256": digest,
        "request": request,
        "response": response,
    }


def test_model_replay_maps_original_ids_and_rejects_modified_or_missing_cues(corpus):
    _, _, transcripts, _, hashes, _ = corpus
    vid = next(iter(transcripts))
    transcript = transcripts[vid]
    record = synthetic_record(transcript, hashes[vid])
    _, _, predictions = model_record_intervals(record, transcript, hashes[vid])
    assert predictions[0].start_seconds == transcript.snippets[0].start_seconds
    assert predictions[0].end_seconds == transcript.snippets[2].end_seconds
    altered = copy.deepcopy(record)
    altered["request"]["snippets"][0]["text"] = "altered"
    with pytest.raises(ValueError, match="original source"):
        model_record_intervals(altered, transcript, hashes[vid])
    altered = copy.deepcopy(record)
    altered["request"]["snippets"].pop(1)
    with pytest.raises(ValueError, match="crosses source cues"):
        model_record_intervals(altered, transcript, hashes[vid])


def test_all_error_ranges_and_timing_partition_match_metrics(corpus, saved):
    videos, labels, transcripts, documents, _, _ = corpus
    rows = {m: {r["video_id"]: r for r in s["per_video"]} for m, s in saved["modes"].items()}
    totals = [0, 0, 0]
    review = {"summary": saved["modes"], "evaluation_sha256": "test", "videos": []}
    for video in videos:
        vid = video["video_id"]
        result = review_video(
            video,
            labels[vid],
            transcripts[vid],
            documents[vid],
            {m: group[vid] for m, group in rows.items()},
        )
        review["videos"].append(result)
        for mode in result["modes"].values():
            assert (
                ranges_duration(mode["false_skip_ranges"])
                == mode["metrics"]["incorrect_predicted_seconds"]
            )
            parts = [
                ranges_duration(mode[k])
                for k in (
                    "refinement_missed_ranges",
                    "candidate_stage_missed_ranges",
                    "outside_observed_span",
                )
            ]
            assert sum(parts) == mode["metrics"]["missed_promotional_seconds"]
        c = result["modes"]["conservative"]
        for i, key in enumerate(
            ("refinement_missed_ranges", "candidate_stage_missed_ranges", "outside_observed_span")
        ):
            totals[i] += ranges_duration(c[key])
    assert totals == [95, 1, 8]
    review["videos"][0]["title"] = "<script>alert('x')</script>"
    review["videos"][0]["review_notes"] = ["<img src=x>"]
    rendered = render_html(review)
    assert "<script>alert" not in rendered and "&lt;script&gt;" in rendered
    assert "<img src=x>" not in rendered
    assert rendered.count("<article ") == 14
    assert "fetch(" not in rendered and 'src="https://' not in rendered
    assert render_markdown(review).count("### Transcript context") == 14


def test_artifact_writer_refuses_overwrite(tmp_path):
    path = tmp_path / "run.json"
    write_new(path, "original")
    with pytest.raises(FileExistsError):
        write_new(path, "replacement")
    assert path.read_text() == "original"
