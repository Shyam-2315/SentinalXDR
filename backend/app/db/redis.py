from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from redis.asyncio import Redis
from redis.exceptions import RedisError

from app.core.config import Settings


class RedisStore:
    def __init__(self) -> None:
        self.client: Redis | None = None

    async def connect(self, settings: Settings) -> None:
        self.client = Redis.from_url(
            settings.redis_url,
            socket_connect_timeout=settings.redis_ping_timeout_seconds,
            socket_timeout=settings.redis_ping_timeout_seconds,
            decode_responses=True,
        )

    async def close(self) -> None:
        if self.client is not None:
            await self.client.aclose()
        self.client = None

    async def ping(self) -> bool:
        if self.client is None:
            return False

        try:
            return bool(await self.client.ping())
        except RedisError:
            return False


redis_store = RedisStore()


def get_redis() -> Redis:
    if redis_store.client is None:
        raise RuntimeError("Redis client is not initialized")
    return redis_store.client


@asynccontextmanager
async def redis_lifespan(settings: Settings) -> AsyncIterator[RedisStore]:
    await redis_store.connect(settings)
    try:
        yield redis_store
    finally:
        await redis_store.close()
