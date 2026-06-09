from datetime import UTC, datetime

from motor.motor_asyncio import AsyncIOMotorDatabase
from pymongo import ReturnDocument

from app.models.alert import Alert, AlertStatus
from app.models.detection import DetectionResult


class AlertRepository:
    def __init__(self, database: AsyncIOMotorDatabase) -> None:
        self.collection = database["alerts"]

    async def create_from_detection_result(
        self,
        result: DetectionResult,
        tags: list[str] | None = None,
    ) -> Alert:
        now = datetime.now(UTC)
        alert = Alert(
            id=f"alr_{result.id.removeprefix('det_')}",
            organization_id=result.organization_id,
            agent_id=result.agent_id,
            event_id=result.event_id,
            detection_result_id=result.id,
            title=result.title,
            description=result.description,
            severity=result.severity,
            status=AlertStatus.OPEN,
            mitre_tactics=result.mitre_tactics,
            mitre_techniques=result.mitre_techniques,
            tags=tags or [],
            created_at=now,
            updated_at=now,
        )
        await self.collection.insert_one(alert.model_dump(mode="json"))
        return alert

    async def list_by_organization(
        self,
        *,
        organization_id: str,
        limit: int = 100,
        skip: int = 0,
    ) -> list[Alert]:
        cursor = (
            self.collection.find({"organization_id": organization_id})
            .sort("created_at", -1)
            .skip(skip)
            .limit(limit)
        )
        return [Alert.model_validate(document) async for document in cursor]

    async def find_by_id_for_organization(
        self,
        *,
        alert_id: str,
        organization_id: str,
    ) -> Alert | None:
        document = await self.collection.find_one(
            {"id": alert_id, "organization_id": organization_id},
        )
        if document is None:
            return None
        return Alert.model_validate(document)

    async def update_status(
        self,
        *,
        alert_id: str,
        organization_id: str,
        status: AlertStatus,
    ) -> Alert | None:
        document = await self.collection.find_one_and_update(
            {"id": alert_id, "organization_id": organization_id},
            {"$set": {"status": status.value, "updated_at": datetime.now(UTC)}},
            return_document=ReturnDocument.AFTER,
        )
        if document is None:
            return None
        return Alert.model_validate(document)
