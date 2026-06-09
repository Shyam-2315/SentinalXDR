from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from motor.motor_asyncio import AsyncIOMotorDatabase

from app.models.event import Event, EventSeverity, EventSource
from app.schemas.events import EventIngestItem


class EventRepository:
    def __init__(self, database: AsyncIOMotorDatabase) -> None:
        self.collection = database["events"]

    async def create_many(
        self,
        *,
        organization_id: str,
        agent_id: str,
        event_items: list[EventIngestItem],
    ) -> list[Event]:
        received_at = datetime.now(UTC)
        events = [
            Event(
                id=f"evt_{uuid4().hex}",
                organization_id=organization_id,
                agent_id=agent_id,
                event_type=item.event_type,
                severity=item.severity,
                source=item.source,
                title=item.title,
                description=item.description,
                raw_event=item.raw_event,
                normalized_fields=item.normalized_fields,
                tags=item.tags,
                timestamp=item.timestamp or received_at,
                received_at=received_at,
            )
            for item in event_items
        ]
        if events:
            await self.collection.insert_many([event.model_dump(mode="json") for event in events])
        return events

    async def list_by_organization(
        self,
        *,
        organization_id: str,
        severity: EventSeverity | None = None,
        source: EventSource | None = None,
        event_type: str | None = None,
        agent_id: str | None = None,
        limit: int = 100,
        skip: int = 0,
    ) -> list[Event]:
        query: dict[str, Any] = {"organization_id": organization_id}
        if severity is not None:
            query["severity"] = severity.value
        if source is not None:
            query["source"] = source.value
        if event_type is not None:
            query["event_type"] = event_type
        if agent_id is not None:
            query["agent_id"] = agent_id

        cursor = (
            self.collection.find(query)
            .sort("received_at", -1)
            .skip(skip)
            .limit(limit)
        )
        return [Event.model_validate(document) async for document in cursor]

    async def find_by_id_for_organization(
        self,
        *,
        event_id: str,
        organization_id: str,
    ) -> Event | None:
        document = await self.collection.find_one(
            {"id": event_id, "organization_id": organization_id},
        )
        if document is None:
            return None
        return Event.model_validate(document)

    async def find_many_by_ids_for_organization(
        self,
        *,
        event_ids: list[str],
        organization_id: str,
    ) -> list[Event]:
        cursor = self.collection.find(
            {"id": {"$in": event_ids}, "organization_id": organization_id},
        )
        return [Event.model_validate(document) async for document in cursor]
