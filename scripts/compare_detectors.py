#!/usr/bin/env python3
"""Run unchanged local rules and/or replay saved predictions; never call a model."""

import argparse
import json
import math
import platform
import subprocess
import time
from dataclasses import asdict
from datetime import UTC, datetime
from pathlib import Path

from evaluate_detector import sha256, summarize_mode, summarize_rows
from offline_common import (
    DETECTOR_SOURCE,
    ROOT,
    canonical_hash,
    load_tune,
    verify_saved_evaluation,
    write_new,
)
from ytsponsorskip.detector import DetectedInterval, Sensitivity
from ytsponsorskip.evaluation import calculate_video_metrics
from ytsponsorskip.model_detection_contract import (
    ModelDetectionRequest,
    ModelDetectionResponse,
    snippet_ids_to_time_range,
    validate_model_response,
)


def recorded_intervals(rows):
    intervals = []
    for row in rows:
        start, end = row["start_seconds"], row["end_seconds"]
        if (
            isinstance(start, bool)
            or isinstance(end, bool)
            or not isinstance(start, (float, int))
            or not isinstance(end, (float, int))
            or not math.isfinite(start)
            or not math.isfinite(end)
            or start < 0
            or end <= start
        ):
            raise ValueError("Invalid recorded interval; refusing to silently drop it")
        intervals.append(
            DetectedInterval(
                start,
                end,
                row.get("score", 0),
                tuple(row.get("evidence", [])),
                tuple(row.get("snippet_indices", [])),
            )
        )
    return tuple(intervals)


def model_record_intervals(record, transcript, transcript_hash):
    """Validate recorded provider output against current source, without inference."""
    if record["transcript_sha256"] != transcript_hash:
        raise ValueError("Model recording transcript hash mismatch")
    if record["origin"] not in ("recorded_model_response", "synthetic_fixture"):
        raise ValueError("Model recording must declare its origin")
    request = ModelDetectionRequest.model_validate(record["request"])
    response = ModelDetectionResponse.model_validate(record["response"])
    if request.video_id != transcript.video_id or request.language_code != transcript.language_code:
        raise ValueError("Model recording video/language mismatch")
    source = {snippet.index: snippet for snippet in transcript.snippets}
    for snippet in request.snippets:
        original = source.get(snippet.snippet_id)
        if original is None or (snippet.text, snippet.start_seconds, snippet.duration_seconds) != (
            original.text,
            original.start_seconds,
            original.duration_seconds,
        ):
            raise ValueError("Model input differs from original source cue")
    validate_model_response(request, response)
    intervals = []
    for segment in response.segments:
        submitted_ids = {snippet.snippet_id for snippet in request.snippets}
        if any(
            segment.start_snippet_id <= index <= segment.end_snippet_id
            and index not in submitted_ids
            for index in source
        ):
            raise ValueError("Model segment crosses source cues not supplied in the request")
        start, end = snippet_ids_to_time_range(
            request.snippets, segment.start_snippet_id, segment.end_snippet_id
        )
        intervals.extend(
            recorded_intervals(
                [
                    {
                        "start_seconds": start,
                        "end_seconds": end,
                        "evidence": [
                            segment.reason_code,
                            segment.ownership.value,
                            segment.kind.value,
                        ],
                        "snippet_indices": list(segment.evidence_snippet_ids),
                    }
                ]
            )
        )
    return request, response, tuple(intervals)


def replay_mode(mode, videos, labels, transcripts, hashes, records, *, model=False):
    rows, exclusions = [], []
    started = time.perf_counter()
    for video in videos:
        video_id = video["video_id"]
        if video_id not in transcripts:
            continue
        record = records.get((mode.value, video_id))
        if record is None:
            exclusions.append({"video_id": video_id, "reason": "missing_recorded_output"})
            continue
        row_started = time.perf_counter()
        provenance = {}
        if model:
            request, response, intervals = model_record_intervals(
                record, transcripts[video_id], hashes[video_id]
            )
            if request.sensitivity != mode:
                raise ValueError("Model recording sensitivity mismatch")
            provenance = {
                "origin": record["origin"],
                "model_version": response.model_version,
                "prompt_version": request.prompt_version,
                "request_sha256": canonical_hash(record["request"]),
                "response_sha256": canonical_hash(record["response"]),
                "input_snippet_count": len(request.snippets),
                "source_snippet_count": len(transcripts[video_id].snippets),
                "recorded_provider_runtime_ms": record.get("provider_runtime_ms"),
            }
        else:
            intervals = recorded_intervals(record["predictions"])
            provenance = {"recorded_detection_runtime_ms": record.get("detection_runtime_ms")}
        metrics = calculate_video_metrics(
            video_id=video_id,
            promotion_status=video["promotion_status"],
            predictions=intervals,
            annotations=labels[video_id],
        )
        rows.append(
            {
                **asdict(metrics),
                "title": video["title"],
                "transcript_sha256": hashes[video_id],
                "predictions": [asdict(interval) for interval in intervals],
                "prediction_count": len(intervals),
                "detection_runtime_ms": None,
                "replay_validation_and_scoring_ms": round(
                    (time.perf_counter() - row_started) * 1000, 3
                ),
                **provenance,
            }
        )
    summary = summarize_rows(rows, 0)
    summary["detection_runtime_ms"] = None
    summary["replay_validation_and_scoring_ms"] = round((time.perf_counter() - started) * 1000, 3)
    summary["excluded_outputs"] = exclusions
    return summary


