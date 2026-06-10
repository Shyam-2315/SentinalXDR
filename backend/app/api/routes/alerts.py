from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.api.dependencies import get_alert_repository, require_roles
from app.models.alert import Alert
from app.models.auth import Role
from app.models.user import User
from app.repositories.alerts import AlertRepository
from app.schemas.alerts import AlertListResponse, AlertRead, AlertStatusUpdate

router = APIRouter(prefix="/alerts", tags=["alerts"])

READ_ROLES = (Role.SUPER_ADMIN, Role.ORG_ADMIN, Role.ANALYST, Role.VIEWER)
UPDATE_ROLES = (Role.SUPER_ADMIN, Role.ORG_ADMIN, Role.ANALYST)


def to_alert_read(alert: Alert) -> AlertRead:
    return AlertRead(**alert.model_dump())


@router.get("", response_model=AlertListResponse)
async def list_alerts(
    current_user: Annotated[User, Depends(require_roles(*READ_ROLES))],
    alerts: Annotated[AlertRepository, Depends(get_alert_repository)],
    limit: int = Query(default=100, ge=1, le=500),
    skip: int = Query(default=0, ge=0),
) -> AlertListResponse:
    organization_alerts = await alerts.list_by_organization(
        organization_id=current_user.organization_id,
        limit=limit,
        skip=skip,
    )
    return AlertListResponse(
        alerts=[to_alert_read(alert) for alert in organization_alerts],
        count=len(organization_alerts),
        limit=limit,
        skip=skip,
    )


@router.get("/{alert_id}", response_model=AlertRead)
async def get_alert(
    alert_id: str,
    current_user: Annotated[User, Depends(require_roles(*READ_ROLES))],
    alerts: Annotated[AlertRepository, Depends(get_alert_repository)],
) -> AlertRead:
    alert = await alerts.find_by_id_for_organization(
        alert_id=alert_id,
        organization_id=current_user.organization_id,
    )
    if alert is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Alert not found")
    return to_alert_read(alert)


@router.patch("/{alert_id}/status", response_model=AlertRead)
async def update_alert_status(
    alert_id: str,
    payload: AlertStatusUpdate,
    current_user: Annotated[User, Depends(require_roles(*UPDATE_ROLES))],
    alerts: Annotated[AlertRepository, Depends(get_alert_repository)],
) -> AlertRead:
    alert = await alerts.update_status(
        alert_id=alert_id,
        organization_id=current_user.organization_id,
        status=payload.status,
    )
    if alert is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Alert not found")
    return to_alert_read(alert)
