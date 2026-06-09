from datetime import UTC, datetime
from typing import Any

from motor.motor_asyncio import AsyncIOMotorDatabase
from pymongo import ReturnDocument

from app.models.attack_chain import AttackChain, AttackChainStatus
from app.models.event import EventSeverity


class AttackChainRepository:
    def __init__(self, database: AsyncIOMotorDatabase) -> None:
        self.collection = database["attack_chains"]

    async def upsert_for_incident(self, chain: AttackChain) -> AttackChain:
        existing = await self.find_by_incident_for_organization(
            incident_id=chain.incident_id,
            organization_id=chain.organization_id,
        )
        if existing is None:
            await self.collection.insert_one(chain.model_dump(mode="json"))
            return chain

        document = await self.collection.find_one_and_update(
            {"id": existing.id, "organization_id": existing.organization_id},
            {
                "$set": {
                    **chain.model_dump(mode="json", exclude={"id", "created_at", "status"}),
                    "updated_at": datetime.now(UTC),
                }
            },
            return_document=ReturnDocument.AFTER,
        )
        if document is None:
            return chain
        return AttackChain.model_validate(document)

    async def list_by_organization(
        self,
        *,
        organization_id: str,
        status: AttackChainStatus | None = None,
        severity: EventSeverity | None = None,
        agent_id: str | None = None,
        mitre_technique: str | None = None,
        min_risk_score: float | None = None,
        limit: int = 100,
        skip: int = 0,
    ) -> list[AttackChain]:
        query: dict[str, Any] = {"organization_id": organization_id}
        if status is not None:
            query["status"] = status.value
        if severity is not None:
            query["severity"] = severity.value
        if agent_id is not None:
            query["agent_ids"] = agent_id
        if mitre_technique is not None:
            query["mitre_techniques"] = mitre_technique
        if min_risk_score is not None:
            query["risk_score"] = {"$gte": min_risk_score}

        cursor = (
            self.collection.find(query)
            .sort("updated_at", -1)
            .skip(skip)
            .limit(limit)
        )
        return [AttackChain.model_validate(document) async for document in cursor]

    async def find_by_id_for_organization(
        self,
        *,
        chain_id: str,
        organization_id: str,
    ) -> AttackChain | None:
        document = await self.collection.find_one(
            {"id": chain_id, "organization_id": organization_id},
        )
        if document is None:
            return None
        return AttackChain.model_validate(document)

    async def find_by_incident_for_organization(
        self,
        *,
        incident_id: str,
        organization_id: str,
    ) -> AttackChain | None:
        document = await self.collection.find_one(
            {"incident_id": incident_id, "organization_id": organization_id},
        )
        if document is None:
            return None
        return AttackChain.model_validate(document)

    async def update_status(
        self,
        *,
        chain_id: str,
        organization_id: str,
        status: AttackChainStatus,
    ) -> AttackChain | None:
        document = await self.collection.find_one_and_update(
            {"id": chain_id, "organization_id": organization_id},
            {"$set": {"status": status.value, "updated_at": datetime.now(UTC)}},
            return_document=ReturnDocument.AFTER,
        )
        if document is None:
            return None
        return AttackChain.model_validate(document)
