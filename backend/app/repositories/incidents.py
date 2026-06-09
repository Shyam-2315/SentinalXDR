from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import uuid4

from motor.motor_asyncio import AsyncIOMotorDatabase
from pymongo import ReturnDocument

from app.models.alert import Alert
from app.models.event import EventSeverity
from app.models.incident import Incident, IncidentStatus

SEVERITY_RANK: dict[EventSeverity, int] = {
    EventSeverity.INFO: 0,
    EventSeverity.LOW: 1,
    EventSeverity.MEDIUM: 2,
    EventSeverity.HIGH: 3,
    EventSeverity.CRITICAL: 4,
}


def max_severity(left: EventSeverity, right: EventSeverity) -> EventSeverity:
    return left if SEVERITY_RANK[left] >= SEVERITY_RANK[right] else right


def append_unique(existing: list[str], values: list[str]) -> list[str]:
    merged = list(existing)
    for value in values:
        if value not in merged:
            merged.append(value)
    return merged


def merge_unique(existing: list[str], values: list[str]) -> list[str]:
    return append_unique(existing, values)


class IncidentRepository:
    def __init__(self, database: AsyncIOMotorDatabase) -> None:
        self.collection = database["incidents"]

    async def find_matching_open_incident(
        self,
        *,
        alert: Alert,
        correlation_window_minutes: int,
    ) -> Incident | None:
        earliest = alert.created_at - timedelta(minutes=correlation_window_minutes)
        statuses = [IncidentStatus.OPEN.value, IncidentStatus.INVESTIGATING.value]
        query = {
            "organization_id": alert.organization_id,
            "agent_ids": alert.agent_id,
            "status": {"$in": statuses},
            "last_seen_at": {"$gte": earliest},
            "$or": [
                {"title": alert.title},
                {"mitre_techniques": {"$in": alert.mitre_techniques[:1]}},
            ],
        }
        document = await self.collection.find_one(query, sort=[("last_seen_at", -1)])
        if document is None:
            return None
        return Incident.model_validate(document)

    async def create_from_alert(self, alert: Alert) -> Incident:
        now = datetime.now(UTC)
        incident = Incident(
            id=f"inc_{uuid4().hex}",
            organization_id=alert.organization_id,
            title=alert.title,
            description=alert.description,
            severity=alert.severity,
            status=IncidentStatus.OPEN,
            alert_ids=[alert.id],
            detection_result_ids=[alert.detection_result_id],
            event_ids=[alert.event_id],
            agent_ids=[alert.agent_id],
            mitre_tactics=alert.mitre_tactics,
            mitre_techniques=alert.mitre_techniques,
            tags=alert.tags,
            first_seen_at=alert.created_at,
            last_seen_at=alert.created_at,
            created_at=now,
            updated_at=now,
        )
        await self.collection.insert_one(incident.model_dump(mode="json"))
        return incident

    async def append_alert(self, *, incident: Incident, alert: Alert) -> Incident:
        update_fields = {
            "severity": max_severity(incident.severity, alert.severity).value,
            "alert_ids": append_unique(incident.alert_ids, [alert.id]),
            "detection_result_ids": append_unique(
                incident.detection_result_ids,
                [alert.detection_result_id],
            ),
            "event_ids": append_unique(incident.event_ids, [alert.event_id]),
            "agent_ids": append_unique(incident.agent_ids, [alert.agent_id]),
            "mitre_tactics": merge_unique(incident.mitre_tactics, alert.mitre_tactics),
            "mitre_techniques": merge_unique(incident.mitre_techniques, alert.mitre_techniques),
            "tags": merge_unique(incident.tags, alert.tags),
            "last_seen_at": max(incident.last_seen_at, alert.created_at),
            "updated_at": datetime.now(UTC),
        }
        document = await self.collection.find_one_and_update(
            {"id": incident.id, "organization_id": incident.organization_id},
            {"$set": update_fields},
            return_document=ReturnDocument.AFTER,
        )
        if document is None:
            return incident
        return Incident.model_validate(document)

    async def list_by_organization(
        self,
        *,
        organization_id: str,
        status: IncidentStatus | None = None,
        severity: EventSeverity | None = None,
        agent_id: str | None = None,
        mitre_technique: str | None = None,
        limit: int = 100,
        skip: int = 0,
    ) -> list[Incident]:
        query: dict[str, Any] = {"organization_id": organization_id}
        if status is not None:
            query["status"] = status.value
        if severity is not None:
            query["severity"] = severity.value
        if agent_id is not None:
            query["agent_ids"] = agent_id
        if mitre_technique is not None:
            query["mitre_techniques"] = mitre_technique

        cursor = (
            self.collection.find(query)
            .sort("updated_at", -1)
            .skip(skip)
            .limit(limit)
        )
        return [Incident.model_validate(document) async for document in cursor]

    async def find_by_id_for_organization(
        self,
        *,
        incident_id: str,
        organization_id: str,
    ) -> Incident | None:
        document = await self.collection.find_one(
            {"id": incident_id, "organization_id": organization_id},
        )
        if document is None:
            return None
        return Incident.model_validate(document)

    async def update_status(
        self,
        *,
        incident_id: str,
        organization_id: str,
        status: IncidentStatus,
    ) -> Incident | None:
        return await self._set_fields(
            incident_id=incident_id,
            organization_id=organization_id,
            fields={"status": status.value},
        )

    async def update_assignment(
        self,
        *,
        incident_id: str,
        organization_id: str,
        assigned_to_user_id: str | None,
    ) -> Incident | None:
        return await self._set_fields(
            incident_id=incident_id,
            organization_id=organization_id,
            fields={"assigned_to_user_id": assigned_to_user_id},
        )

    async def update_summary(
        self,
        *,
        incident_id: str,
        organization_id: str,
        summary: str | None,
    ) -> Incident | None:
        return await self._set_fields(
            incident_id=incident_id,
            organization_id=organization_id,
            fields={"summary": summary},
        )

    async def _set_fields(
        self,
        *,
        incident_id: str,
        organization_id: str,
        fields: dict[str, Any],
    ) -> Incident | None:
        document = await self.collection.find_one_and_update(
            {"id": incident_id, "organization_id": organization_id},
            {"$set": {**fields, "updated_at": datetime.now(UTC)}},
            return_document=ReturnDocument.AFTER,
        )
        if document is None:
            return None
        return Incident.model_validate(document)
