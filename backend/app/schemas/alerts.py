from datetime import datetime

from pydantic import BaseModel

from app.models.alert import AlertStatus
from app.models.event import EventSeverity


class AlertRead(BaseModel):
    id: str
    organization_id: str
    agent_id: str
    event_id: str
    detection_result_id: str
    title: str
    description: str
    severity: EventSeverity
    status: AlertStatus
    mitre_tactics: list[str]
    mitre_techniques: list[str]
    tags: list[str]
    created_at: datetime
    updated_at: datetime


class AlertListResponse(BaseModel):
    alerts: list[AlertRead]
    count: int
    limit: int
    skip: int


class AlertStatusUpdate(BaseModel):
    status: AlertStatus
