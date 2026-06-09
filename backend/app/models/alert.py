from datetime import UTC, datetime
from enum import StrEnum

from pydantic import BaseModel, Field

from app.models.event import EventSeverity


class AlertStatus(StrEnum):
    OPEN = "open"
    INVESTIGATING = "investigating"
    RESOLVED = "resolved"
    FALSE_POSITIVE = "false_positive"


class Alert(BaseModel):
    id: str
    organization_id: str
    agent_id: str
    event_id: str
    detection_result_id: str
    title: str
    description: str
    severity: EventSeverity
    status: AlertStatus = AlertStatus.OPEN
    mitre_tactics: list[str] = Field(default_factory=list)
    mitre_techniques: list[str] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