def paired_quality(runs):
    """Compare only shared evaluated videos; missing recordings are not negatives."""
    result = {}
    for mode in Sensitivity:
        rows = [run["modes"][mode.value]["per_video"] for run in runs]
        shared = set.intersection(*({row["video_id"] for row in group} for group in rows))
        summaries = []
        for run, group in zip(runs, rows, strict=True):
            summary = summarize_rows([row for row in group if row["video_id"] in shared], 0)
            summary.pop("per_video")
            summary.pop("detection_runtime_ms")
            summaries.append({"name": run["name"], "quality": summary})
        result[mode.value] = {"video_ids": sorted(shared), "runs": summaries}
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-dir", type=Path, default=ROOT / "data/transcripts/tune")
    parser.add_argument("--replay-evaluation", type=Path, action="append", default=[])
    parser.add_argument("--replay-model", type=Path, action="append", default=[])
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        parser.error("Output exists; choose a new filename to preserve prior runs")
    videos, labels, transcripts, _, hashes, exclusions = load_tune(args.source_dir)
    git_head = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    config = {
        "classifier": "RulesWindowClassifier",
        "detector_sha256": sha256(DETECTOR_SOURCE),
        "window_seconds": 30,
        "overlap_seconds": 15,
        "configuration_version": "rules-3c35ceb-defaults",
        "semantics": "All other constants and policy are bound by detector_sha256",
    }
    rules = {
        "name": "current-rules",
        "execution": "local_rules_execution",
        "config": config,
        "config_sha256": canonical_hash(config),
        "modes": {},
    }
    for mode in Sensitivity:
        summary = summarize_mode(mode, videos, labels, transcripts)
        for row in summary["per_video"]:
            row["transcript_sha256"] = hashes[row["video_id"]]
        rules["modes"][mode.value] = summary
    runs = [rules]
    for path in args.replay_evaluation:
        saved = json.loads(path.read_text())
        verify_saved_evaluation(saved, videos, hashes)
        records = {
            (mode, row["video_id"]): row
            for mode, summary in saved["modes"].items()
            for row in summary["per_video"]
        }
        runs.append(
            {
                "name": path.stem,
                "execution": "recorded_evaluation_replay",
                "recording_sha256": sha256(path),
                "config": saved["detector"],
                "config_sha256": canonical_hash(saved["detector"]),
                "modes": {
                    mode.value: replay_mode(mode, videos, labels, transcripts, hashes, records)
                    for mode in Sensitivity
                },
            }
        )
    allowed = set(hashes)
    for path in args.replay_model:
        saved = json.loads(path.read_text())
        records = {}
        for record in saved["records"]:
            key = (record["request"]["sensitivity"], record["request"]["video_id"])
            if key[1] not in allowed or key[0] not in Sensitivity or key in records:
                raise ValueError("Out-of-scope, invalid mode, or duplicate model recording")
            records[key] = record
        runs.append(
            {
                "name": path.stem,
                "execution": "recorded_model_replay_no_calls",
                "recording_sha256": sha256(path),
                "config": saved["config"],
                "config_sha256": canonical_hash(saved["config"]),
                "modes": {
                    mode.value: replay_mode(
                        mode, videos, labels, transcripts, hashes, records, model=True
                    )
                    for mode in Sensitivity
                },
            }
        )
    report = {
        "schema_version": 1,
        "created_at": datetime.now(UTC).isoformat(),
        "git_head": git_head,
        "python_version": platform.python_version(),
        "scope": "fully_reviewed_tune_only",
        "live_model_calls": 0,
        "transcript_hashes": hashes,
        "corpus_sha256": canonical_hash(hashes),
        "label_subset_sha256": canonical_hash(
            {
                "videos": videos,
                "segments": labels,
            }
        ),
        "evaluation_code_sha256": sha256(ROOT / "backend/src/ytsponsorskip/evaluation.py"),
        "runner_sha256": sha256(Path(__file__)),
        "aggregation_sha256": sha256(ROOT / "scripts/evaluate_detector.py"),
        "common_helpers_sha256": sha256(ROOT / "scripts/offline_common.py"),
        "model_contract_sha256": sha256(
            ROOT / "backend/src/ytsponsorskip/model_detection_contract.py"
        ),
        "acquisition_exclusions": exclusions,
        "paired_quality": paired_quality(runs),
        "runs": runs,
    }
    write_new(args.output, json.dumps(report, indent=2, allow_nan=False) + "\n")
    print(f"Saved {len(runs)} runs to {args.output}; live model calls: 0")


if __name__ == "__main__":
    main()
