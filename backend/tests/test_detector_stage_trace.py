"""Offline stage tracing must not feed review timestamps into the detector."""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))

from trace_detector_stages import diagnose_point, trace  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]


def test_stage_diagnosis_separates_acquisition_candidate_and_refinement() -> None:
    observed = (0.0, 100.0)
    candidates = [(20.0, 80.0)]
    final = [(40.0, 70.0)]
    assert diagnose_point(
        second=110, observed_range=observed, candidate_ranges=candidates, final_ranges=final
    ) == "outside_available_transcript_timing"
    assert diagnose_point(
        second=10, observed_range=observed, candidate_ranges=candidates, final_ranges=final
    ) == "excluded_by_window_scoring_or_candidate_assembly"
    assert diagnose_point(
        second=30, observed_range=observed, candidate_ranges=candidates, final_ranges=final
    ) == "removed_during_boundary_refinement_or_minimum_duration_gate"
    assert diagnose_point(
        second=50, observed_range=observed, candidate_ranges=candidates, final_ranges=final
    ) == "included_in_final_interval_at_reported_point"


def test_focus_is_only_a_reporting_filter() -> None:
    source = ROOT / "data/transcripts/tune/lXfEK8G8CUI.json"
    document = json.loads(source.read_text(encoding="utf-8"))
    early = trace(document, focus_seconds=540)
    later = trace(document, focus_seconds=580)

    assert early["candidate_ranges"] == later["candidate_ranges"]
    assert early["final_intervals"] == later["final_intervals"]
    assert early["stage_diagnosis_at_approximate_point"] == (
        "removed_during_boundary_refinement_or_minimum_duration_gate"
    )
    assert later["stage_diagnosis_at_approximate_point"] == (
        "included_in_final_interval_at_reported_point"
    )


def test_partial_development_record_is_not_a_complete_label() -> None:
    source = ROOT / "data/development/partial-qf7ws2DF-zk.json"
    record = json.loads(source.read_text(encoding="utf-8"))
    assert record["split"] == "tune"
    assert record["review_status"] == "in_progress"
    assert record["annotation"]["end_seconds"] is None
    assert record["evaluation_policy"]["full_video_accuracy_eligible"] is False
    assert record["evaluation_policy"]["untouched_test_example"] is False
