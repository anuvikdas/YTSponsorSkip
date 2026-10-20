#!/usr/bin/env python3
"""Evaluate the frozen rules once on reviewed held-out inputs, without tuning them."""

import argparse
import json
import statistics
import sys
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend/src"))

from evaluate_detector import (  # noqa: E402
    inventory_sources,
    load_labels,
    sha256,
    summarize_mode,
)
from ytsponsorskip.detection_service import transcript_identity, validate_transcript  # noqa: E402
from ytsponsorskip.detector import Sensitivity  # noqa: E402

FREEZE = {
    "backend/src/ytsponsorskip/detector.py": (
        "764f1dba6f1929b1e00bbe5785f183f91a496bf10ce472603a7552bea185e62c"
    ),
    "backend/src/ytsponsorskip/evaluation.py": (
        "b211aa4f02ef8aab2e3db6b1235285d761ad327007de81c6953c848cdbe191e7"
    ),
    "scripts/evaluate_detector.py": (
        "54578328abafc6b863509e4902f0ce885d09727ba80d70828d6d02ec2c4c2d0e"
    ),
    "data/validation/revised-2026-10-19/videos.csv": (
        "e931d4969aae5c015230b4afe9b75adfd59f6974432e6548e6859004230b3fe1"
    ),
    "data/validation/revised-2026-10-19/segments.csv": (
        "f5ae20577aca2acbd8dc8c4c576eeb7bd70b6d752784423c9547b109427b366c"
    ),
}
TRANSCRIPTS = ROOT / "data/transcripts/held_out"
RECORDS = ROOT / "results/heldout-acquisition"
OUTPUT = ROOT / "data/evaluation/held-out-rules-frozen-2026-10-20.json"


def augment(summary: dict) -> None:
    rows = summary["per_video"]
    summary["unmatched_predicted_segment_count"] = sum(
        len(row.get("predictions", row.get("eligible_intervals", []))) - len(row["matches"])
        for row in rows
    )
    summary["unmatched_annotated_segment_count"] = sum(
        len(row.get("annotations", [])) - len(row["matches"])
        for row in rows
        if "annotations" in row
    )
    annotated = sum(row["annotated_seconds"] for row in rows)
    summary["annotated_seconds"] = round(annotated, 3)
    summary["missed_fraction"] = (
        round(summary["missed_promotional_seconds"] / annotated, 5) if annotated else None
    )


def run() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=OUTPUT)
    args = parser.parse_args()
    for relative, expected in FREEZE.items():
        if sha256(ROOT / relative) != expected:
            raise SystemExit(f"Frozen source changed: {relative}; evaluation refused")
    if args.output.exists():
        raise SystemExit(f"Output exists; refusing to overwrite an evaluation: {args.output}")

    videos, segments = load_labels(
        ROOT / "data/validation/revised-2026-10-19/videos.csv",
        ROOT / "data/validation/revised-2026-10-19/segments.csv",
    )
    reviewed = [
        row for row in videos if row["split"] == "held_out" and row["review_status"] == "reviewed"
    ]
    if len(reviewed) != 8:
        raise SystemExit("Expected exactly eight fully reviewed held-out videos")
    ids = {row["video_id"] for row in reviewed}
    paths = sorted(TRANSCRIPTS.glob("*.json"))
    if any(path.stem not in ids for path in paths):
        raise SystemExit("Held-out transcript directory contains a non-held-out ID")
    inventory = inventory_sources(paths)
    transcripts = inventory.pop("transcripts")
    excluded = []
    for row in reviewed:
        video_id = row["video_id"]
        transcript = transcripts.get(video_id)
        if transcript is None:
            excluded.append({"video_id": video_id, "reason": "no_usable_saved_transcript"})
            continue
        validate_transcript(transcript, video_id)
    evaluated = [row for row in reviewed if row["video_id"] in transcripts]

    acquisition = []
    for row in reviewed:
        video_id = row["video_id"]
        path = RECORDS / f"{video_id}.json"
        if not path.exists():
            acquisition.append({"video_id": video_id, "source": "saved_prior", "latency_ms": None})
            continue
        record = json.loads(path.read_text(encoding="utf-8"))
        acquisition.append(
            {
                "video_id": video_id,
                "source": "supadata-native",
                "http_statuses": record["http_statuses"],
                "result": record["result"],
                "error": record["error"],
                "latency_ms": record["latency_ms"],
                "record_sha256": sha256(path),
            }
        )
    latencies = [row["latency_ms"] for row in acquisition if row["latency_ms"] is not None]
    mode = summarize_mode(Sensitivity.CONSERVATIVE, evaluated, segments, transcripts)
    augment(mode)
    augment(mode["playback_policy"])
    # Playback rows omit annotations to avoid duplicate payload; derive unmatched gold
    # counts from reviewed annotation lists, not from predictions.
    playback_rows = mode["playback_policy"]["per_video"]
    mode["playback_policy"]["unmatched_annotated_segment_count"] = sum(
        len(segments.get(row["video_id"], [])) - len(row["matches"]) for row in playback_rows
    )

    report = {
        "schema_version": 1,
        "evaluated_at": datetime.now(UTC).isoformat(),
        "run_kind": "first_frozen_held_out_evaluation",
        "freeze_manifest": "docs/conservative-freeze-2026-10-20.md",
        "frozen_sha256": FREEZE,
        "transcript_provider": "supadata-native unless saved prior",
        "provider_settings": {"mode": "native", "text": False, "language": "en"},
        "source_files": inventory["sources"],
        "transcript_identity_sha256": {
            video_id: transcript_identity(transcript)
            for video_id, transcript in sorted(transcripts.items())
        },
        "coverage": {
            "fully_reviewed_held_out_videos": len(reviewed),
            "usable_transcript_count": len(evaluated),
            "evaluated_video_ids": [row["video_id"] for row in evaluated],
            "excluded": excluded,
        },
        "acquisition": {
            "per_video": acquisition,
            "mean_latency_ms": round(statistics.mean(latencies), 3) if latencies else None,
            "min_latency_ms": min(latencies) if latencies else None,
            "max_latency_ms": max(latencies) if latencies else None,
            "note": (
                "Acquisition latency excludes offline detector runtime; provider "
                "completeness is not independently verified."
            ),
        },
        "detector": {"mode": "conservative", "result": mode},
        "interpretation": {
            "labels_are": "user_manual_annotations_not_independently_verified_truth",
            "conditional_quality": "metrics include only videos with usable transcripts",
            "end_to_end_coverage": f"{len(evaluated)}/{len(reviewed)}",
            "automatic_skipping_enabled": False,
        },
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "coverage": report["coverage"],
                "acquisition": {k: v for k, v in report["acquisition"].items() if k != "per_video"},
                "raw": {k: v for k, v in mode.items() if k not in ("per_video", "playback_policy")},
                "playback": {k: v for k, v in mode["playback_policy"].items() if k != "per_video"},
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    run()
