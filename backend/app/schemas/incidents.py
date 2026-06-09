from datetime import datetime

from pydantic import BaseModel

from app.models.event import EventSeverity
from app.models.incident import IncidentStatus


class IncidentRead(BaseModel):
    id: str
    organization_id: str
    title: str
    description: str
    severity: EventSeverity
    status: IncidentStatus
    alert_ids: list[str]
    detection_result_ids: list[str]
    event_ids: list[str]
    agent_ids: list[str]
    mitre_tactics: list[str]
    mitre_techniques: list[str]
    tags: list[str]
    first_seen_at: datetime
    last_seen_at: datetime
    created_at: datetime
    updated_at: datetime
    assigned_to_user_id: str | None
    summary: str | None


class IncidentListResponse(BaseModel):
    incidents: list[IncidentRead]
    count: int
    limit: int
    skip: int


class IncidentStatusUpdate(BaseModel):
    status: IncidentStatus


class IncidentAssignUpdate(BaseModel):
    assigned_to_user_id: str | None


class IncidentSummaryUpdate(BaseModel):
    summary: str | None
