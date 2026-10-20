"""Local, persistent, atomic acquisition-attempt budget for the bounded trial."""

import sqlite3
from collections.abc import Sequence
from contextlib import closing
from pathlib import Path
from uuid import uuid4

from ytsponsorskip.domain import FailureCode, TranscriptAcquisitionError
from ytsponsorskip.providers.base import TranscriptProvider

OBSERVED_ATTEMPTS = (
    ("observed-supadata-2026-10-19-dQw4w9WgXcQ", "dQw4w9WgXcQ"),
    ("observed-supadata-2026-10-19-Vw1Qrko8oTs", "Vw1Qrko8oTs"),
)


class TrialBudget:
    """One SQLite file shared by local processes; each reservation commits before network I/O."""

    def __init__(self, path: Path, *, limit: int = 50, max_polls: int = 5) -> None:
        if not 2 <= limit <= 50 or not 1 <= max_polls <= 5:
            raise ValueError("Trial attempt limit must be 2–50 and poll limit 1–5")
        self.path = Path(path)
        self.limit = limit
        self.max_polls = max_polls
        self.path.parent.mkdir(parents=True, exist_ok=True)
        try:
            with closing(self._connect()) as connection, connection:
                connection.execute(
                    "CREATE TABLE IF NOT EXISTS attempts ("
                    "id TEXT PRIMARY KEY, source TEXT NOT NULL, video_id TEXT NOT NULL, "
                    "poll_count INTEGER NOT NULL DEFAULT 0, "
                    "created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP)"
                )
                connection.executemany(
                    "INSERT OR IGNORE INTO attempts(id, source, video_id) "
                    "VALUES (?, 'observed', ?)",
                    OBSERVED_ATTEMPTS,
                )
        except sqlite3.Error as error:
            raise self._unavailable() from error

    def _connect(self):
        connection = sqlite3.connect(self.path, timeout=5)
        connection.execute("PRAGMA busy_timeout=5000")
        return connection

    @staticmethod
    def _unavailable():
        return TranscriptAcquisitionError(
            FailureCode.TRIAL_BUDGET_UNAVAILABLE,
            "The trial budget ledger is unavailable; acquisition was not started.",
            retryable=False,
        )

    @staticmethod
    def _exhausted():
        return TranscriptAcquisitionError(
            FailureCode.TRIAL_BUDGET_EXHAUSTED,
            "The trial acquisition budget is exhausted; skipping is unavailable.",
            retryable=False,
        )

    def reserve_attempt(self, video_id: str, source: str) -> str:
        """BEGIN IMMEDIATE serializes check and insert across processes sharing this file."""
        attempt_id = uuid4().hex
        try:
            with closing(self._connect()) as connection, connection:
                connection.execute("BEGIN IMMEDIATE")
                count = connection.execute("SELECT COUNT(*) FROM attempts").fetchone()[0]
                if count >= self.limit:
                    raise self._exhausted()
                connection.execute(
                    "INSERT INTO attempts(id, source, video_id) VALUES (?, ?, ?)",
                    (attempt_id, source, video_id),
                )
            return attempt_id
        except sqlite3.Error as error:
            raise self._unavailable() from error

    def reserve_poll(self, attempt_id: str) -> int:
        """Count each job-status HTTP call before it is sent."""
        try:
            with closing(self._connect()) as connection, connection:
                connection.execute("BEGIN IMMEDIATE")
                changed = connection.execute(
                    "UPDATE attempts SET poll_count = poll_count + 1 "
                    "WHERE id = ? AND poll_count < ?",
                    (attempt_id, self.max_polls),
                ).rowcount
                if not changed:
                    raise TranscriptAcquisitionError(
                        FailureCode.TRIAL_POLL_LIMIT,
                        "The trial job-poll limit was reached; skipping is unavailable.",
                        retryable=False,
                    )
                return connection.execute(
                    "SELECT poll_count FROM attempts WHERE id = ?", (attempt_id,)
                ).fetchone()[0]
        except sqlite3.Error as error:
            raise self._unavailable() from error

    def snapshot(self) -> dict[str, int]:
        try:
            with closing(self._connect()) as connection, connection:
                count, polls = connection.execute(
                    "SELECT COUNT(*), COALESCE(SUM(poll_count), 0) FROM attempts"
                ).fetchone()
            return {
                "attempts_used": count,
                "attempts_remaining": max(0, self.limit - count),
                "attempt_limit": self.limit,
                "polls_used": polls,
                "polls_per_attempt_limit": self.max_polls,
            }
        except sqlite3.Error as error:
            raise self._unavailable() from error


class BudgetedTranscriptProvider:
    """Wrap a one-request provider; TranscriptService invokes this only on cache misses."""

    def __init__(self, provider: TranscriptProvider, budget: TrialBudget, *, source: str) -> None:
        self.provider = provider
        self.budget = budget
        self.source = source

    def fetch(self, video_id: str, preferred_languages: Sequence[str]):
        self.budget.reserve_attempt(video_id, self.source)
        return self.provider.fetch(video_id, preferred_languages)
