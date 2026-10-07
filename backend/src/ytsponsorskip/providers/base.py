from collections.abc import Sequence
from typing import Protocol

from ytsponsorskip.domain import Transcript


class TranscriptProvider(Protocol):
    def fetch(self, video_id: str, preferred_languages: Sequence[str]) -> Transcript:
        """Fetch one transcript or raise TranscriptAcquisitionError."""
        ...
