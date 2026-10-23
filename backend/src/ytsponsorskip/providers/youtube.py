from collections.abc import Sequence
from importlib.metadata import version
from math import isfinite

from requests import Session
from youtube_transcript_api import (
    AgeRestricted,
    InvalidVideoId,
    IpBlocked,
    NoTranscriptFound,
    RequestBlocked,
    TranscriptsDisabled,
    VideoUnavailable,
    VideoUnplayable,
    YouTubeDataUnparsable,
    YouTubeRequestFailed,
    YouTubeTranscriptApi,
    YouTubeTranscriptApiException,
)

from ytsponsorskip.domain import (
    FailureCode,
    Transcript,
    TranscriptAcquisitionError,
    TranscriptSnippet,
)


class TimeoutSession(Session):
    """Requests session that supplies a timeout when the caller omits one."""

    def __init__(self, timeout_seconds: float) -> None:
        super().__init__()
        self._timeout_seconds = timeout_seconds

    def request(self, method: str, url: str, **kwargs):  # type: ignore[no-untyped-def]
        kwargs.setdefault("timeout", self._timeout_seconds)
        return super().request(method, url, **kwargs)


class YouTubeTranscriptProvider:
    name = "youtube-transcript-api"

    def __init__(self, timeout_seconds: float = 10.0) -> None:
        self._api = YouTubeTranscriptApi(
            http_client=TimeoutSession(timeout_seconds=timeout_seconds)
        )
        self._version = version("youtube-transcript-api")

    def fetch(self, video_id: str, preferred_languages: Sequence[str]) -> Transcript:
        try:
            fetched = self._api.fetch(video_id, languages=list(preferred_languages))
        except TranscriptsDisabled as error:
            raise TranscriptAcquisitionError(
                FailureCode.TRANSCRIPTS_DISABLED,
                "Captions are disabled for this video.",
                retryable=False,
            ) from error
        except NoTranscriptFound as error:
            raise TranscriptAcquisitionError(
                FailureCode.NO_MATCHING_TRANSCRIPT,
                "No transcript matched the requested languages.",
                retryable=False,
            ) from error
        except AgeRestricted as error:
            raise TranscriptAcquisitionError(
                FailureCode.AGE_RESTRICTED,
                "The provider cannot access this age-restricted video.",
                retryable=False,
            ) from error
        except (VideoUnavailable, VideoUnplayable) as error:
            raise TranscriptAcquisitionError(
                FailureCode.VIDEO_UNAVAILABLE,
                "The video is unavailable to the transcript provider.",
                retryable=False,
            ) from error
        except InvalidVideoId as error:
            raise TranscriptAcquisitionError(
                FailureCode.INVALID_VIDEO_ID,
                "The supplied YouTube video ID is invalid.",
                retryable=False,
            ) from error
        except IpBlocked as error:
            raise TranscriptAcquisitionError(
                FailureCode.IP_BLOCKED,
                "YouTube blocked the backend IP address.",
                retryable=True,
            ) from error
        except RequestBlocked as error:
            raise TranscriptAcquisitionError(
                FailureCode.REQUEST_BLOCKED,
                "YouTube blocked transcript requests from this backend.",
                retryable=True,
            ) from error
        except YouTubeDataUnparsable as error:
            raise TranscriptAcquisitionError(
                FailureCode.UPSTREAM_CHANGED,
                "YouTube returned data the provider could not parse.",
                retryable=True,
            ) from error
        except YouTubeRequestFailed as error:
            raise TranscriptAcquisitionError(
                FailureCode.PROVIDER_ERROR,
                "The transcript provider request failed.",
                retryable=True,
            ) from error
        except YouTubeTranscriptApiException as error:
            raise TranscriptAcquisitionError(
                FailureCode.PROVIDER_ERROR,
                "The transcript provider failed unexpectedly.",
                retryable=True,
            ) from error

        if any(
            not isfinite(snippet.start)
            or not isfinite(snippet.duration)
            or snippet.start < 0
            or snippet.duration < 0
            for snippet in fetched
        ):
            raise TranscriptAcquisitionError(
                FailureCode.UPSTREAM_CHANGED,
                "The provider returned invalid transcript timing data.",
                retryable=True,
            )

        snippets = tuple(
            TranscriptSnippet(
                index=index,
                text=snippet.text,
                start_seconds=snippet.start,
                duration_seconds=snippet.duration,
            )
            for index, snippet in enumerate(fetched)
        )
        return Transcript(
            video_id=fetched.video_id,
            language=fetched.language,
            language_code=fetched.language_code,
            is_generated=fetched.is_generated,
            snippets=snippets,
            provider=self.name,
            provider_version=self._version,
        )
