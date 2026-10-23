import pytest
from pydantic import ValidationError
from ytsponsorskip.detector import Sensitivity
from ytsponsorskip.model_detection_contract import (
    ClassificationSnippet,
    ModelDetectionError,
    ModelDetectionRequest,
    ModelDetectionResponse,
    PromotionKind,
    PromotionOwnership,
    ProposedPromotionSegment,
    snippet_ids_to_time_range,
    validate_model_response,
)


def request() -> ModelDetectionRequest:
    return ModelDetectionRequest(
        video_id="dQw4w9WgXcQ",
        request_id="dQw4w9WgXcQ-request-1",
        language_code="en",
        sensitivity=Sensitivity.CONSERVATIVE,
        prompt_version="promotion-v1",
        snippets=(
            ClassificationSnippet(
                snippet_id=7,
                text="Thanks to Example for sponsoring this video.",
                start_seconds=100,
                duration_seconds=4,
            ),
            ClassificationSnippet(
                snippet_id=8,
                text="Use code SAVE at the link below.",
                start_seconds=104,
                duration_seconds=5,
            ),
        ),
    )


def response(**overrides: object) -> ModelDetectionResponse:
    values = {
        "video_id": "dQw4w9WgXcQ",
        "request_id": "dQw4w9WgXcQ-request-1",
        "prompt_version": "promotion-v1",
        "model_version": "example-model-pinned",
        "segments": (
            ProposedPromotionSegment(
                start_snippet_id=7,
                end_snippet_id=8,
                ownership=PromotionOwnership.THIRD_PARTY,
                kind=PromotionKind.SPONSORSHIP,
                evidence_snippet_ids=(7, 8),
                reason_code="disclosure_and_call_to_action",
            ),
        ),
    }
    values.update(overrides)
    return ModelDetectionResponse(**values)


def test_valid_response_maps_ids_to_source_timing() -> None:
    model_request = request()
    model_response = response()

    validate_model_response(model_request, model_response)

    segment = model_response.segments[0]
    assert snippet_ids_to_time_range(
        model_request.snippets,
        segment.start_snippet_id,
        segment.end_snippet_id,
    ) == (100, 109)


def test_stale_identity_and_unknown_snippet_fail_closed() -> None:
    with pytest.raises(ModelDetectionError):
        validate_model_response(request(), response(request_id="stale-request-id"))

    bad_segment = response().segments[0].model_copy(
        update={"end_snippet_id": 99, "evidence_snippet_ids": (7, 99)}
    )
    with pytest.raises(ModelDetectionError):
        validate_model_response(request(), response(segments=(bad_segment,)))


def test_request_rejects_reordered_source_snippets() -> None:
    values = request().model_dump()
    values["snippets"] = list(reversed(values["snippets"]))

    with pytest.raises(ValidationError):
        ModelDetectionRequest.model_validate(values)
