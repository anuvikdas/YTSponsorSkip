import importlib.util
from pathlib import Path

IMPORTER_PATH = Path(__file__).parents[2] / "scripts" / "import_manual_transcripts.py"
SPEC = importlib.util.spec_from_file_location("import_manual_transcripts", IMPORTER_PATH)
assert SPEC is not None and SPEC.loader is not None
IMPORTER = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(IMPORTER)


def test_embedded_timestamp_parser_removes_only_timestamp_metadata() -> None:
    parsed = IMPORTER.parse_embedded_line(
        "1:021 minute, 2 secondsSo at that point, I knew what to do."
    )

    assert parsed == {
        "source_timestamp": "1:02",
        "source_human_timestamp": "1 minute, 2 seconds",
        "start_seconds": 62,
        "text": "So at that point, I knew what to do.",
    }


def test_derived_durations_preserve_duplicate_start_overlaps() -> None:
    snippets, timing = IMPORTER.derive_analysis_durations(
        [
            {"source_timestamp": "0:00", "start_seconds": 0, "text": "one"},
            {"source_timestamp": "0:00", "start_seconds": 0, "text": "two"},
            {"source_timestamp": "0:03", "start_seconds": 3, "text": "three"},
        ]
    )

    assert [snippet["duration_seconds"] for snippet in snippets] == [3, 3, 3]
    assert timing["source_duration_available"] is False
    assert all(snippet["source_duration_seconds"] is None for snippet in snippets)


def test_unknown_caption_type_stays_unknown() -> None:
    caption_type, is_generated, conflict = IMPORTER.caption_metadata("video", "Unknown", {})

    assert caption_type == "unknown"
    assert is_generated is None
    assert conflict is None


def test_conflicting_caption_evidence_becomes_unknown() -> None:
    caption_type, is_generated, conflict = IMPORTER.caption_metadata(
        "aircAruvnKk", "Generated", {"aircAruvnKk": "manual"}
    )

    assert caption_type == "unknown"
    assert is_generated is None
    assert conflict == {
        "reported_in_document": "generated",
        "prior_project_evidence": "manual",
        "resolution": "unknown",
    }
