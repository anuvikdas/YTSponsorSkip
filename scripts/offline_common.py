"""Tune-only data and provenance helpers. No acquisition or inference clients."""

import csv
import hashlib
import json
import math
from dataclasses import asdict
from pathlib import Path

from evaluate_detector import sha256, usable_transcript
from ytsponsorskip.detector import RulesWindowClassifier, assemble_candidates, build_windows
from ytsponsorskip.evaluation import merge_ranges

ROOT = Path(__file__).resolve().parents[1]
DETECTOR_SOURCE = ROOT / "backend/src/ytsponsorskip/detector.py"


def canonical_hash(value):
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
    ).hexdigest()


def load_tune(
    source_dir=ROOT / "data/transcripts/tune",
    videos_path=ROOT / "data/validation/videos.csv",
    segments_path=ROOT / "data/validation/segments.csv",
):
    """Filter video metadata before opening transcripts or consuming segment values."""
    with videos_path.open() as source:
        videos = [
            row
            for row in csv.DictReader(source)
            if row["split"] == "tune" and row["review_status"] == "reviewed"
        ]
    ids = {row["video_id"] for row in videos}
    labels = {video_id: [] for video_id in ids}
    with segments_path.open() as source:
        for row in csv.DictReader(source):
            if row["video_id"] in ids:
                labels[row["video_id"]].append(
                    (float(row["start_seconds"]), float(row["end_seconds"]))
                )
    transcripts, documents, hashes, exclusions = {}, {}, {}, []
    for video in videos:
        video_id = video["video_id"]
        path = source_dir / f"{video_id}.json"
        if not path.exists():
            exclusions.append({"video_id": video_id, "reason": "missing_saved_transcript"})
            continue
        document = json.loads(path.read_text())
        transcript = usable_transcript(document)
        if transcript is None or transcript.video_id != video_id:
            raise ValueError(f"Invalid transcript: {video_id}")
        previous_id, previous_start = -1, -1.0
        for snippet in transcript.snippets:
            if (
                snippet.index <= previous_id
                or snippet.start_seconds < previous_start
                or not snippet.text
                or not math.isfinite(snippet.start_seconds)
                or not math.isfinite(snippet.duration_seconds)
                or snippet.start_seconds < 0
                or snippet.duration_seconds < 0
            ):
                raise ValueError(f"Invalid source cue: {video_id}/{snippet.index}")
            previous_id, previous_start = snippet.index, snippet.start_seconds
        transcripts[video_id] = transcript
        documents[video_id] = document
        hashes[video_id] = sha256(path)
    return videos, labels, transcripts, documents, hashes, exclusions


def subtract_ranges(left, right):
    """Half-open set difference, retaining exact error locations as well as totals."""
    output = []
    for start, end in merge_ranges(left):
        cursor = start
        for other_start, other_end in merge_ranges(right):
            if other_end <= cursor or other_start >= end:
                continue
            if other_start > cursor:
                output.append((cursor, other_start))
            cursor = max(cursor, other_end)
            if cursor >= end:
                break
        if cursor < end:
            output.append((cursor, end))
    return output


def trace_rules(transcript, mode):
    """Label-free stage trace. Evaluation intersects labels only after this returns."""
    classifier = RulesWindowClassifier()
    windows = build_windows(transcript)
    scores = tuple(classifier.score(window) for window in windows)
    candidates = assemble_candidates(windows, scores, classifier, mode)
    by_id = {snippet.index: snippet for snippet in transcript.snippets}
    ranges = [
        (
            min(by_id[i].start_seconds for i in candidate.snippet_indices),
            max(by_id[i].end_seconds for i in candidate.snippet_indices),
        )
        for candidate in candidates
    ]
    return {
        "candidate_ranges": merge_ranges(ranges),
        "candidates": [asdict(candidate) for candidate in candidates],
        "highest_score_window": asdict(
            max(zip(windows, scores, strict=True), key=lambda pair: pair[1].score)[0]
        )
        if windows
        else None,
    }


def verify_saved_evaluation(report, videos, hashes):
    """Require an exclusively reviewed-tune report bound to the exact saved files."""
    if (
        report["scope"]["split"] != "tune"
        or report["scope"]["held_out_used"]
        or report["scope"]["partial_reviews_used"]
    ):
        raise ValueError("Only fully reviewed tune evaluation is accepted")
    allowed = {video["video_id"] for video in videos}
    source_hashes = {}
    for source in report["inventory"]["sources"]:
        for video_id in source["video_ids"]:
            if video_id in source_hashes and source_hashes[video_id] != source["sha256"]:
                raise ValueError("Ambiguous transcript provenance")
            source_hashes[video_id] = source["sha256"]
    for mode in ("conservative", "aggressive"):
        seen = set()
        for row in report["modes"][mode]["per_video"]:
            video_id = row["video_id"]
            if video_id not in allowed or video_id in seen:
                raise ValueError("Out-of-scope or duplicate video in recording")
            seen.add(video_id)
            if source_hashes.get(video_id) != hashes.get(video_id) or video_id not in hashes:
                raise ValueError(f"Transcript hash mismatch: {video_id}")


def write_new(path, text):
    """Never overwrite a preserved evaluation or review artifact implicitly."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8") as target:
        target.write(text)
