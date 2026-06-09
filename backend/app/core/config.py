from functools import lru_cache
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


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
        default="change-me-in-production-minimum-32-chars",
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


@lru_cache
def get_settings() -> Settings:
    return Settings()
