from datetime import UTC, datetime
from uuid import uuid4

from motor.motor_asyncio import AsyncIOMotorDatabase

from app.models.auth import Role, UserStatus
from app.models.user import User


class UserRepository:
    def __init__(self, database: AsyncIOMotorDatabase) -> None:
        self.collection = database["users"]

    async def count(self) -> int:
        return await self.collection.count_documents({})

    async def create(
        self,
        *,
        email: str,
        display_name: str,
        organization_id: str,
        role: Role,
        hashed_password: str,
        status: UserStatus = UserStatus.ACTIVE,
    ) -> User:
        now = datetime.now(UTC)
        user = User(
            id=f"usr_{uuid4().hex}",
            email=email.lower(),
            display_name=display_name,
            organization_id=organization_id,
            role=role,
            status=status,
            hashed_password=hashed_password,
            created_at=now,
            updated_at=now,
        )
        await self.collection.insert_one(user.model_dump(mode="json"))
        return user

    async def find_by_email(self, email: str) -> User | None:
        document = await self.collection.find_one({"email": email.lower()})
        if document is None:
            return None
        return User.model_validate(document)

    async def find_by_id(self, user_id: str) -> User | None:
        document = await self.collection.find_one({"id": user_id})
        if document is None:
            return None
        return User.model_validate(document)
