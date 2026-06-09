from datetime import UTC, datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field


class EventSeverity(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"
    INFO = "info"


class EventSource(StrEnum):
    WINDOWS = "windows"
    LINUX = "linux"
    NETWORK = "network"
    CLOUD = "cloud"
    IDENTITY = "identity"
    WEB = "web"
    AGENT = "agent"


class Event(BaseModel):
    id: str
    organization_id: str
    agent_id: str
    event_type: str
    severity: EventSeverity
    source: EventSource
    title: str
    description: str | None = None
    raw_event: dict[str, Any]
    normalized_fields: dict[str, Any] = Field(default_factory=dict)
    tags: list[str] = Field(default_factory=list)
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))
    received_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
