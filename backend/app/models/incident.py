from datetime import UTC, datetime
from enum import StrEnum

from pydantic import BaseModel, Field

from app.models.event import EventSeverity


class IncidentStatus(StrEnum):
    OPEN = "open"
    INVESTIGATING = "investigating"
    CONTAINED = "contained"
    RESOLVED = "resolved"
    FALSE_POSITIVE = "false_positive"


class Incident(BaseModel):
    id: str
    organization_id: str
    title: str
    description: str
    severity: EventSeverity
    status: IncidentStatus = IncidentStatus.OPEN
    alert_ids: list[str] = Field(default_factory=list)
    detection_result_ids: list[str] = Field(default_factory=list)
    event_ids: list[str] = Field(default_factory=list)
    agent_ids: list[str] = Field(default_factory=list)
    mitre_tactics: list[str] = Field(default_factory=list)
    mitre_techniques: list[str] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)
    first_seen_at: datetime
    last_seen_at: datetime
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    assigned_to_user_id: str | None = None
    summary: str | None = None
