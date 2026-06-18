from datetime import UTC, datetime
from uuid import uuid4

from motor.motor_asyncio import AsyncIOMotorDatabase

from app.models.organization import Organization


class OrganizationRepository:
    def __init__(self, database: AsyncIOMotorDatabase) -> None:
        self.collection = database["organizations"]

    async def count(self) -> int:
        return await self.collection.count_documents({})

    async def create(self, name: str) -> Organization:
        now = datetime.now(UTC)
        organization = Organization(
            id=f"org_{uuid4().hex}",
            name=name,
            created_at=now,
            updated_at=now,
        )
        await self.collection.insert_one(organization.model_dump(mode="json"))
        return organization

    async def find_by_id(self, organization_id: str) -> Organization | None:
        document = await self.collection.find_one({"id": organization_id})
        if document is None:
            return None
        return Organization.model_validate(document)
