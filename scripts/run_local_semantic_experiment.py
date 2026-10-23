#!/usr/bin/env python3
"""One preregistered local-encoder comparison; no acquisition or hosted inference."""

import argparse
import importlib.metadata
import json
import platform
import resource
import subprocess
import sys
from dataclasses import asdict
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend/src"))
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "tools/local-semantic"))

from evaluate_contextual_development import evaluate, load_data  # noqa: E402
from evaluate_detector import sha256, usable_transcript  # noqa: E402
from semantic import LocalSemanticDetector, LocalSemanticEncoder  # noqa: E402
from ytsponsorskip.contextual_detector import ContextualPromotionDetector  # noqa: E402
from ytsponsorskip.detector import PromotionDetector, Sensitivity  # noqa: E402
from ytsponsorskip.evaluation import (  # noqa: E402
    intersection_duration,
    match_intervals,
    playback_eligible_intervals,
    ranges_duration,
)

CONFIG = ROOT / "data/experiments/local-semantic-v1.json"
ANNOTATION = ROOT / "data/development/qf7ws2DF-zk-2026-10-22.json"
QF = ROOT / "results/development-transcripts/qf7ws2DF-zk.json"
FROZEN = ROOT / "data/evaluation/held-out-rules-frozen-2026-10-20.json"


def confirmed_interval_metrics(detector, transcript, annotation):
    detection = detector.detect(transcript, Sensitivity.CONSERVATIVE)
    predictions = playback_eligible_intervals(detection.intervals)
    ranges = [(item.start_seconds, item.end_seconds) for item in predictions]
    labels = [(item["start_seconds"], item["end_seconds"]) for item in annotation["intervals"]]
    duration = ranges_duration(labels)
    covered = intersection_duration(ranges, labels)
    return {
        "video_id": transcript.video_id,
        "review_scope": "confirmed_interval_only",
        "annotations": annotation["intervals"],
        "predictions": [asdict(item) for item in predictions],
        "known_promotional_seconds": duration,
        "covered_known_promotional_seconds": round(covered, 3),
        "missed_known_promotional_seconds": round(duration - covered, 3),
        "predicted_seconds_outside_reviewed_interval_unknown": round(
            ranges_duration(ranges) - covered, 3
        ),
        "matches": [asdict(item) for item in match_intervals(ranges, labels)],
        "full_video_false_positive_metrics": None,
    }


def acceptance(summary, reference, criteria):
    old_negatives = {
        row["video_id"]
        for row in reference["per_video"]
        if row["promotion_status"] == "none" and row["predicted_seconds"] > 0
    }
    new_negatives = {
        row["video_id"]
        for row in summary["per_video"]
        if row["promotion_status"] == "none" and row["predicted_seconds"] > 0
    }
    checks = {
        "incorrect_seconds": summary["incorrect_predicted_seconds"]
        <= criteria["maximum_incorrect_predicted_seconds"],
        "negative_videos": summary["negative_videos_with_any_predicted_skip"]
        <= criteria["maximum_negative_videos_with_predicted_skip"],
        "missed_seconds": summary["missed_promotional_seconds"]
        <= criteria["maximum_missed_promotional_seconds"],
        "matched_segments": summary["matched_segment_count"]
        >= criteria["minimum_matched_segment_count"],
        "start_boundary": summary["mean_start_boundary_error_seconds"] is not None
        and summary["mean_start_boundary_error_seconds"]
        <= criteria["maximum_mean_start_boundary_error_seconds"],
        "end_boundary": summary["mean_end_boundary_error_seconds"] is not None
        and summary["mean_end_boundary_error_seconds"]
        <= criteria["maximum_mean_end_boundary_error_seconds"],
        "no_new_negative_ids": not (new_negatives - old_negatives),
    }
    return {
        "passes": all(checks.values()),
        "checks": checks,
        "new_negative_video_ids": sorted(new_negatives - old_negatives),
    }


