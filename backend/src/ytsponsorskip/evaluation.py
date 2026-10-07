from dataclasses import dataclass

from ytsponsorskip.detector import DetectedInterval

type TimeRange = tuple[float, float]


@dataclass(frozen=True, slots=True)
class SegmentMatch:
    prediction_index: int
    annotation_index: int
    overlap_seconds: float
    start_error_seconds: float
    end_error_seconds: float


@dataclass(frozen=True, slots=True)
class VideoMetrics:
    video_id: str
    promotion_status: str
    annotated_seconds: float
    predicted_seconds: float
    incorrect_predicted_seconds: float
    missed_promotional_seconds: float
    matches: tuple[SegmentMatch, ...]


def merge_ranges(ranges: list[TimeRange]) -> list[TimeRange]:
    valid = sorted((start, end) for start, end in ranges if start >= 0 and end > start)
    merged: list[TimeRange] = []
    for start, end in valid:
        if merged and start <= merged[-1][1]:
            merged[-1] = (merged[-1][0], max(merged[-1][1], end))
        else:
            merged.append((start, end))
    return merged


def ranges_duration(ranges: list[TimeRange]) -> float:
    return sum(end - start for start, end in merge_ranges(ranges))


def intersection_duration(left: list[TimeRange], right: list[TimeRange]) -> float:
    left_merged = merge_ranges(left)
    right_merged = merge_ranges(right)
    left_index = 0
    right_index = 0
    overlap = 0.0
    while left_index < len(left_merged) and right_index < len(right_merged):
        left_start, left_end = left_merged[left_index]
        right_start, right_end = right_merged[right_index]
        overlap += max(0.0, min(left_end, right_end) - max(left_start, right_start))
        if left_end <= right_end:
            left_index += 1
        else:
            right_index += 1
    return overlap


def match_intervals(
    predictions: list[TimeRange], annotations: list[TimeRange]
) -> tuple[SegmentMatch, ...]:
    candidates = []
    for prediction_index, (pred_start, pred_end) in enumerate(predictions):
        for annotation_index, (gold_start, gold_end) in enumerate(annotations):
            overlap = max(0.0, min(pred_end, gold_end) - max(pred_start, gold_start))
            if overlap > 0:
                candidates.append(
                    (
                        overlap,
                        prediction_index,
                        annotation_index,
                        pred_start,
                        pred_end,
                        gold_start,
                        gold_end,
                    )
                )
    candidates.sort(reverse=True)
    used_predictions: set[int] = set()
    used_annotations: set[int] = set()
    matches = []
    for (
        overlap,
        prediction_index,
        annotation_index,
        pred_start,
        pred_end,
        gold_start,
        gold_end,
    ) in candidates:
        if prediction_index in used_predictions or annotation_index in used_annotations:
            continue
        used_predictions.add(prediction_index)
        used_annotations.add(annotation_index)
        matches.append(
            SegmentMatch(
                prediction_index=prediction_index,
                annotation_index=annotation_index,
                overlap_seconds=overlap,
                start_error_seconds=abs(pred_start - gold_start),
                end_error_seconds=abs(pred_end - gold_end),
            )
        )
    return tuple(sorted(matches, key=lambda match: match.annotation_index))


def calculate_video_metrics(
    *,
    video_id: str,
    promotion_status: str,
    predictions: tuple[DetectedInterval, ...],
    annotations: list[TimeRange],
) -> VideoMetrics:
    predicted_ranges = [(interval.start_seconds, interval.end_seconds) for interval in predictions]
    shared_seconds = intersection_duration(predicted_ranges, annotations)
    predicted_seconds = ranges_duration(predicted_ranges)
    annotated_seconds = ranges_duration(annotations)
    return VideoMetrics(
        video_id=video_id,
        promotion_status=promotion_status,
        annotated_seconds=annotated_seconds,
        predicted_seconds=predicted_seconds,
        incorrect_predicted_seconds=max(0.0, predicted_seconds - shared_seconds),
        missed_promotional_seconds=max(0.0, annotated_seconds - shared_seconds),
        matches=match_intervals(predicted_ranges, annotations),
    )
