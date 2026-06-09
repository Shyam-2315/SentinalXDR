from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

from app.models.event import EventSeverity, EventSource


class EventRead(BaseModel):
    id: str
    organization_id: str
    agent_id: str
    event_type: str
    severity: EventSeverity
    source: EventSource
    title: str
    description: str | None
    raw_event: dict[str, Any]
    normalized_fields: dict[str, Any]
    tags: list[str]
    timestamp: datetime
    received_at: datetime


class EventIngestItem(BaseModel):
    event_type: str = Field(min_length=1, max_length=120)
    severity: EventSeverity
    source: EventSource
    title: str = Field(min_length=1, max_length=255)
    description: str | None = None
    raw_event: dict[str, Any]
    normalized_fields: dict[str, Any] = Field(default_factory=dict)
    tags: list[str] = Field(default_factory=list)
    timestamp: datetime | None = None


class EventIngestRequest(BaseModel):
    events: list[EventIngestItem] = Field(min_length=1)


class EventIngestResponse(BaseModel):
    accepted: int
    detections_created: int = 0
    alerts_created: int = 0
    incidents_created: int = 0
    incidents_updated: int = 0
    events: list[EventRead]


class EventListResponse(BaseModel):
    events: list[EventRead]
    count: int
    limit: int
    skip: int