def regressions(summary, reference):
    prior = {row["video_id"]: row for row in reference["per_video"]}
    output = []
    for row in summary["per_video"]:
        old = prior[row["video_id"]]
        incorrect_delta = row["incorrect_predicted_seconds"] - old["incorrect_predicted_seconds"]
        missed_delta = row["missed_promotional_seconds"] - old["missed_promotional_seconds"]
        if abs(incorrect_delta) > 0.001 or abs(missed_delta) > 0.001:
            output.append(
                {
                    "video_id": row["video_id"],
                    "incorrect_seconds_delta": round(incorrect_delta, 3),
                    "missed_seconds_delta": round(missed_delta, 3),
                }
            )
    return output


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--evidence-output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists() or args.evidence_output.exists():
        parser.error("Output exists; preserve recordings and choose a new path")
    config = json.loads(CONFIG.read_text())
    versions = {name: importlib.metadata.version(name) for name in config["packages"]}
    if versions != config["packages"]:
        raise SystemExit("Use the isolated environment with the preregistered package versions")
    videos, labels, transcripts, hashes, exclusions = load_data()
    if len(transcripts) != 22:
        raise SystemExit("All 22 fully reviewed saved development inputs are required")
    qf = usable_transcript(json.loads(QF.read_text())) if QF.exists() else None
    all_transcripts = dict(transcripts)
    if qf is not None:
        all_transcripts[qf.video_id] = qf
    before_rss = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    encoder = LocalSemanticEncoder(
        ROOT / "results/local-semantic/model",
        config,
        ROOT / "results/local-semantic/embeddings",
    )
    evidence = {}
    for video_id, transcript in all_transcripts.items():
        evidence[video_id] = encoder.score_transcript(transcript)
        row = evidence[video_id]
        print(
            f"{video_id}: {row['origin']}; windows={row['all_window_count']}; "
            f"views={row['all_window_count'] + row['boundary_view_count']}; "
            f"ms={row['encoding_and_scoring_ms']}",
            flush=True,
        )
    detectors = {
        "frozen_rules": PromotionDetector(),
        "contextual_v1": ContextualPromotionDetector(),
    }
    for threshold in config["margin_settings"]:
        detectors[f"semantic_margin_{threshold:.2f}"] = LocalSemanticDetector(
            evidence,
            threshold=threshold,
            minimum_similarity=config["positive_similarity_minimum"],
        )
    summaries = {
        name: evaluate(detector, videos, labels, transcripts, Sensitivity.CONSERVATIVE)
        for name, detector in detectors.items()
    }
    for name, summary in summaries.items():
        if name.startswith("semantic_"):
            prediction_ms = summary["detection_runtime_ms"]
            encoding_ms = sum(
                evidence[video_id]["encoding_and_scoring_ms"] for video_id in transcripts
            )
            summary["prediction_assembly_runtime_ms"] = prediction_ms
            summary["shared_local_encoding_and_scoring_ms"] = round(encoding_ms, 3)
            summary["detection_runtime_ms"] = round(prediction_ms + encoding_ms, 3)
            for row in summary["per_video"]:
                row["local_encoding_and_scoring_ms"] = evidence[row["video_id"]][
                    "encoding_and_scoring_ms"
                ]
                row["embedding_origin"] = evidence[row["video_id"]]["origin"]
    reference = summaries["contextual_v1"]
    decisions = {
        name: acceptance(summary, reference, config["selection_criteria"])
        for name, summary in summaries.items()
        if name.startswith("semantic_")
    }
    passing = [name for name, decision in decisions.items() if decision["passes"]]
    selected = (
        min(
            passing,
            key=lambda name: (
                summaries[name]["incorrect_predicted_seconds"],
                summaries[name]["missed_promotional_seconds"],
                summaries[name]["detection_runtime_ms"],
            ),
        )
        if passing
        else "contextual_v1"
    )
    after_rss = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    rss_unit = 1024 * 1024 if sys.platform == "darwin" else 1024
    report = {
        "experiment_version": config["experiment_version"],
        "generated_at_utc": datetime.now(UTC).isoformat(),
        "preregistration_commit": subprocess.check_output(
            ["git", "log", "-1", "--format=%H", "--", str(CONFIG)], cwd=ROOT, text=True
        ).strip(),
        "configuration": config,
        "configuration_sha256": sha256(CONFIG),
        "model_assets": encoder.manifest,
        "package_versions": versions,
        "platform": platform.platform(),
        "source_hashes": {
            "transcripts": hashes,
            "qf_transcript": sha256(QF) if qf else None,
            "qf_annotation": sha256(ANNOTATION),
            "frozen_heldout_report_unchanged": sha256(FROZEN),
            "code": {
                str(path.relative_to(ROOT)): sha256(path)
                for path in [
                    Path(__file__),
                    ROOT / "tools/local-semantic/semantic.py",
                    ROOT / "tools/local-semantic/views.py",
                    ROOT / "scripts/evaluate_detector.py",
                    ROOT / "scripts/evaluate_contextual_development.py",
                    ROOT / "backend/src/ytsponsorskip/detector.py",
                    ROOT / "backend/src/ytsponsorskip/contextual_detector.py",
                ]
            },
        },
        "scope": {
            "fully_reviewed_development_videos": 22,
            "formerly_held_out_now_development": 8,
            "independent_validation": False,
            "partial_metrics_separate": True,
        },
        "exclusions": exclusions,
        "model_load_ms": round(encoder.load_ms, 3),
        "prototype_encoding_ms": round(encoder.prototype_encoding_ms, 3),
        "peak_process_memory_mb": round(after_rss / rss_unit, 3),
        "incremental_peak_memory_mb": round((after_rss - before_rss) / rss_unit, 3),
        "embedding_origins": {video_id: row["origin"] for video_id, row in evidence.items()},
        "all_window_coverage": {
            video_id: {
                key: row[key]
                for key in [
                    "all_window_count",
                    "source_cue_count",
                    "covered_source_cue_count",
                    "max_encoded_tokens",
                    "silent_truncation_count",
                    "encoding_and_scoring_ms",
                ]
            }
            for video_id, row in evidence.items()
        },
        "comparisons": summaries,
        "acceptance": decisions,
        "changes_vs_contextual": {
            name: regressions(summary, reference) for name, summary in summaries.items()
        },
        "selected_detector_for_selected_case_preview": selected,
        "confirmed_interval_only": {
            name: confirmed_interval_metrics(detector, qf, json.loads(ANNOTATION.read_text()))
            for name, detector in detectors.items()
        }
        if qf
        else {"status": "missing_saved_transcript"},
        "hosted_inference_calls": 0,
        "supadata_requests": 0,
        "service_spend_usd": 0,
    }
    args.evidence_output.parent.mkdir(parents=True, exist_ok=True)
    args.evidence_output.write_text(json.dumps(evidence, indent=2, allow_nan=False) + "\n")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, allow_nan=False) + "\n")
    for name, summary in summaries.items():
        print(
            f"{name}: incorrect={summary['incorrect_predicted_seconds']}; "
            f"negative_skips={summary['negative_videos_with_any_predicted_skip']}/9; "
            f"missed={summary['missed_promotional_seconds']}; "
            f"matches={summary['matched_segment_count']}; "
            f"boundary={summary['mean_start_boundary_error_seconds']}/"
            f"{summary['mean_end_boundary_error_seconds']}; "
            f"runtime_ms={summary['detection_runtime_ms']}"
        )
    print("Selected for selected-case preview:", selected)


if __name__ == "__main__":
    main()
