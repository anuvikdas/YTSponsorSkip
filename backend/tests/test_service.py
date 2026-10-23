from ytsponsorskip.domain import Transcript, TranscriptSnippet
from ytsponsorskip.service import calculate_timing_metrics


def test_timing_metrics_keep_display_timing_distinct_from_boundaries() -> None:
    transcript = Transcript(
        video_id="abcdefghijk",
        language="English",
        language_code="en",
        is_generated=False,
        snippets=(
            TranscriptSnippet(0, "one", 0.0, 2.0),
            TranscriptSnippet(1, "two", 1.5, 1.0),
            TranscriptSnippet(2, "three", 3.0, 1.0),
        ),
        provider="fake",
        provider_version="test",
    )

    metrics = calculate_timing_metrics(transcript)

    assert metrics.snippet_count == 3
    assert metrics.median_snippet_duration_seconds == 1.0
    assert metrics.median_start_gap_seconds == 1.5
    assert metrics.overlapping_snippet_count == 1
    assert metrics.covered_span_seconds == 4.0
