from datetime import datetime
from typing import Any

from pydantic import BaseModel

from app.models.audit_log import AuditStatus


class AuditLogRead(BaseModel):
    id: str
    organization_id: str | None
    actor_user_id: str | None
    actor_email: str | None
    actor_role: str | None
    action: str
    resource_type: str
    resource_id: str | None
    status: AuditStatus
    ip_address: str | None
    user_agent: str | None
    description: str
    metadata: dict[str, Any]
    created_at: datetime


class AuditLogListResponse(BaseModel):
    audit_logs: list[AuditLogRead]
    count: int
    limit: int
    skip: int
