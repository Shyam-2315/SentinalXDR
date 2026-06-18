from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.api.dependencies import get_audit_repository, require_roles
from app.models.audit_log import AuditLog, AuditStatus
from app.models.auth import Role
from app.models.user import User
from app.repositories.audit_logs import AuditLogRepository
from app.schemas.audit_logs import AuditLogListResponse, AuditLogRead

router = APIRouter(prefix="/audit", tags=["audit"])

AUDIT_READ_ROLES = (Role.SUPER_ADMIN, Role.ORG_ADMIN)


def to_audit_read(audit_log: AuditLog) -> AuditLogRead:
    return AuditLogRead(**audit_log.model_dump())


@router.get("", response_model=AuditLogListResponse)
async def list_audit_logs(
    current_user: Annotated[User, Depends(require_roles(*AUDIT_READ_ROLES))],
    audit_logs: Annotated[AuditLogRepository, Depends(get_audit_repository)],
    action: str | None = None,
    resource_type: str | None = None,
    actor_user_id: str | None = None,
    status_filter: Annotated[AuditStatus | None, Query(alias="status")] = None,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    limit: int = Query(default=100, ge=1, le=500),
    skip: int = Query(default=0, ge=0),
) -> AuditLogListResponse:
    organization_logs = await audit_logs.list_for_organization(
        organization_id=current_user.organization_id,
        action=action,
        resource_type=resource_type,
        actor_user_id=actor_user_id,
        status=status_filter,
        date_from=date_from,
        date_to=date_to,
        limit=limit,
        skip=skip,
    )
    return AuditLogListResponse(
        audit_logs=[to_audit_read(audit_log) for audit_log in organization_logs],
        count=len(organization_logs),
        limit=limit,
        skip=skip,
    )


@router.get("/{audit_id}", response_model=AuditLogRead)
async def get_audit_log(
    audit_id: str,
    current_user: Annotated[User, Depends(require_roles(*AUDIT_READ_ROLES))],
    audit_logs: Annotated[AuditLogRepository, Depends(get_audit_repository)],
) -> AuditLogRead:
    audit_log = await audit_logs.find_by_id_for_organization(
        audit_id=audit_id,
        organization_id=current_user.organization_id,
    )
    if audit_log is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Audit log not found")
    return to_audit_read(audit_log)
