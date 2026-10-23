"""Persistent local native-caption reuse and the five-distinct-video authorization ledger."""

import json
import os
import re
import sqlite3
import time
from dataclasses import asdict, replace
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

from ytsponsorskip.domain import (
    FailureCode,
    Transcript,
    TranscriptAcquisitionError,
    TranscriptSnippet,
)
from ytsponsorskip.providers.supadata import SupadataProbeError, SupadataTranscriptProvider

ROOT = Path(__file__).resolve().parents[4]
DEFAULT_DIRECTORY = ROOT / "results/development-transcripts"


class NativeDemoBudget:
    """Shares the original five-attempt authorization across restarts and local processes."""

    def __init__(self, path: Path, directory: Path = DEFAULT_DIRECTORY):
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)
        prior = []
        for record in directory.glob("*.attempt.json"):
            value = json.loads(record.read_text())
            video_id = value["video_id"]
            if not re.fullmatch(r"[A-Za-z0-9_-]{11}", video_id):
                raise ValueError("Invalid campaign reservation record")
            prior.append(video_id)
        with sqlite3.connect(path) as connection:
            connection.execute(
                "CREATE TABLE IF NOT EXISTS native_demo_attempts "
                "(video_id TEXT PRIMARY KEY, created_at TEXT DEFAULT CURRENT_TIMESTAMP)"
            )
            connection.executemany(
                "INSERT OR IGNORE INTO native_demo_attempts(video_id) VALUES (?)",
                [(video_id,) for video_id in prior],
            )

    def reserve(self, video_id):
        try:
            with sqlite3.connect(self.path, timeout=5) as connection:
                connection.execute("BEGIN IMMEDIATE")
                existing = connection.execute(
                    "SELECT 1 FROM native_demo_attempts WHERE video_id=?", (video_id,)
                ).fetchone()
                count = connection.execute("SELECT COUNT(*) FROM native_demo_attempts").fetchone()[
                    0
                ]
                if existing or count >= 5:
                    raise TranscriptAcquisitionError(
                        FailureCode.TRIAL_BUDGET_EXHAUSTED,
                        "This video was already attempted, or the five-video allowance is used. "
                        "No retry was sent; use a saved transcript.",
                        retryable=False,
                    )
                connection.execute(
                    "INSERT INTO native_demo_attempts(video_id) VALUES (?)", (video_id,)
                )
        except sqlite3.Error as error:
            raise TranscriptAcquisitionError(
                FailureCode.TRIAL_BUDGET_UNAVAILABLE,
                "Native attempt ledger unavailable.",
                retryable=False,
            ) from error

    def snapshot(self):
        with sqlite3.connect(self.path) as connection:
            ids = [
                row[0]
                for row in connection.execute(
                    "SELECT video_id FROM native_demo_attempts ORDER BY created_at, video_id"
                )
            ]
        return {
            "native_attempt_limit": 5,
            "native_attempts_used": len(ids),
            "native_attempts_remaining": max(0, 5 - len(ids)),
            "attempted_video_ids": ids,
        }


def write_atomic(path, value):
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        temporary = path.with_name(path.name + f".{uuid4().hex}.tmp")
        temporary.write_text(
            json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + "\n"
        )
        os.replace(temporary, path)
    except OSError as error:
        raise TranscriptAcquisitionError(
            FailureCode.PROVIDER_ERROR,
            "Local transcript persistence failed; no retry was sent.",
            retryable=False,
        ) from error


