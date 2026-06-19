from functools import lru_cache
from typing import Literal

from pydantic import AliasChoices, Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

DEFAULT_JWT_SECRET_KEY = "change-me-in-production-minimum-32-chars"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "SentinelXDR API"
    app_version: str = "0.1.0"
    environment: Literal["local", "test", "staging", "production"] = "local"
    debug: bool = False
    expose_api_docs: bool = Field(default=True, alias="EXPOSE_API_DOCS")

    api_v1_prefix: str = "/api/v1"

    mongodb_uri: str = Field(default="mongodb://mongo:27017", alias="MONGODB_URI")
    mongodb_database: str = Field(default="sentinelxdr", alias="MONGODB_DATABASE")
    mongodb_ping_timeout_ms: int = Field(default=1000, alias="MONGODB_PING_TIMEOUT_MS")

    redis_url: str = Field(default="redis://redis:6379/0", alias="REDIS_URL")
    redis_ping_timeout_seconds: float = Field(
        default=1.0,
        alias="REDIS_PING_TIMEOUT_SECONDS",
    )

    jwt_secret_key: str = Field(
        default=DEFAULT_JWT_SECRET_KEY,
        alias="JWT_SECRET_KEY",
    )
    jwt_algorithm: str = Field(default="HS256", alias="JWT_ALGORITHM")
    access_token_expire_minutes: int = Field(default=15, alias="ACCESS_TOKEN_EXPIRE_MINUTES")
    refresh_token_expire_days: int = Field(default=7, alias="REFRESH_TOKEN_EXPIRE_DAYS")

    agent_api_key_bytes: int = Field(default=32, alias="AGENT_API_KEY_BYTES")
    event_ingest_batch_size_limit: int = Field(
        default=100,
        alias="EVENT_INGEST_BATCH_SIZE_LIMIT",
    )
    incident_correlation_window_minutes: int = Field(
        default=30,
        alias="INCIDENT_CORRELATION_WINDOW_MINUTES",
    )
    evidence_storage_root: str = Field(default="storage/evidence", alias="EVIDENCE_STORAGE_ROOT")
    evidence_max_upload_mb: int = Field(default=25, alias="EVIDENCE_MAX_UPLOAD_MB")
    cors_allowed_origins: str = Field(
        default=(
            "http://localhost:5173,http://127.0.0.1:5173,"
            "http://localhost:3000,http://127.0.0.1:3000"
        ),
        validation_alias=AliasChoices("BACKEND_CORS_ORIGINS", "CORS_ALLOWED_ORIGINS"),
    )

    @property
    def cors_origins(self) -> list[str]:
        return [
            origin.strip()
            for origin in self.cors_allowed_origins.split(",")
            if origin.strip()
        ]

    @model_validator(mode="after")
    def validate_production_settings(self) -> "Settings":
        if self.environment != "production":
            return self

        errors: list[str] = []
        if self.debug:
            errors.append("DEBUG=true is not allowed when ENVIRONMENT=production")
        if self.jwt_secret_key == DEFAULT_JWT_SECRET_KEY:
            errors.append("JWT_SECRET_KEY must be changed when ENVIRONMENT=production")
        if "*" in self.cors_origins:
            errors.append("Wildcard CORS origins are not allowed when ENVIRONMENT=production")

        if errors:
            raise ValueError("; ".join(errors))
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()
