"""Provider-neutral contracts for a possible model-assisted detector.

Nothing in this module calls a model or participates in the active detector.  It makes the
boundary reviewable before any SDK, API key, or paid inference is introduced.
"""

from collections.abc import Sequence
from enum import StrEnum
from typing import Protocol

from pydantic import BaseModel, ConfigDict, Field, model_validator

from ytsponsorskip.detector import Sensitivity


class PromotionOwnership(StrEnum):
    THIRD_PARTY = "third_party"
    CREATOR_OWNED = "creator_owned"


class PromotionKind(StrEnum):
    SPONSORSHIP = "sponsorship"
    AFFILIATE = "affiliate"
    MERCHANDISE = "merchandise"
    MEMBERSHIP = "membership"
    PRODUCT_OR_SERVICE = "product_or_service"


class ModelFailureCode(StrEnum):
    TIMEOUT = "timeout"
    RATE_LIMITED = "rate_limited"
    PROVIDER_UNAVAILABLE = "provider_unavailable"
    REFUSED = "refused"
    CONTEXT_TOO_LARGE = "context_too_large"
    INVALID_RESPONSE = "invalid_response"
    MISCONFIGURED = "misconfigured"
    BUDGET_EXHAUSTED = "budget_exhausted"


class ClassificationSnippet(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    snippet_id: int = Field(ge=0)
    text: str = Field(min_length=1, max_length=10_000)
    start_seconds: float = Field(ge=0, allow_inf_nan=False)
    duration_seconds: float = Field(ge=0, allow_inf_nan=False)


class ModelDetectionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    video_id: str = Field(pattern=r"^[A-Za-z0-9_-]{11}$")
    request_id: str = Field(min_length=12, max_length=160)
    language_code: str = Field(min_length=1, max_length=35)
    sensitivity: Sensitivity
    prompt_version: str = Field(min_length=1, max_length=80)
    snippets: tuple[ClassificationSnippet, ...] = Field(min_length=1, max_length=20_000)

    @model_validator(mode="after")
    def snippets_are_unique_and_ordered(self) -> "ModelDetectionRequest":
        ids = [snippet.snippet_id for snippet in self.snippets]
        starts = [snippet.start_seconds for snippet in self.snippets]
        if len(ids) != len(set(ids)):
            raise ValueError("snippet IDs must be unique")
        if ids != sorted(ids):
            raise ValueError("snippet IDs must retain source order")
        if starts != sorted(starts):
            raise ValueError("snippets must retain source timing order")
        return self


class ProposedPromotionSegment(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    start_snippet_id: int = Field(ge=0)
    end_snippet_id: int = Field(ge=0)
    ownership: PromotionOwnership
    kind: PromotionKind
    evidence_snippet_ids: tuple[int, ...] = Field(min_length=1, max_length=20)
    reason_code: str = Field(pattern=r"^[a-z][a-z0-9_]{0,63}$")

    @model_validator(mode="after")
    def range_is_ordered(self) -> "ProposedPromotionSegment":
        if self.end_snippet_id < self.start_snippet_id:
            raise ValueError("segment snippet range must be ordered")
        return self


class ModelDetectionResponse(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    video_id: str = Field(pattern=r"^[A-Za-z0-9_-]{11}$")
    request_id: str = Field(min_length=12, max_length=160)
    prompt_version: str = Field(min_length=1, max_length=80)
    model_version: str = Field(min_length=1, max_length=120)
    segments: tuple[ProposedPromotionSegment, ...] = Field(max_length=100)


class ModelDetectionError(RuntimeError):
    def __init__(self, code: ModelFailureCode, message: str, *, retryable: bool) -> None:
        super().__init__(message)
        self.code = code
        self.retryable = retryable


class ContextClassifier(Protocol):
    """Replaceable hosted, local, or decision-model adapter."""

    async def classify(self, request: ModelDetectionRequest) -> ModelDetectionResponse:
        """Return snippet-ID ranges or raise a typed, no-skip failure."""


def validate_model_response(
    request: ModelDetectionRequest,
    response: ModelDetectionResponse,
) -> None:
    """Validate semantic identities and ranges that JSON Schema cannot express."""

    if response.video_id != request.video_id or response.request_id != request.request_id:
        raise ModelDetectionError(
            ModelFailureCode.INVALID_RESPONSE,
            "model response does not match the active video/request",
            retryable=False,
        )
    if response.prompt_version != request.prompt_version:
        raise ModelDetectionError(
            ModelFailureCode.INVALID_RESPONSE,
            "model response does not match the requested prompt version",
            retryable=False,
        )

    valid_ids = {snippet.snippet_id for snippet in request.snippets}
    for segment in response.segments:
        referenced = {
            segment.start_snippet_id,
            segment.end_snippet_id,
            *segment.evidence_snippet_ids,
        }
        if not referenced <= valid_ids:
            raise ModelDetectionError(
                ModelFailureCode.INVALID_RESPONSE,
                "model response references a snippet outside the request",
                retryable=False,
            )
        if not all(
            segment.start_snippet_id <= snippet_id <= segment.end_snippet_id
            for snippet_id in segment.evidence_snippet_ids
        ):
            raise ModelDetectionError(
                ModelFailureCode.INVALID_RESPONSE,
                "model evidence must fall inside its proposed range",
                retryable=False,
            )

    ordered = sorted(
        response.segments,
        key=lambda segment: (segment.start_snippet_id, segment.end_snippet_id),
    )
    for previous, current in zip(ordered, ordered[1:], strict=False):
        if current.start_snippet_id <= previous.end_snippet_id:
            raise ModelDetectionError(
                ModelFailureCode.INVALID_RESPONSE,
                "model segments must not overlap",
                retryable=False,
            )


def snippet_ids_to_time_range(
    snippets: Sequence[ClassificationSnippet],
    start_snippet_id: int,
    end_snippet_id: int,
) -> tuple[float, float]:
    """Map validated IDs to source timing; this is not boundary refinement."""

    by_id = {snippet.snippet_id: snippet for snippet in snippets}
    first = by_id[start_snippet_id]
    last = by_id[end_snippet_id]
    return first.start_seconds, last.start_seconds + last.duration_seconds
