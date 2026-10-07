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
    is_generated: bool
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
