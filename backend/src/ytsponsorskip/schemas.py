from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class TranscriptSnippetResponse(StrictModel):
    index: int = Field(ge=0)
    text: str
    start_seconds: float = Field(ge=0)
    duration_seconds: float = Field(ge=0)


class TranscriptMetadataResponse(StrictModel):
    language: str
    language_code: str
    is_generated: bool | None
    provider: str
    provider_version: str


class TimingMetricsResponse(StrictModel):
    snippet_count: int = Field(ge=0)
    median_snippet_duration_seconds: float | None
    median_start_gap_seconds: float | None
    overlapping_snippet_count: int = Field(ge=0)
    covered_span_seconds: float = Field(ge=0)


class AcquisitionResponse(StrictModel):
    status: str = "ready"
    video_id: str
    request_id: str
    transcript: TranscriptMetadataResponse
    snippets: list[TranscriptSnippetResponse]
    provider_latency_ms: float | None = Field(default=None, ge=0)
    cache_hit: bool
    coalesced: bool
    timing: TimingMetricsResponse


class ErrorDetails(StrictModel):
    code: str
    message: str
    retryable: bool
    request_id: str


class ErrorResponse(StrictModel):
    status: str = "unavailable"
    error: ErrorDetails


class HealthResponse(StrictModel):
    status: str
    environment: str


class DetectedIntervalResponse(StrictModel):
    start_seconds: float = Field(ge=0, allow_inf_nan=False)
    end_seconds: float = Field(gt=0, allow_inf_nan=False)
    heuristic_score: int
    evidence: list[str]
    snippet_indices: list[int]
    auto_skip_eligible: bool


class DetectionResponse(StrictModel):
    status: Literal["ready"] = "ready"
    video_id: str
    request_id: str
    mode: Literal["conservative", "aggressive"]
    transcript_source: Literal["saved", "supadata"]
    transcript_provider: str
    transcript_sha256: str
    detector_version: str
    language_code: str
    caption_type: Literal["manual", "generated", "unknown"]
    timing_provenance: str
    intervals: list[DetectedIntervalResponse]
    window_count: int = Field(ge=0)
    transcript_cache_hit: bool
    transcript_disk_cache_hit: bool = False
    transcript_coalesced: bool
    detection_cache_hit: bool
    detection_coalesced: bool
    provider_latency_ms: float | None = Field(ge=0, default=None)
    detection_latency_ms: float | None = Field(ge=0, default=None)
    total_latency_ms: float = Field(ge=0)
    native_budget: dict | None = None
