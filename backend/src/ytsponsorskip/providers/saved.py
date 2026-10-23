"""Development-only, explicit allowlist of manually collected reviewed-tune transcripts."""

import json
import math
from pathlib import Path

from ytsponsorskip.domain import (
    FailureCode,
    Transcript,
    TranscriptAcquisitionError,
    TranscriptSnippet,
)

REVIEWED_TUNE_IDS = frozenset(
    {
        "094y1Z2wpJg",
        "bHIhgxav9LY",
        "iWeu2dxHRDg",
        "DTvS9lvRxZ8",
        "I9hJ_Rux9y0",
        "lXfEK8G8CUI",
        "-lErGZZgUbY",
        "MRtg6A1f2Ko",
        "9lx11dy9J30",
        "Sew4rctKghY",
        "O7sQBfpQCvU",
        "U3aXWizDbQ4",
        "x7X9w_GIm1s",
        "aircAruvnKk",
    }
)
DEFAULT_SAVED_DIR = Path(__file__).resolve().parents[4] / "data/transcripts/tune"


class SavedTuneTranscriptProvider:
    """No network and no fallback. Never opens any file outside the explicit ID allowlist."""

    name = "saved-reviewed-tune"

    def __init__(self, directory: Path = DEFAULT_SAVED_DIR) -> None:
        self.directory = directory

    def fetch(self, video_id: str, preferred_languages: tuple[str, ...] | list[str]) -> Transcript:
        if video_id not in REVIEWED_TUNE_IDS:
            raise TranscriptAcquisitionError(
                FailureCode.NO_MATCHING_TRANSCRIPT,
                "No development transcript is saved for this video.",
                retryable=False,
            )
        path = self.directory / f"{video_id}.json"
        try:
            document = json.loads(path.read_text(encoding="utf-8"))
        except OSError as error:
            raise TranscriptAcquisitionError(
                FailureCode.NO_MATCHING_TRANSCRIPT,
                "The saved development transcript is unavailable.",
                retryable=False,
            ) from error
        except ValueError as error:
            raise self._malformed() from error
        try:
            if document["video_id"] != video_id or document["status"] != "ready":
                raise ValueError("identity or status mismatch")
            metadata = document["transcript"]
            language_code = metadata["language_code"]
            if not isinstance(language_code, str) or not language_code.lower().startswith("en"):
                raise ValueError("non-English saved transcript")
            snippets = document["snippets"]
            if not isinstance(snippets, list) or not snippets:
                raise ValueError("empty saved transcript")
            normalized = []
            previous_start = -1.0
            for expected_index, cue in enumerate(snippets):
                start = cue["start_seconds"]
                duration = cue["duration_seconds"]
                if (
                    type(cue["index"]) is not int
                    or cue["index"] != expected_index
                    or not isinstance(cue["text"], str)
                    or not cue["text"].strip()
                    or isinstance(start, bool)
                    or isinstance(duration, bool)
                    or not isinstance(start, (int, float))
                    or not isinstance(duration, (int, float))
                    or not math.isfinite(start)
                    or not math.isfinite(duration)
                    or start < previous_start
                    or start < 0
                    or duration < 0
                ):
                    raise ValueError("invalid saved cue")
                normalized.append(TranscriptSnippet(expected_index, cue["text"], start, duration))
                previous_start = start
            generated = metadata["is_generated"]
            if generated is not None and type(generated) is not bool:
                raise ValueError("invalid caption type")
            return Transcript(
                video_id=video_id,
                language=metadata["language"],
                language_code=language_code,
                is_generated=generated,
                snippets=tuple(normalized),
                provider="saved-reviewed-tune",
                provider_version=str(metadata["provider_version"]),
            )
        except (KeyError, TypeError, ValueError) as error:
            raise self._malformed() from error

    @staticmethod
    def _malformed() -> TranscriptAcquisitionError:
        return TranscriptAcquisitionError(
            FailureCode.UPSTREAM_CHANGED,
            "The saved development transcript is malformed; preview is unavailable.",
            retryable=False,
        )
