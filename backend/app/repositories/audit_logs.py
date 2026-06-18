from datetime import datetime
from typing import Any

from motor.motor_asyncio import AsyncIOMotorDatabase

from app.models.audit_log import AuditLog, AuditStatus


class AuditLogRepository:
    def __init__(self, database: AsyncIOMotorDatabase) -> None:
        self.collection = database["audit_logs"]

    async def create(self, audit_log: AuditLog) -> AuditLog:
        await self.collection.insert_one(audit_log.model_dump(mode="json"))
        return audit_log

    async def list_for_organization(
        self,
        *,
        organization_id: str,
        action: str | None = None,
        resource_type: str | None = None,
        actor_user_id: str | None = None,
        status: AuditStatus | None = None,
        date_from: datetime | None = None,
        date_to: datetime | None = None,
        limit: int = 100,
        skip: int = 0,
    ) -> list[AuditLog]:
        query = self._build_query(
            organization_id=organization_id,
            action=action,
            resource_type=resource_type,
            actor_user_id=actor_user_id,
            status=status,
            date_from=date_from,
            date_to=date_to,
        )
        cursor = (
            self.collection.find(query)
            .sort("created_at", -1)
            .skip(skip)
            .limit(limit)
        )
        return [AuditLog.model_validate(document) async for document in cursor]

    async def find_by_id_for_organization(
        self,
        *,
        audit_id: str,
        organization_id: str,
    ) -> AuditLog | None:
        document = await self.collection.find_one(
            {"id": audit_id, "organization_id": organization_id},
        )
        if document is None:
            return None
        return AuditLog.model_validate(document)

    def _build_query(
        self,
        *,
        organization_id: str,
        action: str | None,
        resource_type: str | None,
        actor_user_id: str | None,
        status: AuditStatus | None,
        date_from: datetime | None,
        date_to: datetime | None,
    ) -> dict[str, Any]:
        query: dict[str, Any] = {"organization_id": organization_id}
        if action is not None:
            query["action"] = action
        if resource_type is not None:
            query["resource_type"] = resource_type
        if actor_user_id is not None:
            query["actor_user_id"] = actor_user_id
        if status is not None:
            query["status"] = status.value
        if date_from is not None or date_to is not None:
            created_at: dict[str, datetime] = {}
            if date_from is not None:
                created_at["$gte"] = date_from
            if date_to is not None:
                created_at["$lte"] = date_to
            query["created_at"] = created_at
        return query
