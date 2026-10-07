#!/usr/bin/env python3
import argparse
import csv
import hashlib
import json
import statistics
import time
from collections import defaultdict
from dataclasses import asdict
from pathlib import Path
from typing import Any

from ytsponsorskip.detector import PromotionDetector, Sensitivity
from ytsponsorskip.domain import Transcript, TranscriptSnippet
from ytsponsorskip.evaluation import TimeRange, calculate_video_metrics


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def response_entries(document: dict[str, Any]) -> list[dict[str, Any]]:
    if isinstance(document.get("results"), list):
        return list(document["results"])
    return [document]


def entry_video_id(entry: dict[str, Any]) -> str | None:
    video_id = entry.get("video_id")
    if isinstance(video_id, str) and video_id:
        return video_id
    return None


def usable_transcript(entry: dict[str, Any]) -> Transcript | None:
    video_id = entry_video_id(entry)
    snippets = entry.get("snippets")
    if not video_id or not isinstance(snippets, list) or not snippets:
        return None
    metadata = entry.get("transcript") if isinstance(entry.get("transcript"), dict) else {}
    try:
        normalized_snippets = tuple(
            TranscriptSnippet(
                index=int(snippet["index"]),
                text=str(snippet["text"]),
                start_seconds=float(snippet["start_seconds"]),
                duration_seconds=float(snippet["duration_seconds"]),
            )
            for snippet in snippets
        )
    except (KeyError, TypeError, ValueError):
        return None
    caption_type = str(metadata.get("caption_type", entry.get("caption_type", "unknown")))
    raw_is_generated = metadata.get("is_generated")
    if isinstance(raw_is_generated, bool):
        is_generated: bool | None = raw_is_generated
    elif caption_type == "generated":
        is_generated = True
    elif caption_type == "manual":
        is_generated = False
    else:
        is_generated = None
    return Transcript(
        video_id=video_id,
        language=str(metadata.get("language", entry.get("language", "unknown"))),
        language_code=str(metadata.get("language_code", entry.get("language_code", "unknown"))),
        is_generated=is_generated,
        snippets=normalized_snippets,
        provider=str(metadata.get("provider", "saved-response")),
        provider_version=str(
            metadata.get("provider_version", entry.get("provider_version", "unknown"))
        ),
    )


def inventory_sources(paths: list[Path]) -> dict[str, Any]:
    transcripts: dict[str, Transcript] = {}
    seen_video_ids: set[str] = set()
    metadata_only_ids: set[str] = set()
    failure_codes: defaultdict[str, set[str]] = defaultdict(set)
    source_records = []

    for path in paths:
        document = json.loads(path.read_text(encoding="utf-8"))
        entries = response_entries(document)
        usable_count = 0
        for entry in entries:
            video_id = entry_video_id(entry)
            if video_id:
                seen_video_ids.add(video_id)
            transcript = usable_transcript(entry)
            if transcript is not None:
                transcripts.setdefault(transcript.video_id, transcript)
                metadata_only_ids.discard(transcript.video_id)
                usable_count += 1
            elif video_id and (entry.get("success") or entry.get("status") == "ready"):
                metadata_only_ids.add(video_id)
            failure_code = entry.get("failure_code")
            if not failure_code and isinstance(entry.get("error"), dict):
                failure_code = entry["error"].get("code")
            if video_id and failure_code:
                failure_codes[video_id].add(str(failure_code))
        source_records.append(
            {
                "path": str(path),
                "sha256": sha256(path),
                "entry_count": len(entries),
                "usable_entry_count": usable_count,
                "video_ids": [
                    video_id
                    for entry in entries
                    if (video_id := entry_video_id(entry)) is not None
                ],
            }
        )

    return {
        "transcripts": transcripts,
        "seen_video_ids": sorted(seen_video_ids),
        "metadata_only_ids": sorted(metadata_only_ids - set(transcripts)),
        "failure_codes": {video_id: sorted(codes) for video_id, codes in failure_codes.items()},
        "sources": source_records,
    }


def load_labels(
    videos_path: Path, segments_path: Path
) -> tuple[list[dict[str, str]], dict[str, list[TimeRange]]]:
    with videos_path.open(newline="", encoding="utf-8") as source:
        videos = list(csv.DictReader(source))
    segments: defaultdict[str, list[TimeRange]] = defaultdict(list)
    with segments_path.open(newline="", encoding="utf-8") as source:
        for row in csv.DictReader(source):
            segments[row["video_id"]].append(
                (float(row["start_seconds"]), float(row["end_seconds"]))
            )
    return videos, dict(segments)


