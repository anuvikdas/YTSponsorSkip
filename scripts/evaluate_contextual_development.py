#!/usr/bin/env python3
"""Compare unchanged rules and contextual continuity on reviewed development videos."""

import argparse
import csv
import json
import sys
import time
from dataclasses import asdict
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend/src"))
sys.path.insert(0, str(ROOT / "scripts"))

from evaluate_detector import sha256, summarize_rows, usable_transcript  # noqa: E402
from ytsponsorskip.contextual_detector import ContextualPromotionDetector  # noqa: E402
from ytsponsorskip.detection_service import validate_transcript  # noqa: E402
from ytsponsorskip.detector import PromotionDetector, Sensitivity  # noqa: E402
from ytsponsorskip.evaluation import (  # noqa: E402
    calculate_video_metrics,
    playback_eligible_intervals,
)

VIDEOS = ROOT / "data/validation/revised-2026-10-19/videos.csv"
SEGMENTS = ROOT / "data/validation/revised-2026-10-19/segments.csv"
QF = ROOT / "results/development-transcripts/qf7ws2DF-zk.json"
FROZEN_REPORT = ROOT / "data/evaluation/held-out-rules-frozen-2026-10-20.json"


def load_data():
    with VIDEOS.open(newline="", encoding="utf-8") as source:
        videos = [row for row in csv.DictReader(source) if row["review_status"] == "reviewed"]
    labels = {video["video_id"]: [] for video in videos}
    with SEGMENTS.open(newline="", encoding="utf-8") as source:
        for row in csv.DictReader(source):
            if row["video_id"] in labels:
                labels[row["video_id"]].append(
                    (float(row["start_seconds"]), float(row["end_seconds"]))
                )
    transcripts, hashes, exclusions = {}, {}, []
    for video in videos:
        video_id = video["video_id"]
        path = ROOT / "data/transcripts" / video["split"] / f"{video_id}.json"
        if not path.exists():
            exclusions.append({"video_id": video_id, "reason": "missing_saved_transcript"})
            continue
        transcript = usable_transcript(json.loads(path.read_text(encoding="utf-8")))
        if transcript is None:
            exclusions.append({"video_id": video_id, "reason": "unusable_saved_transcript"})
            continue
        validate_transcript(transcript, video_id)
        transcripts[video_id] = transcript
        hashes[video_id] = sha256(path)
    return videos, labels, transcripts, hashes, exclusions


def evaluate(detector, videos, labels, transcripts, mode):
    rows = []
    runtime_ms = 0.0
    for video in videos:
        video_id = video["video_id"]
        if video_id not in transcripts:
            continue
        # Detector sees original transcript only. Manual boundaries enter below, after detect().
        started = time.perf_counter()
        detection = detector.detect(transcripts[video_id], mode)
        duration_ms = (time.perf_counter() - started) * 1000
        runtime_ms += duration_ms
        predictions = playback_eligible_intervals(detection.intervals)
        metrics = calculate_video_metrics(
            video_id=video_id,
            promotion_status=video["promotion_status"],
            predictions=predictions,
            annotations=labels[video_id],
        )
        rows.append(
            {
                **asdict(metrics),
                "split_origin": video["split"],
                "annotations": [list(item) for item in labels[video_id]],
                "predictions": [asdict(item) for item in predictions],
                "raw_prediction_count": len(detection.intervals),
                "runtime_ms": round(duration_ms, 3),
            }
        )
    return summarize_rows(rows, runtime_ms)


def partial_probe(detector):
    if not QF.exists():
        return {"video_id": "qf7ws2DF-zk", "status": "transcript_unavailable"}
    transcript = usable_transcript(json.loads(QF.read_text(encoding="utf-8")))
    if transcript is None:
        return {"video_id": "qf7ws2DF-zk", "status": "transcript_unusable"}
    validate_transcript(transcript, "qf7ws2DF-zk")
    detection = detector.detect(transcript, Sensitivity.CONSERVATIVE)
    return {
        "video_id": "qf7ws2DF-zk",
        "status": "partial_opening_only",
        "transcript_sha256": sha256(QF),
        "approximate_user_start_seconds": 1331,
        "predictions": [asdict(item) for item in detection.intervals],
        "note": "No end label; excluded from complete-interval and full-video metrics.",
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        parser.error("Output exists; refusing to overwrite a comparison")
    videos, labels, transcripts, hashes, exclusions = load_data()
    if len(videos) != 22 or len(transcripts) != 22:
        raise SystemExit(
            f"Expected 22 reviewed saved inputs; got {len(videos)} / {len(transcripts)}"
        )
    detectors = {
        "frozen_rules": PromotionDetector(),
        "contextual_v1": ContextualPromotionDetector(),
    }
    result = {
        "schema_version": 1,
        "generated_at_utc": datetime.now(UTC).isoformat(),
        "scope": {
            "reviewed_tune_videos": 14,
            "retired_held_out_videos_now_development": 8,
            "partial_reviews_in_complete_metrics": False,
            "remaining_untouched_final_test_videos": 0,
            "manual_boundaries_supplied_to_detector": False,
            "auto_skipping_enabled": False,
            "playback_gate": "final merged interval duration strictly greater than 3 seconds",
        },
        "source_hashes": {
            "videos_csv": sha256(VIDEOS),
            "segments_csv": sha256(SEGMENTS),
            "frozen_heldout_report": sha256(FROZEN_REPORT),
            "transcripts": hashes,
        },
        "detector_source_hashes": {
            "frozen_rules": sha256(ROOT / "backend/src/ytsponsorskip/detector.py"),
            "contextual_v1": sha256(ROOT / "backend/src/ytsponsorskip/contextual_detector.py"),
        },
        "exclusions": exclusions,
        "modes": {},
        "partial_opening_probe": {},
    }
    for mode in (Sensitivity.CONSERVATIVE, Sensitivity.AGGRESSIVE):
        result["modes"][mode.value] = {
            name: evaluate(detector, videos, labels, transcripts, mode)
            for name, detector in detectors.items()
        }
    result["partial_opening_probe"] = {
        name: partial_probe(detector) for name, detector in detectors.items()
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    for mode, comparisons in result["modes"].items():
        for name, summary in comparisons.items():
            print(
                f"{mode} {name}: videos={summary['evaluated_video_count']} "
                f"incorrect={summary['incorrect_predicted_seconds']} "
                f"negative_skips={summary['negative_videos_with_any_predicted_skip']}/"
                f"{summary['evaluated_negative_video_count']} "
                f"missed={summary['missed_promotional_seconds']} "
                f"matched={summary['matched_segment_count']} "
                f"start/end_mae={summary['mean_start_boundary_error_seconds']}/"
                f"{summary['mean_end_boundary_error_seconds']} "
                f"runtime_ms={summary['detection_runtime_ms']}"
            )


if __name__ == "__main__":
    main()