class PersistentNativeProvider:
    """No fallback or retries. The enclosing TranscriptService coalesces concurrent requests."""

    def __init__(
        self,
        provider: SupadataTranscriptProvider,
        budget: NativeDemoBudget,
        *,
        directory=DEFAULT_DIRECTORY,
        reuse_directories=None,
        secret="",
    ):
        self.provider = provider
        self.budget = budget
        self.directory = directory
        self.reuse_directories = (
            reuse_directories
            if reuse_directories is not None
            else [
                directory,
                ROOT / "data/transcripts/held_out",
            ]
        )
        self.secret = secret

    def _saved(self, video_id):
        for directory in self.reuse_directories:
            path = directory / f"{video_id}.json"
            if not path.exists():
                continue
            try:
                document = json.loads(path.read_text())
                metadata = document["transcript"]
                if document["video_id"] != video_id or metadata["provider"] != "supadata-native":
                    continue
                transcript = Transcript(
                    video_id,
                    metadata["language"],
                    metadata["language_code"],
                    metadata.get("is_generated"),
                    tuple(TranscriptSnippet(**cue) for cue in document["snippets"]),
                    "supadata-native",
                    metadata["provider_version"],
                )
                # Local import avoids the provider/service import cycle.
                from ytsponsorskip.detection_service import validate_transcript

                validate_transcript(transcript, video_id)
                return replace(transcript, provider="supadata-native-saved")
            except (OSError, ValueError, KeyError, TypeError) as error:
                raise TranscriptAcquisitionError(
                    FailureCode.UPSTREAM_CHANGED,
                    "Saved native transcript is malformed; no retry sent.",
                    retryable=False,
                ) from error
        return None

    def fetch(self, video_id, preferred_languages):
        if not re.fullmatch(r"[A-Za-z0-9_-]{11}", video_id):
            raise TranscriptAcquisitionError(
                FailureCode.INVALID_VIDEO_ID, "Invalid YouTube video ID.", retryable=False
            )
        if not preferred_languages or not preferred_languages[0].lower().startswith("en"):
            raise TranscriptAcquisitionError(
                FailureCode.NO_MATCHING_TRANSCRIPT,
                "Native demo supports English only.",
                retryable=False,
            )
        saved = self._saved(video_id)
        if saved is not None:
            return saved
        self.budget.reserve(video_id)
        acquired_at = datetime.now(UTC).isoformat()
        record_path = self.directory / f"{video_id}.attempt.json"
        record = {
            "video_id": video_id,
            "acquired_at": acquired_at,
            "result": "started_or_interrupted",
            "request": {"lang": "en", "mode": "native", "text": False},
        }
        write_atomic(record_path, record)
        started = time.monotonic()
        observations = ()
        try:
            result = self.provider.fetch_with_observations(video_id, preferred_languages)
            transcript = result.transcript
            observations = result.observations
            write_atomic(
                self.directory / f"{video_id}.json",
                {
                    "schema_version": 1,
                    "status": "ready",
                    "video_id": video_id,
                    "acquired_at": acquired_at,
                    "source": {
                        "library": "supadata-native",
                        "version": transcript.provider_version,
                        "request": record["request"],
                        "manual_annotations_used": False,
                    },
                    "transcript": {
                        "language": transcript.language,
                        "language_code": transcript.language_code,
                        "is_generated": transcript.is_generated,
                        "caption_type": "unknown",
                        "provider": transcript.provider,
                        "provider_version": transcript.provider_version,
                    },
                    "timing": {
                        "source_unit": "milliseconds",
                        "normalized_unit": "seconds",
                        "duration_is_exact_promotion_boundary": False,
                    },
                    "snippets": [asdict(cue) for cue in transcript.snippets],
                },
            )
            record["result"] = "usable"
            return transcript
        except TranscriptAcquisitionError as error:
            observations = error.observations if isinstance(error, SupadataProbeError) else ()
            record.update(result="unavailable", error_code=error.code.value)
            raise
        finally:
            record["latency_ms"] = round((time.monotonic() - started) * 1000, 3)
            record["http_statuses"] = [item.status_code for item in observations]
            # Persist response data, never request headers. Redact an echoed key defensively.
            raw = json.dumps([asdict(item) for item in observations], ensure_ascii=False)
            record["responses"] = (
                json.loads(raw.replace(self.secret, "[REDACTED]"))
                if self.secret
                else json.loads(raw)
            )
            write_atomic(record_path, record)
