#!/usr/bin/env python3
import argparse
import csv
import hashlib
import json
import re
import statistics
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path
from urllib.parse import parse_qs, urlparse
from xml.etree import ElementTree
from zipfile import ZipFile

WORD_NAMESPACE = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
RELATIONSHIP_NAMESPACE = (
    "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
)
PACKAGE_RELATIONSHIP_NAMESPACE = (
    "http://schemas.openxmlformats.org/package/2006/relationships"
)
NS = {"w": WORD_NAMESPACE, "r": RELATIONSHIP_NAMESPACE}

STATUS_RE = re.compile(r"^Status:\s*(.+?)\s*\|\s*Caption type:\s*(.+?)\s*$")
TIMESTAMP_RE = re.compile(r"^(?:(\d+):)?(\d+):(\d{2})$")
EMBEDDED_RE = re.compile(
    r"^(?P<timestamp>\d+:\d{2})"
    r"(?P<label>(?:\d+\s+minutes?(?:,\s*\d+\s+seconds?)?|\d+\s+seconds?))"
    r"(?P<text>.*)$"
)
HUMAN_MINUTES_RE = re.compile(
    r"^(?P<minutes>\d+)\s+minutes?(?:,\s*(?P<seconds>\d+)\s+seconds?)?$"
)
HUMAN_SECONDS_RE = re.compile(r"^(?P<seconds>\d+)\s+seconds?$")


def qualified(namespace: str, name: str) -> str:
    return f"{{{namespace}}}{name}"


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def parse_timestamp(value: str) -> int | None:
    match = TIMESTAMP_RE.fullmatch(value.strip())
    if match is None:
        return None
    hours = int(match.group(1) or 0)
    minutes = int(match.group(2))
    seconds = int(match.group(3))
    if seconds >= 60:
        return None
    return hours * 3600 + minutes * 60 + seconds


def parse_human_timestamp(value: str) -> int | None:
    if match := HUMAN_MINUTES_RE.fullmatch(value):
        seconds = int(match.group("seconds") or 0)
        if seconds >= 60:
            return None
        return int(match.group("minutes")) * 60 + seconds
    if match := HUMAN_SECONDS_RE.fullmatch(value):
        return int(match.group("seconds"))
    return None


def parse_embedded_line(value: str) -> dict[str, object] | None:
    match = EMBEDDED_RE.fullmatch(value)
    if match is None:
        return None
    start_seconds = parse_timestamp(match.group("timestamp"))
    repeated_seconds = parse_human_timestamp(match.group("label"))
    if start_seconds is None or repeated_seconds != start_seconds:
        return None
    text = match.group("text")
    if not text:
        return None
    return {
        "source_timestamp": match.group("timestamp"),
        "source_human_timestamp": match.group("label"),
        "start_seconds": start_seconds,
        "text": text,
    }


def extract_docx_paragraphs(path: Path) -> list[dict[str, object]]:
    with ZipFile(path) as archive:
        document = ElementTree.fromstring(archive.read("word/document.xml"))
    body = document.find("w:body", NS)
    if body is None:
        raise ValueError("DOCX has no document body")
    paragraphs = []
    for block_index, element in enumerate(body):
        if element.tag != qualified(WORD_NAMESPACE, "p"):
            continue
        text = "".join(node.text or "" for node in element.findall(".//w:t", NS))
        style_node = element.find("./w:pPr/w:pStyle", NS)
        style = (
            style_node.get(qualified(WORD_NAMESPACE, "val"))
            if style_node is not None
            else None
        )
        paragraphs.append({"block_index": block_index, "style": style, "text": text})
    return paragraphs


def split_sections(paragraphs: list[dict[str, object]]) -> list[list[dict[str, object]]]:
    heading_positions = [
        index for index, paragraph in enumerate(paragraphs) if paragraph["style"] == "Heading1"
    ]
    return [
        paragraphs[start : heading_positions[position + 1]]
        if position + 1 < len(heading_positions)
        else paragraphs[start:]
        for position, start in enumerate(heading_positions)
    ]


