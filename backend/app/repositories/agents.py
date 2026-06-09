from datetime import UTC, datetime
from uuid import uuid4

from motor.motor_asyncio import AsyncIOMotorDatabase
from pymongo import ReturnDocument

from app.core.security import verify_agent_api_key
from app.models.agent import Agent, AgentStatus, OSType


class AgentRepository:
    def __init__(self, database: AsyncIOMotorDatabase) -> None:
        self.collection = database["agents"]

    async def create(
        self,
        *,
        organization_id: str,
        name: str,
        hostname: str,
        os_type: OSType,
        agent_version: str | None,
        api_key_hash: str,
        ip_address: str | None = None,
        tags: list[str] | None = None,
    ) -> Agent:
        now = datetime.now(UTC)
        agent = Agent(
            id=f"agt_{uuid4().hex}",
            organization_id=organization_id,
            name=name,
            hostname=hostname,
            os_type=os_type,
            agent_version=agent_version,
            status=AgentStatus.OFFLINE,
            api_key_hash=api_key_hash,
            ip_address=ip_address,
            tags=tags or [],
            created_at=now,
            updated_at=now,
        )
        await self.collection.insert_one(agent.model_dump(mode="json"))
        return agent

    async def list_by_organization(self, organization_id: str) -> list[Agent]:
        cursor = self.collection.find({"organization_id": organization_id}).sort("created_at", -1)
        return [Agent.model_validate(document) async for document in cursor]

    async def find_by_id_for_organization(
        self,
        *,
        agent_id: str,
        organization_id: str,
    ) -> Agent | None:
        document = await self.collection.find_one(
            {"id": agent_id, "organization_id": organization_id},
        )
        if document is None:
            return None
        return Agent.model_validate(document)

    async def find_by_api_key(self, api_key: str) -> Agent | None:
        async for document in self.collection.find({}):
            if verify_agent_api_key(api_key, document["api_key_hash"]):
                return Agent.model_validate(document)
        return None

    async def update_heartbeat(
        self,
        *,
        agent_id: str,
        ip_address: str | None,
        agent_version: str | None,
    ) -> Agent | None:
        now = datetime.now(UTC)
        update_fields: dict[str, object] = {
            "last_seen_at": now,
            "status": AgentStatus.ONLINE.value,
            "updated_at": now,
        }
        if ip_address is not None:
            update_fields["ip_address"] = ip_address
        if agent_version is not None:
            update_fields["agent_version"] = agent_version

        document = await self.collection.find_one_and_update(
            {"id": agent_id},
            {"$set": update_fields},
            return_document=ReturnDocument.AFTER,
        )
        if document is None:
            return None
        return Agent.model_validate(document)

    async def disable(self, *, agent_id: str, organization_id: str) -> Agent | None:
        now = datetime.now(UTC)
        document = await self.collection.find_one_and_update(
            {"id": agent_id, "organization_id": organization_id},
            {"$set": {"status": AgentStatus.DISABLED.value, "updated_at": now}},
            return_document=ReturnDocument.AFTER,
        )
        if document is None:
            return None
        return Agent.model_validate(document)
