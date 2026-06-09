from datetime import UTC, datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field

from app.models.event import EventSeverity, EventSource


class ConditionOperator(StrEnum):
    EQUALS = "equals"
    CONTAINS = "contains"
    REGEX = "regex"
    IN = "in"
    GT = "gt"
    GTE = "gte"
    LT = "lt"
    LTE = "lte"


class DetectionRule(BaseModel):
    id: str
    organization_id: str | None = None
    name: str
    description: str
    enabled: bool = True
    severity: EventSeverity
    source: EventSource
    event_type: str
    conditions: dict[str, Any]
    mitre_tactics: list[str] = Field(default_factory=list)
    mitre_techniques: list[str] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class DetectionResult(BaseModel):
    id: str
    organization_id: str
    agent_id: str
    event_id: str
    rule_id: str
    rule_name: str
    severity: EventSeverity
    title: str
    description: str
    mitre_tactics: list[str] = Field(default_factory=list)
    mitre_techniques: list[str] = Field(default_factory=list)
    matched_fields: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
