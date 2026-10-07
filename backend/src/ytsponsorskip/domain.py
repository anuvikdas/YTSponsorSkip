from dataclasses import dataclass
from enum import StrEnum


@dataclass(frozen=True, slots=True)
class TranscriptSnippet:
    index: int
    text: str
    start_seconds: float
    duration_seconds: float

    @property
    def end_seconds(self) -> float:
        return self.start_seconds + self.duration_seconds


@dataclass(frozen=True, slots=True)
class Transcript:
    video_id: str
    language: str
    language_code: str
    is_generated: bool | None
    snippets: tuple[TranscriptSnippet, ...]
    provider: str
    provider_version: str


class FailureCode(StrEnum):
    TRANSCRIPTS_DISABLED = "TRANSCRIPTS_DISABLED"
    NO_MATCHING_TRANSCRIPT = "NO_MATCHING_TRANSCRIPT"
    VIDEO_UNAVAILABLE = "VIDEO_UNAVAILABLE"
    AGE_RESTRICTED = "AGE_RESTRICTED"
    REQUEST_BLOCKED = "REQUEST_BLOCKED"
    IP_BLOCKED = "IP_BLOCKED"
    UPSTREAM_CHANGED = "UPSTREAM_CHANGED"
    ACQUISITION_TIMEOUT = "ACQUISITION_TIMEOUT"
    INVALID_VIDEO_ID = "INVALID_VIDEO_ID"
    PROVIDER_ERROR = "PROVIDER_ERROR"


class TranscriptAcquisitionError(Exception):
    def __init__(self, code: FailureCode, message: str, *, retryable: bool) -> None:
        super().__init__(message)
        self.code = code
        self.public_message = message
        self.retryable = retryable
