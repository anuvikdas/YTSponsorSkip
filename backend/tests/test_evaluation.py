from ytsponsorskip.detector import DetectedInterval
from ytsponsorskip.evaluation import (
    calculate_video_metrics,
    match_intervals,
    playback_eligible_intervals,
)


def detected(start: float, end: float) -> DetectedInterval:
    return DetectedInterval(start, end, 5, ("test",), (0,))


def test_metrics_use_union_time_for_false_and_missed_seconds() -> None:
    metrics = calculate_video_metrics(
        video_id="video",
        promotion_status="one_or_more",
        predictions=(detected(5, 15), detected(14, 25)),
        annotations=[(10, 20)],
    )

    assert metrics.predicted_seconds == 20
    assert metrics.annotated_seconds == 10
    assert metrics.incorrect_predicted_seconds == 10
    assert metrics.missed_promotional_seconds == 0


def test_interval_matching_is_one_to_one_by_greatest_overlap() -> None:
    matches = match_intervals(
        predictions=[(8, 18), (20, 31)],
        annotations=[(10, 20), (22, 30)],
    )

    assert [(match.prediction_index, match.annotation_index) for match in matches] == [
        (0, 0),
        (1, 1),
    ]
    assert matches[0].start_error_seconds == 2
    assert matches[1].end_error_seconds == 1


def test_playback_policy_filters_only_after_merging_and_preserves_detector_input() -> None:
    predictions = (
        detected(10, 11.5),
        detected(11.5, 13),  # exactly 3 seconds together: not eligible
        detected(20, 22),
        detected(22, 24),  # 4 seconds together: eligible
        detected(30, 33.001),
    )
    eligible = playback_eligible_intervals(predictions)
    assert [(i.start_seconds, i.end_seconds) for i in eligible] == [
        (20, 24),
        (30, 33.001),
    ]
    assert len(predictions) == 5
