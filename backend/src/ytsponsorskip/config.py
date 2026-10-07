from functools import lru_cache

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


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
