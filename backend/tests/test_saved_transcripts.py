import importlib.util
from pathlib import Path

EVALUATOR_PATH = Path(__file__).parents[2] / "scripts" / "evaluate_detector.py"
SPEC = importlib.util.spec_from_file_location("evaluate_detector", EVALUATOR_PATH)
assert SPEC is not None and SPEC.loader is not None
EVALUATOR = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(EVALUATOR)
usable_transcript = EVALUATOR.usable_transcript


def test_saved_unknown_caption_type_is_not_coerced_to_manual() -> None:
    transcript = usable_transcript(
        {
            "video_id": "U3aXWizDbQ4",
            "transcript": {
                "language": "English",
                "language_code": "en",
                "caption_type": "unknown",
                "is_generated": None,
            },
            "snippets": [
                {
                    "index": 0,
                    "text": "source text",
                    "start_seconds": 0,
                    "duration_seconds": 1.5,
                }
            ],
        }
    )

    assert transcript is not None
    assert transcript.is_generated is None
