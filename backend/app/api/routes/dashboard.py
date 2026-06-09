"""Dashboard API routes.

All endpoints are read-only and accessible to VIEWER, ANALYST, ORG_ADMIN,
and SUPER_ADMIN.  All data is scoped to the authenticated user's organisation.
"""

from typing import Annotated

from fastapi import APIRouter, Depends, Query

from app.api.dependencies import (
    get_agent_repository,
    get_alert_repository,
    get_attack_chain_repository,
    get_dashboard_repository,
    get_event_repository,
    get_incident_repository,
    require_roles,
)
from app.models.auth import Role
from app.models.user import User
from app.repositories.agents import AgentRepository
from app.repositories.alerts import AlertRepository
from app.repositories.attack_chains import AttackChainRepository
from app.repositories.dashboard import DashboardRepository
from app.repositories.events import EventRepository
from app.repositories.incidents import IncidentRepository
from app.schemas.dashboard import (
    AgentHealthResponse,
    DashboardSummary,
    MitreSummary,
    RecentAlertsResponse,
    RecentAttackChainsResponse,
    RecentIncidentsResponse,
    SecurityPosture,
    SeverityTrendsResponse,
)
from app.services.dashboard_service import DashboardService

router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])

READ_ROLES = (Role.SUPER_ADMIN, Role.ORG_ADMIN, Role.ANALYST, Role.VIEWER)


def _build_service(
    dashboard_repo: Annotated[DashboardRepository, Depends(get_dashboard_repository)],
    agent_repo: Annotated[AgentRepository, Depends(get_agent_repository)],
    alert_repo: Annotated[AlertRepository, Depends(get_alert_repository)],
    incident_repo: Annotated[IncidentRepository, Depends(get_incident_repository)],
    attack_chain_repo: Annotated[AttackChainRepository, Depends(get_attack_chain_repository)],
    event_repo: Annotated[EventRepository, Depends(get_event_repository)],
) -> DashboardService:
    return DashboardService(
        dashboard_repo=dashboard_repo,
        agent_repo=agent_repo,
        alert_repo=alert_repo,
        incident_repo=incident_repo,
        attack_chain_repo=attack_chain_repo,
        event_repo=event_repo,
    )


@router.get("/summary", response_model=DashboardSummary)
async def get_summary(
    current_user: Annotated[User, Depends(require_roles(*READ_ROLES))],
    svc: Annotated[DashboardService, Depends(_build_service)],
) -> DashboardSummary:
    """High-level counts for all major entities in the organisation."""
    return await svc.get_summary(current_user.organization_id)


@router.get("/security-posture", response_model=SecurityPosture)
async def get_security_posture(
    current_user: Annotated[User, Depends(require_roles(*READ_ROLES))],
    svc: Annotated[DashboardService, Depends(_build_service)],
) -> SecurityPosture:
    """Derived security posture score (0-100) with label, risks, and actions."""
    return await svc.get_security_posture(current_user.organization_id)


@router.get("/recent-alerts", response_model=RecentAlertsResponse)
async def get_recent_alerts(
    current_user: Annotated[User, Depends(require_roles(*READ_ROLES))],
    svc: Annotated[DashboardService, Depends(_build_service)],
    limit: int = Query(default=10, ge=1, le=100),
) -> RecentAlertsResponse:
    """Most recent alerts, newest first."""
    return await svc.get_recent_alerts(current_user.organization_id, limit=limit)


@router.get("/recent-incidents", response_model=RecentIncidentsResponse)
async def get_recent_incidents(
    current_user: Annotated[User, Depends(require_roles(*READ_ROLES))],
    svc: Annotated[DashboardService, Depends(_build_service)],
    limit: int = Query(default=10, ge=1, le=100),
) -> RecentIncidentsResponse:
    """Most recent incidents, newest first."""
    return await svc.get_recent_incidents(current_user.organization_id, limit=limit)


@router.get("/recent-attack-chains", response_model=RecentAttackChainsResponse)
async def get_recent_attack_chains(
    current_user: Annotated[User, Depends(require_roles(*READ_ROLES))],
    svc: Annotated[DashboardService, Depends(_build_service)],
    limit: int = Query(default=10, ge=1, le=100),
) -> RecentAttackChainsResponse:
    """Most recent attack chains, newest first."""
    return await svc.get_recent_attack_chains(current_user.organization_id, limit=limit)


@router.get("/mitre-summary", response_model=MitreSummary)
async def get_mitre_summary(
    current_user: Annotated[User, Depends(require_roles(*READ_ROLES))],
    svc: Annotated[DashboardService, Depends(_build_service)],
) -> MitreSummary:
    """Alert counts grouped by MITRE tactic → technique × severity."""
    return await svc.get_mitre_summary(current_user.organization_id)


@router.get("/severity-trends", response_model=SeverityTrendsResponse)
async def get_severity_trends(
    current_user: Annotated[User, Depends(require_roles(*READ_ROLES))],
    svc: Annotated[DashboardService, Depends(_build_service)],
) -> SeverityTrendsResponse:
    """Daily alert counts by severity for the last 7 days."""
    return await svc.get_severity_trends(current_user.organization_id)


@router.get("/agent-health", response_model=AgentHealthResponse)
async def get_agent_health(
    current_user: Annotated[User, Depends(require_roles(*READ_ROLES))],
    svc: Annotated[DashboardService, Depends(_build_service)],
) -> AgentHealthResponse:
    """Agent health breakdown: by status, stale, recently active, disabled."""
    return await svc.get_agent_health(current_user.organization_id)