def looks_like_heading(value: str) -> bool:
    return len(value) <= 60


def repair_bare_seconds(
    payload: list[dict[str, object]], position: int, previous_start: int | None
) -> int | None:
    value = str(payload[position]["text"]).strip()
    if not value.isdigit() or not 0 <= int(value) < 60 or previous_start is None:
        return None
    if position + 2 >= len(payload):
        return None
    next_start = parse_timestamp(str(payload[position + 2]["text"]).strip())
    candidate = int(value)
    if next_start is None or not previous_start < candidate < next_start:
        return None
    return candidate


def parse_alternating_payload(
    payload: list[dict[str, object]],
) -> tuple[list[dict[str, object]], list[dict[str, object]], list[dict[str, object]]]:
    snippets = []
    warnings = []
    excluded = []
    position = 0
    previous_start = None
    while position < len(payload):
        raw_value = str(payload[position]["text"])
        value = raw_value.strip()
        if not value:
            position += 1
            continue
        start_seconds = parse_timestamp(value)
        repaired = False
        if start_seconds is None:
            start_seconds = repair_bare_seconds(payload, position, previous_start)
            repaired = start_seconds is not None
        if start_seconds is None:
            kind = "section_heading" if looks_like_heading(value) else "untimestamped_text"
            excluded.append(
                {
                    "block_index": payload[position]["block_index"],
                    "kind": kind,
                    "text": raw_value,
                }
            )
            if kind == "untimestamped_text":
                warnings.append(
                    {
                        "code": "UNTIMESTAMPED_TRANSCRIPT_TEXT",
                        "block_index": payload[position]["block_index"],
                        "text": raw_value,
                    }
                )
            position += 1
            continue
        if position + 1 >= len(payload):
            warnings.append(
                {
                    "code": "TIMESTAMP_WITHOUT_TEXT",
                    "block_index": payload[position]["block_index"],
                    "source_timestamp": raw_value,
                }
            )
            position += 1
            continue
        text = str(payload[position + 1]["text"])
        if parse_timestamp(text.strip()) is not None or parse_embedded_line(text) is not None:
            warnings.append(
                {
                    "code": "TIMESTAMP_WITHOUT_TEXT",
                    "block_index": payload[position]["block_index"],
                    "source_timestamp": raw_value,
                }
            )
            position += 1
            continue
        source_timestamp = value if not repaired else raw_value
        snippet = {
            "source_timestamp": source_timestamp,
            "start_seconds": start_seconds,
            "text": text,
        }
        if repaired:
            snippet["source_timestamp_repaired_to"] = f"0:{start_seconds:02d}"
            warnings.append(
                {
                    "code": "BARE_SECONDS_TIMESTAMP_REPAIRED",
                    "block_index": payload[position]["block_index"],
                    "source_timestamp": raw_value,
                    "normalized_start_seconds": start_seconds,
                }
            )
        snippets.append(snippet)
        previous_start = start_seconds
        position += 2
    return snippets, warnings, excluded


def parse_embedded_payload(
    payload: list[dict[str, object]],
) -> tuple[list[dict[str, object]], list[dict[str, object]], list[dict[str, object]]]:
    snippets = []
    warnings = []
    excluded = []
    for paragraph in payload:
        raw_value = str(paragraph["text"])
        parsed = parse_embedded_line(raw_value)
        if parsed is not None:
            snippets.append(parsed)
            continue
        if not raw_value.strip():
            continue
        kind = "section_heading" if looks_like_heading(raw_value.strip()) else "unparsed_text"
        excluded.append(
            {
                "block_index": paragraph["block_index"],
                "kind": kind,
                "text": raw_value,
            }
        )
        if kind == "unparsed_text":
            warnings.append(
                {
                    "code": "UNPARSED_EMBEDDED_LINE",
                    "block_index": paragraph["block_index"],
                    "text": raw_value,
                }
            )
    return snippets, warnings, excluded


