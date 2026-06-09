from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field, field_validator

from app.models.event import EventSeverity, EventSource
from app.services.detection_engine import validate_rule_conditions


class DetectionRuleRead(BaseModel):
    id: str
    organization_id: str | None
    name: str
    description: str
    enabled: bool
    severity: EventSeverity
    source: EventSource
    event_type: str
    conditions: dict[str, Any]
    mitre_tactics: list[str]
    mitre_techniques: list[str]
    tags: list[str]
    created_at: datetime
    updated_at: datetime


class DetectionRuleCreate(BaseModel):
    name: str = Field(min_length=1, max_length=160)
    description: str = Field(min_length=1)
    enabled: bool = True
    severity: EventSeverity
    source: EventSource
    event_type: str = Field(min_length=1, max_length=120)
    conditions: dict[str, Any]
    mitre_tactics: list[str] = Field(default_factory=list)
    mitre_techniques: list[str] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)

    @field_validator("conditions")
    @classmethod
    def validate_conditions(cls, value: dict[str, Any]) -> dict[str, Any]:
        validate_rule_conditions(value)
        return value


class DetectionRuleUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=160)
    description: str | None = Field(default=None, min_length=1)
    enabled: bool | None = None
    severity: EventSeverity | None = None
    source: EventSource | None = None
    event_type: str | None = Field(default=None, min_length=1, max_length=120)
    conditions: dict[str, Any] | None = None
    mitre_tactics: list[str] | None = None
    mitre_techniques: list[str] | None = None
    tags: list[str] | None = None

    @field_validator("conditions")
    @classmethod
    def validate_conditions(cls, value: dict[str, Any] | None) -> dict[str, Any] | None:
        if value is not None:
            validate_rule_conditions(value)
        return value


class DetectionRuleListResponse(BaseModel):
    rules: list[DetectionRuleRead]


class DetectionResultRead(BaseModel):
    id: str
    organization_id: str
    agent_id: str
    event_id: str
    rule_id: str
    rule_name: str
    severity: EventSeverity
    title: str
    description: str
    mitre_tactics: list[str]
    mitre_techniques: list[str]
    matched_fields: dict[str, Any]
    created_at: datetime


class DetectionResultListResponse(BaseModel):
    results: list[DetectionResultRead]
    count: int
    limit: int
    skip: int
