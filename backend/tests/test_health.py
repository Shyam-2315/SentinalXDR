from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient

from app.core.config import get_settings
from app.db.mongodb import mongodb
from app.db.redis import redis_store
from app.main import app


@pytest.fixture(autouse=True)
def clear_settings_cache() -> Iterator[None]:
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


@pytest.fixture
def client() -> Iterator[TestClient]:
    with TestClient(app) as test_client:
        yield test_client


def set_dependency_health(monkeypatch: pytest.MonkeyPatch, *, db: bool, redis: bool) -> None:
    async def db_ping() -> bool:
        return db

    async def redis_ping() -> bool:
        return redis

    monkeypatch.setattr(mongodb, "ping", db_ping)
    monkeypatch.setattr(redis_store, "ping", redis_ping)


def test_live_health(client: TestClient) -> None:
    response = client.get("/health/live")

    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_db_health_success(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    set_dependency_health(monkeypatch, db=True, redis=True)

    response = client.get("/health/db")

    assert response.status_code == 200
    assert response.json()["status"] == "healthy"
    assert response.json()["name"] == "mongodb"


def test_db_health_failure(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    set_dependency_health(monkeypatch, db=False, redis=True)

    response = client.get("/health/db")

    assert response.status_code == 503
    assert response.json()["status"] == "unhealthy"


def test_redis_health_success(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    set_dependency_health(monkeypatch, db=True, redis=True)

    response = client.get("/health/redis")

    assert response.status_code == 200
    assert response.json()["status"] == "healthy"
    assert response.json()["name"] == "redis"


def test_redis_health_failure(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    set_dependency_health(monkeypatch, db=True, redis=False)

    response = client.get("/health/redis")

    assert response.status_code == 503
    assert response.json()["status"] == "unhealthy"


def test_ready_health_success(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    set_dependency_health(monkeypatch, db=True, redis=True)

    response = client.get("/health/ready")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ready"
    assert body["dependencies"]["mongodb"]["status"] == "healthy"
    assert body["dependencies"]["redis"]["status"] == "healthy"


def test_cors_allows_frontend_localhost_origin(client: TestClient) -> None:
    response = client.options(
        "/api/dashboard/summary",
        headers={
            "Origin": "http://localhost:5173",
            "Access-Control-Request-Method": "GET",
        },
    )

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "http://localhost:5173"


@pytest.mark.parametrize(
    ("db_healthy", "redis_healthy"),
    [
        (False, True),
        (True, False),
        (False, False),
    ],
)
def test_ready_health_failure(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
    db_healthy: bool,
    redis_healthy: bool,
) -> None:
    set_dependency_health(monkeypatch, db=db_healthy, redis=redis_healthy)

    response = client.get("/health/ready")

    assert response.status_code == 503
    assert response.json()["status"] == "not_ready"
