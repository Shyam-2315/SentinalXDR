from datetime import UTC, datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field


class AuditStatus(StrEnum):
    SUCCESS = "success"
    FAILURE = "failure"


class AuditLog(BaseModel):
    id: str
    organization_id: str | None = None
    actor_user_id: str | None = None
    actor_email: str | None = None
    actor_role: str | None = None
    action: str
    resource_type: str
    resource_id: str | None = None
    status: AuditStatus
    ip_address: str | None = None
    user_agent: str | None = None
    description: str
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
