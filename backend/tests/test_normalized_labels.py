import csv
import math
from collections import Counter
from pathlib import Path

PROJECT_ROOT = Path(__file__).parents[2]


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as source:
        return list(csv.DictReader(source))


def test_normalized_manual_labels_have_expected_shape_and_totals() -> None:
    videos = read_csv(PROJECT_ROOT / "data/validation/videos.csv")
    segments = read_csv(PROJECT_ROOT / "data/validation/segments.csv")

    assert len(videos) == 24
    assert len(segments) == 13
    assert Counter(video["split"] for video in videos) == {"tune": 16, "held_out": 8}
    assert sum(video["promotion_status"] == "one_or_more" for video in videos) == 12
    assert sum(video["promotion_status"] == "none" for video in videos) == 10
    assert sum(video["review_status"] == "in_progress" for video in videos) == 2
    assert all(
        video["promotion_status"] == "unknown"
        for video in videos
        if video["review_status"] == "in_progress"
    )

    video_ids = {video["video_id"] for video in videos}
    keys: set[tuple[str, int]] = set()
    for segment in segments:
        assert segment["video_id"] in video_ids
        segment_number = int(segment["segment_number"])
        key = (segment["video_id"], segment_number)
        assert key not in keys
        keys.add(key)
        start = float(segment["start_seconds"])
        end = float(segment["end_seconds"])
        assert math.isfinite(start) and math.isfinite(end)
        assert 0 <= start < end
        assert segment["category"] == ""
        assert segment["boundary_certainty"] == ""

    foundations = [segment for segment in segments if segment["video_id"] == "0_KhihMIOG8"]
    assert [int(segment["segment_number"]) for segment in foundations] == [1, 2]
