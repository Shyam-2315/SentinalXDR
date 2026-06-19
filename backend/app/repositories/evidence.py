from datetime import UTC, datetime
from typing import Any

from motor.motor_asyncio import AsyncIOMotorDatabase
from pymongo import ReturnDocument

from app.models.evidence import (
    Evidence,
    EvidenceCustodyEvent,
    EvidenceStatus,
    EvidenceVerificationStatus,
)


class EvidenceRepository:
    def __init__(self, database: AsyncIOMotorDatabase) -> None:
        self.collection = database["evidence"]

    async def create(self, evidence: Evidence) -> Evidence:
        await self.collection.insert_one(evidence.model_dump(mode="json"))
        return evidence

    async def list_by_organization(
        self,
        *,
        organization_id: str,
        incident_id: str | None = None,
        status: EvidenceStatus | None = None,
        verification_status: EvidenceVerificationStatus | None = None,
        tag: str | None = None,
        limit: int = 100,
        skip: int = 0,
    ) -> list[Evidence]:
        query: dict[str, Any] = {"organization_id": organization_id}
        if incident_id is not None:
            query["incident_id"] = incident_id
        if status is not None:
            query["status"] = status.value
        if verification_status is not None:
            query["verification_status"] = verification_status.value
        if tag is not None:
            query["tags"] = tag

        cursor = self.collection.find(query).sort("created_at", -1).skip(skip).limit(limit)
        return [Evidence.model_validate(document) async for document in cursor]

    async def count_by_organization(
        self,
        *,
        organization_id: str,
        incident_id: str | None = None,
        status: EvidenceStatus | None = None,
        verification_status: EvidenceVerificationStatus | None = None,
        tag: str | None = None,
    ) -> int:
        query: dict[str, Any] = {"organization_id": organization_id}
        if incident_id is not None:
            query["incident_id"] = incident_id
        if status is not None:
            query["status"] = status.value
        if verification_status is not None:
            query["verification_status"] = verification_status.value
        if tag is not None:
            query["tags"] = tag
        return await self.collection.count_documents(query)

    async def find_by_id_for_organization(
        self,
        *,
        evidence_id: str,
        organization_id: str,
    ) -> Evidence | None:
        document = await self.collection.find_one(
            {"id": evidence_id, "organization_id": organization_id},
        )
        if document is None:
            return None
        return Evidence.model_validate(document)

    async def set_incident(
        self,
        *,
        evidence_id: str,
        organization_id: str,
        incident_id: str | None,
    ) -> Evidence | None:
        return await self._set_fields(
            evidence_id=evidence_id,
            organization_id=organization_id,
            fields={"incident_id": incident_id},
        )

    async def set_status(
        self,
        *,
        evidence_id: str,
        organization_id: str,
        status: EvidenceStatus,
    ) -> Evidence | None:
        return await self._set_fields(
            evidence_id=evidence_id,
            organization_id=organization_id,
            fields={"status": status.value},
        )

    async def set_verification(
        self,
        *,
        evidence_id: str,
        organization_id: str,
        verification_status: EvidenceVerificationStatus,
        last_verified_at: datetime,
    ) -> Evidence | None:
        return await self._set_fields(
            evidence_id=evidence_id,
            organization_id=organization_id,
            fields={
                "verification_status": verification_status.value,
                "last_verified_at": last_verified_at,
            },
        )

    async def _set_fields(
        self,
        *,
        evidence_id: str,
        organization_id: str,
        fields: dict[str, Any],
    ) -> Evidence | None:
        document = await self.collection.find_one_and_update(
            {"id": evidence_id, "organization_id": organization_id},
            {"$set": {**fields, "updated_at": datetime.now(UTC)}},
            return_document=ReturnDocument.AFTER,
        )
        if document is None:
            return None
        return Evidence.model_validate(document)


class EvidenceCustodyRepository:
    def __init__(self, database: AsyncIOMotorDatabase) -> None:
        self.collection = database["evidence_custody"]

    async def create(self, event: EvidenceCustodyEvent) -> EvidenceCustodyEvent:
        await self.collection.insert_one(event.model_dump(mode="json"))
        return event

    async def list_for_evidence(
        self,
        *,
        organization_id: str,
        evidence_id: str,
        limit: int = 500,
        skip: int = 0,
        newest_first: bool = False,
    ) -> list[EvidenceCustodyEvent]:
        sort_direction = -1 if newest_first else 1
        cursor = (
            self.collection.find({"organization_id": organization_id, "evidence_id": evidence_id})
            .sort("created_at", sort_direction)
            .skip(skip)
            .limit(limit)
        )
        return [EvidenceCustodyEvent.model_validate(document) async for document in cursor]
