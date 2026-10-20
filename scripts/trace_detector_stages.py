#!/usr/bin/env python3
"""Trace frozen rule stages on saved cues; review times select output only, never candidates."""

import argparse
import json
import math
import sys
from dataclasses import asdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend/src"))
sys.path.insert(0, str(ROOT / "scripts"))

from evaluate_detector import sha256, usable_transcript  # noqa: E402
from ytsponsorskip.detection_service import validate_transcript  # noqa: E402
from ytsponsorskip.detector import (  # noqa: E402
    PromotionDetector,
    RulesWindowClassifier,
    Sensitivity,
    assemble_candidates,
    build_windows,
)


def contains(ranges: list[tuple[float, float]], second: float) -> bool:
    return any(start <= second < end for start, end in ranges)


def diagnose_point(
    *,
    second: float,
    observed_range: tuple[float, float],
    candidate_ranges: list[tuple[float, float]],
    final_ranges: list[tuple[float, float]],
) -> str:
    """Diagnostic category for one approximate point, not a semantic ground-truth claim."""
    if not contains([observed_range], second):
        return "outside_available_transcript_timing"
    if not contains(candidate_ranges, second):
        return "excluded_by_window_scoring_or_candidate_assembly"
    if not contains(final_ranges, second):
        return "removed_during_boundary_refinement_or_minimum_duration_gate"
    return "included_in_final_interval_at_reported_point"


def trace(document: dict, *, focus_seconds: float, context_seconds: float = 90) -> dict:
    transcript = usable_transcript(document)
    if transcript is None:
        raise ValueError("Saved transcript must contain nonempty normalized timed cues")
    validate_transcript(transcript, transcript.video_id)
    if not math.isfinite(focus_seconds) or focus_seconds < 0:
        raise ValueError("Focus seconds must be finite and nonnegative")
    if not math.isfinite(context_seconds) or context_seconds <= 0:
        raise ValueError("Context seconds must be finite and positive")

    # The detector stages see only the transcript and frozen Conservative configuration.
    classifier = RulesWindowClassifier()
    windows = build_windows(transcript)
    scores = tuple(classifier.score(window) for window in windows)
    candidates = assemble_candidates(windows, scores, classifier, Sensitivity.CONSERVATIVE)
    final = PromotionDetector().detect(transcript, Sensitivity.CONSERVATIVE)

    cue_by_id = {cue.index: cue for cue in transcript.snippets}
    candidate_ranges = [
        (
            min(cue_by_id[index].start_seconds for index in item.snippet_indices),
            max(cue_by_id[index].end_seconds for index in item.snippet_indices),
        )
        for item in candidates
    ]
    final_ranges = [(item.start_seconds, item.end_seconds) for item in final.intervals]
    observed_range = (
        min(cue.start_seconds for cue in transcript.snippets),
        max(cue.end_seconds for cue in transcript.snippets),
    )
    lower, upper = max(0, focus_seconds - context_seconds), focus_seconds + context_seconds
    candidate_window_ids = {window_id for item in candidates for window_id in item.window_ids}
    return {
        "video_id": transcript.video_id,
        "transcript_provider": transcript.provider,
        "transcript_provider_version": transcript.provider_version,
        "language_code": transcript.language_code,
        "caption_type": (
            "generated"
            if transcript.is_generated is True
            else "manual"
            if transcript.is_generated is False
            else "unknown"
        ),
        "mode": "conservative",
        "detector_source_sha256": sha256(ROOT / "backend/src/ytsponsorskip/detector.py"),
        "focus_seconds_is_output_filter_only": focus_seconds,
        "observed_cue_range": observed_range,
        "stage_diagnosis_at_approximate_point": diagnose_point(
            second=focus_seconds,
            observed_range=observed_range,
            candidate_ranges=candidate_ranges,
            final_ranges=final_ranges,
        ),
        "candidate_ranges": candidate_ranges,
        "final_intervals": [asdict(item) for item in final.intervals],
        "nearby_windows": [
            {
                **asdict(window),
                "score": scores[position].score,
                "evidence": scores[position].evidence,
                "qualifies_as_anchor": classifier.qualifies(
                    scores[position], Sensitivity.CONSERVATIVE
                ),
                "supports_neighbor": classifier.supports(
                    scores[position], Sensitivity.CONSERVATIVE
                ),
                "included_in_candidate": window.window_id in candidate_window_ids,
            }
            for position, window in enumerate(windows)
            if window.start_seconds < upper and window.end_seconds > lower
        ],
        "nearby_candidates": [
            {**asdict(item), "range_seconds": candidate_ranges[position]}
            for position, item in enumerate(candidates)
            if candidate_ranges[position][0] < upper and candidate_ranges[position][1] > lower
        ],
        "nearby_original_cues": [
            asdict(cue)
            for cue in transcript.snippets
            if cue.start_seconds < upper and cue.end_seconds > lower
        ],
        "limitation": (
            "A point diagnosis cannot establish an exact promotion start; compare the full "
            "nearby windows/cues with the video. Matching a user-reported Chrome preview "
            "also requires the same transcript source and detector version."
        ),
    }


def run() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--focus-seconds", type=float, required=True)
    parser.add_argument("--context-seconds", type=float, default=90)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        parser.error("Output exists; refusing to overwrite an earlier diagnostic")
    document = json.loads(args.source.read_text(encoding="utf-8"))
    result = trace(
        document,
        focus_seconds=args.focus_seconds,
        context_seconds=args.context_seconds,
    )
    result["source_file_sha256"] = sha256(args.source)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    print(
        f"{result['video_id']}: {result['stage_diagnosis_at_approximate_point']}; "
        f"{len(result['nearby_windows'])} nearby windows; "
        f"{len(result['nearby_candidates'])} nearby candidates"
    )


if __name__ == "__main__":
    run()
