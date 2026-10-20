from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

DEFAULT_TRIAL_BUDGET_PATH = Path(__file__).resolve().parents[3] / "results/trial-budget.sqlite3"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="YTSS_",
        env_file=".env",
        extra="ignore",
    )

    environment: str = "local"
    allowed_origins_csv: str = "http://localhost"
    request_timeout_seconds: float = Field(default=10.0, gt=0, le=60)
    max_concurrent_acquisitions: int = Field(default=4, ge=1, le=16)
    cache_ttl_seconds: int = Field(default=900, ge=0, le=86_400)
    cache_max_entries: int = Field(default=128, ge=1, le=10_000)
    request_limit_per_minute: int = Field(default=60, ge=1, le=10_000)
    api_token: str | None = None
    transcript_provider: Literal["youtube", "supadata"] = "youtube"
    detector_variant: Literal["frozen_rules", "contextual_v1"] = "frozen_rules"
    trial_budget_path: Path = DEFAULT_TRIAL_BUDGET_PATH
    trial_attempt_limit: int = Field(default=50, ge=2, le=50)
    trial_poll_limit: int = Field(default=5, ge=1, le=5)
    supadata_api_key: SecretStr | None = Field(
        default=None, validation_alias="SUPADATA_API_KEY", repr=False
    )

    @field_validator("allowed_origins_csv")
    @classmethod
    def require_origins(cls, value: str) -> str:
        if not any(part.strip() for part in value.split(",")):
            raise ValueError("at least one allowed origin is required")
        return value

    @property
    def allowed_origins(self) -> list[str]:
        return [part.strip() for part in self.allowed_origins_csv.split(",") if part.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
