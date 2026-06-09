from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from pymongo.errors import PyMongoError

from app.core.config import Settings


class MongoDB:
    def __init__(self) -> None:
        self.client: AsyncIOMotorClient | None = None
        self.database: AsyncIOMotorDatabase | None = None

    async def connect(self, settings: Settings) -> None:
        self.client = AsyncIOMotorClient(
            settings.mongodb_uri,
            serverSelectionTimeoutMS=settings.mongodb_ping_timeout_ms,
        )
        self.database = self.client[settings.mongodb_database]

    async def close(self) -> None:
        if self.client is not None:
            self.client.close()
        self.client = None
        self.database = None

    async def ping(self) -> bool:
        if self.client is None:
            return False

        try:
            await self.client.admin.command("ping")
        except PyMongoError:
            return False
        return True


mongodb = MongoDB()


def get_database() -> AsyncIOMotorDatabase:
    if mongodb.database is None:
        raise RuntimeError("MongoDB database is not initialized")
    return mongodb.database


@asynccontextmanager
async def mongo_lifespan(settings: Settings) -> AsyncIterator[MongoDB]:
    await mongodb.connect(settings)
    try:
        yield mongodb
    finally:
        await mongodb.close()
