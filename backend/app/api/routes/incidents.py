from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status

from app.api.dependencies import (
    get_audit_service,
    get_incident_repository,
    get_user_repository,
    require_roles,
)
from app.models.auth import Role
from app.models.event import EventSeverity
from app.models.incident import Incident, IncidentStatus
from app.models.user import User
from app.repositories.incidents import IncidentRepository
from app.repositories.users import UserRepository
from app.schemas.incidents import (
    IncidentAssignUpdate,
    IncidentListResponse,
    IncidentRead,
    IncidentStatusUpdate,
    IncidentSummaryUpdate,
)
from app.services.audit_service import AuditService

router = APIRouter(prefix="/incidents", tags=["incidents"])

READ_ROLES = (Role.SUPER_ADMIN, Role.ORG_ADMIN, Role.ANALYST, Role.VIEWER)
UPDATE_ROLES = (Role.SUPER_ADMIN, Role.ORG_ADMIN, Role.ANALYST)
REOPEN_ROLES = (Role.SUPER_ADMIN, Role.ORG_ADMIN)

ALLOWED_TRANSITIONS: dict[IncidentStatus, set[IncidentStatus]] = {
    IncidentStatus.OPEN: {
        IncidentStatus.INVESTIGATING,
        IncidentStatus.CONTAINED,
        IncidentStatus.RESOLVED,
        IncidentStatus.FALSE_POSITIVE,
    },
    IncidentStatus.INVESTIGATING: {
        IncidentStatus.CONTAINED,
        IncidentStatus.RESOLVED,
        IncidentStatus.FALSE_POSITIVE,
    },
    IncidentStatus.CONTAINED: {IncidentStatus.RESOLVED},
    IncidentStatus.RESOLVED: set(),
    IncidentStatus.FALSE_POSITIVE: set(),
}


def to_incident_read(incident: Incident) -> IncidentRead:
    return IncidentRead(**incident.model_dump())


@router.get("", response_model=IncidentListResponse)
async def list_incidents(
    current_user: Annotated[User, Depends(require_roles(*READ_ROLES))],
    incidents: Annotated[IncidentRepository, Depends(get_incident_repository)],
    status_filter: Annotated[IncidentStatus | None, Query(alias="status")] = None,
    severity: EventSeverity | None = None,
    agent_id: str | None = None,
    mitre_technique: str | None = None,
    limit: int = Query(default=100, ge=1, le=500),
    skip: int = Query(default=0, ge=0),
) -> IncidentListResponse:
    organization_incidents = await incidents.list_by_organization(
        organization_id=current_user.organization_id,
        status=status_filter,
        severity=severity,
        agent_id=agent_id,
        mitre_technique=mitre_technique,
        limit=limit,
        skip=skip,
    )
    return IncidentListResponse(
        incidents=[to_incident_read(incident) for incident in organization_incidents],
        count=len(organization_incidents),
        limit=limit,
        skip=skip,
    )


@router.get("/{incident_id}", response_model=IncidentRead)
async def get_incident(
    incident_id: str,
    current_user: Annotated[User, Depends(require_roles(*READ_ROLES))],
    incidents: Annotated[IncidentRepository, Depends(get_incident_repository)],
) -> IncidentRead:
    incident = await incidents.find_by_id_for_organization(
        incident_id=incident_id,
        organization_id=current_user.organization_id,
    )
    if incident is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Incident not found")
    return to_incident_read(incident)


@router.patch("/{incident_id}/status", response_model=IncidentRead)
async def update_incident_status(
    incident_id: str,
    payload: IncidentStatusUpdate,
    request: Request,
    current_user: Annotated[User, Depends(require_roles(*UPDATE_ROLES))],
    incidents: Annotated[IncidentRepository, Depends(get_incident_repository)],
    audit: Annotated[AuditService, Depends(get_audit_service)],
) -> IncidentRead:
    incident = await incidents.find_by_id_for_organization(
        incident_id=incident_id,
        organization_id=current_user.organization_id,
    )
    if incident is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Incident not found")

    if not is_status_transition_allowed(incident.status, payload.status, current_user.role):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid incident status transition",
        )

    updated = await incidents.update_status(
        incident_id=incident.id,
        organization_id=current_user.organization_id,
        status=payload.status,
    )
    if updated is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Incident not found")
    await audit.log(
        action="incident.status_update",
        resource_type="incident",
        resource_id=updated.id,
        description="Incident status updated",
        request=request,
        current_user=current_user,
        metadata={
            "previous_status": incident.status.value,
            "status": updated.status.value,
            "title": updated.title,
        },
    )
    return to_incident_read(updated)


@router.patch("/{incident_id}/assign", response_model=IncidentRead)
async def assign_incident(
    incident_id: str,
    payload: IncidentAssignUpdate,
    request: Request,
    current_user: Annotated[User, Depends(require_roles(*UPDATE_ROLES))],
    incidents: Annotated[IncidentRepository, Depends(get_incident_repository)],
    users: Annotated[UserRepository, Depends(get_user_repository)],
    audit: Annotated[AuditService, Depends(get_audit_service)],
) -> IncidentRead:
    incident = await incidents.find_by_id_for_organization(
        incident_id=incident_id,
        organization_id=current_user.organization_id,
    )
    if incident is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Incident not found")

    if payload.assigned_to_user_id is not None:
        assignee = await users.find_by_id(payload.assigned_to_user_id)
        if assignee is None or assignee.organization_id != current_user.organization_id:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    updated = await incidents.update_assignment(
        incident_id=incident.id,
        organization_id=current_user.organization_id,
        assigned_to_user_id=payload.assigned_to_user_id,
    )
    if updated is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Incident not found")
    await audit.log(
        action="incident.assign",
        resource_type="incident",
        resource_id=updated.id,
        description="Incident assignment updated",
        request=request,
        current_user=current_user,
        metadata={
            "previous_assigned_to_user_id": incident.assigned_to_user_id,
            "assigned_to_user_id": updated.assigned_to_user_id,
            "title": updated.title,
        },
    )
    return to_incident_read(updated)


@router.patch("/{incident_id}/summary", response_model=IncidentRead)
async def update_incident_summary(
    incident_id: str,
    payload: IncidentSummaryUpdate,
    request: Request,
    current_user: Annotated[User, Depends(require_roles(*UPDATE_ROLES))],
    incidents: Annotated[IncidentRepository, Depends(get_incident_repository)],
    audit: Annotated[AuditService, Depends(get_audit_service)],
) -> IncidentRead:
    incident = await incidents.update_summary(
        incident_id=incident_id,
        organization_id=current_user.organization_id,
        summary=payload.summary,
    )
    if incident is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Incident not found")
    await audit.log(
        action="incident.summary_update",
        resource_type="incident",
        resource_id=incident.id,
        description="Incident summary updated",
        request=request,
        current_user=current_user,
        metadata={"title": incident.title, "summary_present": bool(incident.summary)},
    )
    return to_incident_read(incident)


def is_status_transition_allowed(
    current_status: IncidentStatus,
    next_status: IncidentStatus,
    role: Role,
) -> bool:
    if current_status == next_status:
        return True
    if next_status == IncidentStatus.OPEN and current_status in {
        IncidentStatus.RESOLVED,
        IncidentStatus.FALSE_POSITIVE,
    }:
        return role in REOPEN_ROLES
    return next_status in ALLOWED_TRANSITIONS[current_status]