def derive_analysis_durations(
    snippets: list[dict[str, object]],
) -> tuple[list[dict[str, object]], dict[str, object]]:
    starts = [int(snippet["start_seconds"]) for snippet in snippets]
    positive_deltas = [
        later - earlier
        for earlier, later in zip(starts, starts[1:], strict=False)
        if later > earlier
    ]
    terminal_duration = float(statistics.median(positive_deltas)) if positive_deltas else 1.0
    normalized = []
    for index, snippet in enumerate(snippets):
        start = int(snippet["start_seconds"])
        next_distinct = next((value for value in starts[index + 1 :] if value > start), None)
        if next_distinct is None:
            duration = terminal_duration
            derivation = "per_video_median_positive_start_delta"
        else:
            duration = float(next_distinct - start)
            derivation = "next_distinct_source_start_minus_current_start"
        normalized.append(
            {
                "index": index,
                "text": snippet["text"],
                "start_seconds": float(start),
                "duration_seconds": duration,
                "source_timestamp": snippet["source_timestamp"],
                "source_human_timestamp": snippet.get("source_human_timestamp"),
                "source_timestamp_repaired_to": snippet.get("source_timestamp_repaired_to"),
                "source_duration_seconds": None,
                "duration_is_derived": True,
                "duration_derivation": derivation,
            }
        )
    return normalized, {
        "source_unit": "seconds",
        "source_precision_seconds": 1,
        "source_duration_available": False,
        "normalized_unit": "seconds",
        "duration_available": True,
        "duration_policy": {
            "non_terminal": "next distinct source start minus current start",
            "duplicate_starts": "share the next distinct start, preserving derived overlap",
            "terminal": "per-video median positive consecutive start delta",
            "interpretation": "analysis span only; not an exact caption or speech boundary",
        },
        "terminal_derived_duration_seconds": terminal_duration,
    }


def normalize_status(raw_status: str) -> tuple[str, str | None]:
    lowered = raw_status.strip().lower()
    if lowered in {"complete", "completed"}:
        return "complete", None
    if lowered == "competed":
        return "complete", "STATUS_TYPO_NORMALIZED"
    return lowered, None


def caption_metadata(
    video_id: str, reported_type: str, prior_types: dict[str, str]
) -> tuple[str, bool | None, dict[str, object] | None]:
    normalized = reported_type.strip().lower()
    if normalized not in {"manual", "generated", "unknown"}:
        normalized = "unknown"
    prior = prior_types.get(video_id)
    conflict = None
    if (
        prior in {"manual", "generated"}
        and normalized in {"manual", "generated"}
        and prior != normalized
    ):
        conflict = {
            "reported_in_document": normalized,
            "prior_project_evidence": prior,
            "resolution": "unknown",
        }
        normalized = "unknown"
    is_generated = True if normalized == "generated" else False if normalized == "manual" else None
    return normalized, is_generated, conflict


