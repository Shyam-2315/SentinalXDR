from time import perf_counter
from typing import Any

from fastapi import APIRouter, status
from fastapi.responses import JSONResponse

from app.core.config import get_settings
from app.db.mongodb import mongodb
from app.db.redis import redis_store

router = APIRouter(prefix="/health", tags=["health"])


def _health_response(payload: dict[str, Any], healthy: bool) -> JSONResponse:
    status_code = status.HTTP_200_OK if healthy else status.HTTP_503_SERVICE_UNAVAILABLE
    return JSONResponse(status_code=status_code, content=payload)


async def _check_dependency(name: str, ping) -> tuple[dict[str, Any], bool]:
    started_at = perf_counter()
    healthy = await ping()
    latency_ms = round((perf_counter() - started_at) * 1000, 2)

    return (
        {
            "name": name,
            "status": "healthy" if healthy else "unhealthy",
            "latency_ms": latency_ms,
        },
        healthy,
    )


@router.get("/live")
async def live() -> dict[str, str]:
    settings = get_settings()
    return {
        "status": "ok",
        "service": settings.app_name,
        "version": settings.app_version,
    }


@router.get("/ready")
async def ready() -> JSONResponse:
    db_status, db_healthy = await _check_dependency("mongodb", mongodb.ping)
    redis_status, redis_healthy = await _check_dependency("redis", redis_store.ping)
    healthy = db_healthy and redis_healthy

    return _health_response(
        {
            "status": "ready" if healthy else "not_ready",
            "dependencies": {
                "mongodb": db_status,
                "redis": redis_status,
            },
        },
        healthy,
    )


@router.get("/db")
async def db() -> JSONResponse:
    db_status, healthy = await _check_dependency("mongodb", mongodb.ping)
    return _health_response(db_status, healthy)


@router.get("/redis")
async def redis() -> JSONResponse:
    redis_status, healthy = await _check_dependency("redis", redis_store.ping)
    return _health_response(redis_status, healthy)
