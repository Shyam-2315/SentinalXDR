from __future__ import annotations

import logging
from typing import Any
from uuid import uuid4

from fastapi import Request

from app.models.audit_log import AuditLog, AuditStatus
from app.models.user import User
from app.repositories.audit_logs import AuditLogRepository

logger = logging.getLogger(__name__)

SENSITIVE_KEY_FRAGMENTS = (
    "password",
    "token",
    "api_key",
    "apikey",
    "agent_key",
    "authorization",
    "jwt",
    "secret",
)
REDACTED = "[REDACTED]"


def redact_sensitive(value: Any) -> Any:
    if isinstance(value, dict):
        redacted: dict[str, Any] = {}
        for key, item in value.items():
            key_text = str(key).lower()
            if any(fragment in key_text for fragment in SENSITIVE_KEY_FRAGMENTS):
                redacted[key] = REDACTED
            else:
                redacted[key] = redact_sensitive(item)
        return redacted
    if isinstance(value, list):
        return [redact_sensitive(item) for item in value]
    return value


class AuditService:
    def __init__(self, repository: AuditLogRepository | None) -> None:
        self.repository = repository

    async def log(
        self,
        *,
        action: str,
        resource_type: str,
        status: AuditStatus = AuditStatus.SUCCESS,
        description: str,
        request: Request | None = None,
        current_user: User | None = None,
        organization_id: str | None = None,
        actor_user_id: str | None = None,
        actor_email: str | None = None,
        actor_role: str | None = None,
        resource_id: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        if self.repository is None:
            return

        try:
            audit_log = AuditLog(
                id=f"aud_{uuid4().hex}",
                organization_id=organization_id
                if organization_id is not None
                else current_user.organization_id
                if current_user is not None
                else None,
                actor_user_id=actor_user_id
                if actor_user_id is not None
                else current_user.id
                if current_user is not None
                else None,
                actor_email=actor_email
                if actor_email is not None
                else str(current_user.email)
                if current_user is not None
                else None,
                actor_role=actor_role
                if actor_role is not None
                else current_user.role.value
                if current_user is not None
                else None,
                action=action,
                resource_type=resource_type,
                resource_id=resource_id,
                status=status,
                ip_address=request.client.host if request is not None and request.client else None,
                user_agent=request.headers.get("user-agent") if request is not None else None,
                description=description,
                metadata=redact_sensitive(metadata or {}),
            )
            await self.repository.create(audit_log)
        except Exception:
            logger.warning("Audit log write failed", exc_info=True)