def summarize_mode(
    mode: Sensitivity,
    videos: list[dict[str, str]],
    segments: dict[str, list[TimeRange]],
    transcripts: dict[str, Transcript],
) -> dict[str, Any]:
    detector = PromotionDetector()
    per_video = []
    runtime_ms = 0.0
    for video in videos:
        transcript = transcripts.get(video["video_id"])
        if transcript is None:
            continue
        started = time.perf_counter()
        detection = detector.detect(transcript, mode)
        video_runtime_ms = (time.perf_counter() - started) * 1000
        runtime_ms += video_runtime_ms
        annotations = segments.get(video["video_id"], [])
        metrics = calculate_video_metrics(
            video_id=video["video_id"],
            promotion_status=video["promotion_status"],
            predictions=detection.intervals,
            annotations=annotations,
        )
        per_video.append(
            {
                **asdict(metrics),
                "title": video["title"],
                "annotations": [
                    {"start_seconds": start, "end_seconds": end}
                    for start, end in annotations
                ],
                "prediction_count": len(detection.intervals),
                "predictions": [asdict(interval) for interval in detection.intervals],
                "window_count": detection.window_count,
                "detection_runtime_ms": round(video_runtime_ms, 3),
            }
        )

    matches = [match for row in per_video for match in row["matches"]]
    negative_rows = [row for row in per_video if row["promotion_status"] == "none"]
    if not per_video:
        return {
            "evaluated_video_count": 0,
            "incorrect_predicted_seconds": None,
            "negative_videos_with_any_predicted_skip": None,
            "evaluated_negative_video_count": 0,
            "missed_promotional_seconds": None,
            "matched_segment_count": None,
            "mean_start_boundary_error_seconds": None,
            "mean_end_boundary_error_seconds": None,
            "detection_runtime_ms": None,
            "per_video": [],
        }
    return {
        "evaluated_video_count": len(per_video),
        "incorrect_predicted_seconds": round(
            sum(row["incorrect_predicted_seconds"] for row in per_video), 3
        ),
        "negative_videos_with_any_predicted_skip": sum(
            row["predicted_seconds"] > 0 for row in negative_rows
        ),
        "evaluated_negative_video_count": len(negative_rows),
        "missed_promotional_seconds": round(
            sum(row["missed_promotional_seconds"] for row in per_video), 3
        ),
        "matched_segment_count": len(matches),
        "mean_start_boundary_error_seconds": round(
            statistics.mean(match["start_error_seconds"] for match in matches), 3
        )
        if matches
        else None,
        "mean_end_boundary_error_seconds": round(
            statistics.mean(match["end_error_seconds"] for match in matches), 3
        )
        if matches
        else None,
        "detection_runtime_ms": round(runtime_ms, 3),
        "per_video": per_video,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, action="append", default=[])
    parser.add_argument("--source-dir", type=Path, action="append", default=[])
    parser.add_argument("--videos", type=Path, default=Path("data/validation/videos.csv"))
    parser.add_argument("--segments", type=Path, default=Path("data/validation/segments.csv"))
    parser.add_argument("--output", type=Path)
    parser.add_argument("--detector-commit", default="unknown")
    args = parser.parse_args()

    source_paths = list(args.source)
    for directory in args.source_dir:
        source_paths.extend(
            path for path in sorted(directory.glob("*.json")) if path.name != "import-report.json"
        )
    inventory = inventory_sources(source_paths)
    videos, segments = load_labels(args.videos, args.segments)
    tune_reviewed = [
        video
        for video in videos
        if video["split"] == "tune" and video["review_status"] == "reviewed"
    ]
    tune_partial = [
        video
        for video in videos
        if video["split"] == "tune" and video["review_status"] == "in_progress"
    ]
    transcripts: dict[str, Transcript] = inventory.pop("transcripts")
    usable_ids = sorted({video["video_id"] for video in tune_reviewed} & set(transcripts))
    exclusions = []
    for video in tune_reviewed:
        video_id = video["video_id"]
        if video_id in transcripts:
            continue
        if video_id in inventory["metadata_only_ids"]:
            reason = "saved_success_has_no_snippets"
        elif video_id in inventory["failure_codes"]:
            reason = "acquisition_failure:" + ",".join(inventory["failure_codes"][video_id])
        else:
            reason = "no_saved_transcript"
        exclusions.append({"video_id": video_id, "reason": reason})

    report = {
        "detector": {
            "baseline_commit": args.detector_commit,
            "source_path": "backend/src/ytsponsorskip/detector.py",
            "source_sha256": sha256(Path("backend/src/ytsponsorskip/detector.py")),
            "classifier": "RulesWindowClassifier",
            "window_seconds": 30.0,
            "overlap_seconds": 15.0,
            "conservative_join_gap_seconds": 20.0,
            "aggressive_join_gap_seconds": 30.0,
        },
        "scope": {
            "split": "tune",
            "held_out_used": False,
            "partial_reviews_used": False,
            "rule_development_note": "Manual segment timestamps are evaluation targets only.",
            "timing_note": (
                "Imported source contains starts only. duration_seconds is a derived analysis "
                "span, not an exact caption or speech boundary."
            ),
        },
        "inventory": inventory,
        "coverage": {
            "reviewed_tune_videos": len(tune_reviewed),
            "usable_tune_transcripts": len(usable_ids),
            "usable_tune_video_ids": usable_ids,
            "excluded_reviewed_tune_videos": exclusions,
            "excluded_partial_tune_videos": [video["video_id"] for video in tune_partial],
        },
        "modes": {
            mode.value: summarize_mode(mode, tune_reviewed, segments, transcripts)
            for mode in Sensitivity
        },
    }
    rendered = json.dumps(report, indent=2) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered, encoding="utf-8")
    print(rendered, end="")


if __name__ == "__main__":
    main()
