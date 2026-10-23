"""Offline adapter/evaluator checks using synthetic scores; no model or network calls."""

import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT / "backend/src"), str(ROOT / "scripts"), str(Path(__file__).parent)]

from run_local_semantic_experiment import acceptance, confirmed_interval_metrics  # noqa: E402
from semantic import LocalSemanticDetector  # noqa: E402
from ytsponsorskip.detection_service import transcript_identity  # noqa: E402
from ytsponsorskip.detector import (  # noqa: E402
    DetectedInterval,
    DetectionResult,
    Sensitivity,
)
from ytsponsorskip.domain import Transcript, TranscriptSnippet  # noqa: E402
from ytsponsorskip.evaluation import playback_eligible_intervals  # noqa: E402


def source():
    return Transcript(
        "synthetic01",
        "English",
        "en",
        None,
        (
            TranscriptSnippet(0, "First synthetic phrase.", 0, 1),
            TranscriptSnippet(1, "Second synthetic phrase.", 2, 2),
        ),
        "synthetic-test-fixture",
        "1",
    )


class SemanticContractTests(unittest.TestCase):
    def test_partial_review_scores_only_the_confirmed_interval(self):
        class RecordedSyntheticDetector:
            def detect(self, transcript, sensitivity):
                return DetectionResult(
                    transcript.video_id,
                    sensitivity,
                    (
                        DetectedInterval(9, 21, 1, (), ()),
                        DetectedInterval(30, 35, 1, (), ()),
                    ),
                    1,
                )

        result = confirmed_interval_metrics(
            RecordedSyntheticDetector(),
            source(),
            {"intervals": [{"start_seconds": 10, "end_seconds": 20}]},
        )
        self.assertEqual(result["covered_known_promotional_seconds"], 10)
        self.assertEqual(result["missed_known_promotional_seconds"], 0)
        self.assertEqual(result["predicted_seconds_outside_reviewed_interval_unknown"], 7)
        self.assertIsNone(result["full_video_false_positive_metrics"])

    def test_zero_predictions_cannot_pass_by_avoiding_false_skips(self):
        criteria = json.loads((ROOT / "data/experiments/local-semantic-v1.json").read_text())[
            "selection_criteria"
        ]
        empty = {
            "incorrect_predicted_seconds": 0,
            "negative_videos_with_any_predicted_skip": 0,
            "missed_promotional_seconds": 763,
            "matched_segment_count": 0,
            "mean_start_boundary_error_seconds": None,
            "mean_end_boundary_error_seconds": None,
            "per_video": [],
        }
        self.assertFalse(acceptance(empty, empty, criteria)["passes"])

    def test_stale_semantic_evidence_is_rejected(self):
        detector = LocalSemanticDetector(
            {"synthetic01": {"transcript_identity_sha256": "wrong"}},
            threshold=0.05,
            minimum_similarity=0.4,
        )
        with self.assertRaises(ValueError):
            detector.detect(source())

    def test_short_semantic_fragments_preserve_the_final_duration_gate(self):
        transcript = source()
        score = {"snippet_indices": [0, 1], "positive_similarity": 0.8, "margin": 0.3}
        evidence = {
            "synthetic01": {
                "transcript_identity_sha256": transcript_identity(transcript),
                "windows": [score],
                "boundary_contexts": [score],
                "all_window_count": 1,
            }
        }
        result = LocalSemanticDetector(evidence, threshold=0.05, minimum_similarity=0.4).detect(
            transcript, Sensitivity.CONSERVATIVE
        )
        self.assertEqual(len(result.intervals), 2)
        self.assertEqual(playback_eligible_intervals(result.intervals), ())


if __name__ == "__main__":
    unittest.main()
