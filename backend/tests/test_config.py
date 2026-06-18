import pytest
from pydantic import ValidationError

from app.core.config import DEFAULT_JWT_SECRET_KEY, Settings


def set_valid_production_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ENVIRONMENT", "production")
    monkeypatch.setenv("DEBUG", "false")
    monkeypatch.setenv("JWT_SECRET_KEY", "test-production-secret-with-at-least-32-characters")
    monkeypatch.setenv("BACKEND_CORS_ORIGINS", "https://sentinelxdr.example.com")


def test_valid_production_settings_are_allowed(monkeypatch: pytest.MonkeyPatch) -> None:
    set_valid_production_env(monkeypatch)

    settings = Settings()

    assert settings.environment == "production"
    assert settings.debug is False
    assert settings.cors_origins == ["https://sentinelxdr.example.com"]


def test_production_rejects_debug_true(monkeypatch: pytest.MonkeyPatch) -> None:
    set_valid_production_env(monkeypatch)
    monkeypatch.setenv("DEBUG", "true")

    with pytest.raises(ValidationError, match="DEBUG=true is not allowed"):
        Settings()


def test_production_rejects_default_jwt_secret(monkeypatch: pytest.MonkeyPatch) -> None:
    set_valid_production_env(monkeypatch)
    monkeypatch.setenv("JWT_SECRET_KEY", DEFAULT_JWT_SECRET_KEY)

    with pytest.raises(ValidationError, match="JWT_SECRET_KEY must be changed"):
        Settings()


def test_production_rejects_wildcard_cors(monkeypatch: pytest.MonkeyPatch) -> None:
    set_valid_production_env(monkeypatch)
    monkeypatch.setenv("BACKEND_CORS_ORIGINS", "https://sentinelxdr.example.com,*")

    with pytest.raises(ValidationError, match="Wildcard CORS origins"):
        Settings()