def load_expected_videos(path: Path) -> dict[str, dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as source:
        rows = list(csv.DictReader(source))
    return {
        row["video_id"]: row
        for row in rows
        if row["split"] == "tune" and row["review_status"] == "reviewed"
    }


def load_prior_caption_types(path: Path) -> dict[str, str]:
    with path.open(newline="", encoding="utf-8") as source:
        return {
            row["video_id"]: row["expected_caption_type"]
            for row in csv.DictReader(source)
            if row["expected_caption_type"] in {"manual", "generated"}
        }


def gap_records(snippets: list[dict[str, object]]) -> list[dict[str, object]]:
    starts = [float(snippet["start_seconds"]) for snippet in snippets]
    return [
        {
            "after_index": index,
            "start_seconds": start,
            "next_start_seconds": later,
            "gap_seconds": later - start,
            "interpretation": (
                "could be legitimate silence or omitted cues; not classified automatically"
            ),
        }
        for index, (start, later) in enumerate(zip(starts, starts[1:], strict=False))
        if later - start > 10
    ]


def build_document(
    section: list[dict[str, object]],
    *,
    source_path: Path,
    source_sha256: str,
    acquired_at: str,
    expected_video: dict[str, str],
    prior_types: dict[str, str],
) -> tuple[dict[str, object], dict[str, object]]:
    if len(section) < 5:
        raise ValueError("video section has fewer than five metadata paragraphs")
    heading = str(section[0]["text"]).strip()
    title = str(section[1]["text"]).strip()
    url = str(section[2]["text"]).strip()
    video_id = parse_qs(urlparse(url).query).get("v", [None])[0]
    if not video_id:
        raise ValueError(f"{heading} does not contain a YouTube video ID")
    status_match = STATUS_RE.fullmatch(str(section[3]["text"]).strip())
    if status_match is None:
        raise ValueError(f"{heading} has an invalid status line")
    raw_status, reported_caption_type = status_match.groups()
    status, status_warning = normalize_status(raw_status)
    notes = str(section[4]["text"])
    payload = section[5:]
    embedded_count = sum(parse_embedded_line(str(row["text"])) is not None for row in payload)
    timestamp_count = sum(parse_timestamp(str(row["text"]).strip()) is not None for row in payload)
    if embedded_count > timestamp_count:
        source_format = "embedded_start_human_timestamp_and_text"
        parsed, warnings, excluded = parse_embedded_payload(payload)
    else:
        source_format = "alternating_start_and_text_paragraphs"
        parsed, warnings, excluded = parse_alternating_payload(payload)
    if status_warning:
        warnings.append({"code": status_warning, "reported_status": raw_status})
    starts = [int(snippet["start_seconds"]) for snippet in parsed]
    if any(later < earlier for earlier, later in zip(starts, starts[1:], strict=False)):
        raise ValueError(f"{video_id} has decreasing source timestamps")
    if not parsed:
        raise ValueError(f"{video_id} has no parsed transcript snippets")
    snippets, timing = derive_analysis_durations(parsed)
    caption_type, is_generated, caption_conflict = caption_metadata(
        video_id, reported_caption_type, prior_types
    )
    if caption_conflict:
        warnings.append({"code": "CAPTION_TYPE_CONFLICT", **caption_conflict})
    suspicious_gaps = gap_records(snippets)
    duplicate_count = len(starts) - len(set(starts))
    document = {
        "schema_version": 1,
        "status": "ready",
        "video_id": video_id,
        "acquired_at": acquired_at,
        "environment": {"kind": "manual-docx-collection", "browser_context": True},
        "source": {
            "library": "manual-docx-import",
            "version": "1",
            "document_name": source_path.name,
            "document_sha256": source_sha256,
            "section_heading": heading,
            "source_format": source_format,
            "credentials_used": False,
            "cookies_exported": False,
            "transcript_panel_interaction": "unknown_by_importer",
            "user_reported_status": status,
            "user_reported_status_raw": raw_status,
            "user_reported_notes": notes,
        },
        "transcript": {
            "language": "English",
            "language_code": "en",
            "caption_type": caption_type,
            "caption_type_reported_in_document": reported_caption_type.strip().lower(),
            "caption_type_conflict": caption_conflict,
            "is_generated": is_generated,
            "provider": "manual-docx-import",
            "provider_version": "1",
        },
        "timing": timing,
        "completeness": {
            "user_reported_status": status,
            "independently_verified": False,
            "snippet_count": len(snippets),
            "first_start_seconds": starts[0],
            "last_start_seconds": starts[-1],
            "video_duration_seconds": None,
            "trailing_completeness": "unavailable_without_video_duration_or_source_end_time",
            "duplicate_start_count": duplicate_count,
            "suspicious_gap_count": len(suspicious_gaps),
            "suspicious_gaps": suspicious_gaps,
            "parse_warning_count": len(warnings),
            "parse_warnings": warnings,
            "excluded_non_transcript_lines": excluded,
        },
        "provenance": {
            "title_in_document": title,
            "title_in_validation_table": expected_video["title"],
            "url": url,
            "manual_sponsor_annotations_used_as_input": False,
        },
        "snippets": snippets,
    }
    summary = {
        "video_id": video_id,
        "title": title,
        "status": status,
        "status_raw": raw_status,
        "source_format": source_format,
        "caption_type": caption_type,
        "caption_type_reported": reported_caption_type.strip().lower(),
        "caption_type_conflict": caption_conflict,
        "snippet_count": len(snippets),
        "first_start_seconds": starts[0],
        "last_start_seconds": starts[-1],
        "duplicate_start_count": duplicate_count,
        "suspicious_gap_count": len(suspicious_gaps),
        "suspicious_gaps": suspicious_gaps,
        "warning_count": len(warnings),
        "warnings": warnings,
        "excluded_non_transcript_line_count": len(excluded),
    }
    return document, summary


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("input", type=Path)
    parser.add_argument("--output-dir", type=Path, default=Path("data/transcripts/tune"))
    parser.add_argument("--videos", type=Path, default=Path("data/validation/videos.csv"))
    parser.add_argument(
        "--acquisition-corpus", type=Path, default=Path("data/acquisition_corpus.csv")
    )
    parser.add_argument("--report", type=Path)
    args = parser.parse_args()

    expected = load_expected_videos(args.videos)
    prior_types = load_prior_caption_types(args.acquisition_corpus)
    source_sha256 = file_sha256(args.input)
    acquired_at = datetime.fromtimestamp(args.input.stat().st_mtime, UTC).isoformat()
    sections = split_sections(extract_docx_paragraphs(args.input))

    built: dict[str, dict[str, object]] = {}
    summaries = []
    duplicates = []
    unexpected = []
    errors = []
    for section in sections:
        try:
            url = str(section[2]["text"]).strip()
            video_id = parse_qs(urlparse(url).query).get("v", [None])[0]
            if video_id not in expected:
                unexpected.append(video_id)
                continue
            if video_id in built:
                duplicates.append(video_id)
                continue
            document, summary = build_document(
                section,
                source_path=args.input,
                source_sha256=source_sha256,
                acquired_at=acquired_at,
                expected_video=expected[video_id],
                prior_types=prior_types,
            )
            built[video_id] = document
            summaries.append(summary)
        except (IndexError, TypeError, ValueError) as error:
            errors.append(str(error))

    missing = sorted(set(expected) - set(built))
    report = {
        "schema_version": 1,
        "source": {
            "path": str(args.input),
            "filename": args.input.name,
            "sha256": source_sha256,
            "size_bytes": args.input.stat().st_size,
            "modified_at": acquired_at,
            "preserved_unchanged": True,
        },
        "scope": {
            "expected_reviewed_tune_videos": len(expected),
            "held_out_included": False,
            "partial_reviews_included": False,
            "manual_sponsor_annotations_used_as_input": False,
        },
        "coverage": {
            "sections_found": len(sections),
            "usable_transcripts": len(built),
            "missing_video_ids": missing,
            "duplicate_video_ids": sorted(set(duplicates)),
            "unexpected_video_ids": sorted(item for item in unexpected if item),
            "section_errors": errors,
            "total_snippets": sum(int(row["snippet_count"]) for row in summaries),
            "caption_types": dict(Counter(str(row["caption_type"]) for row in summaries)),
        },
        "timing_policy": {
            "source_contains_start_times_only": True,
            "source_durations_fabricated": False,
            "analysis_durations_derived": True,
            "non_terminal": "next distinct source start minus current start",
            "terminal": "per-video median positive consecutive start delta",
            "effect": (
                "detector windows and predicted end boundaries use approximate analysis spans; "
                "they can extend through silence and boundary error includes this timing "
                "uncertainty"
            ),
        },
        "videos": summaries,
    }

    if missing or duplicates or unexpected or errors:
        raise SystemExit(json.dumps(report, indent=2))
    args.output_dir.mkdir(parents=True, exist_ok=True)
    for video_id, document in built.items():
        (args.output_dir / f"{video_id}.json").write_text(
            json.dumps(document, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
    report_path = args.report or args.output_dir / "import-report.json"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
