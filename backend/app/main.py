from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.router import build_api_router
from app.api.routes.health import router as health_router
from app.core.config import get_settings
from app.db.mongodb import mongodb
from app.db.redis import redis_store


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    settings = get_settings()
    if settings.environment == "test":
        yield
        return
    await mongodb.connect(settings)
    await redis_store.connect(settings)
    try:
        yield
    finally:
        await redis_store.close()
        await mongodb.close()


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        debug=settings.debug,
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
        lifespan=lifespan,
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(build_api_router(), prefix="/api")
    app.include_router(health_router)
    app.include_router(build_api_router(), prefix=settings.api_v1_prefix)
    return app


app = create_app()
