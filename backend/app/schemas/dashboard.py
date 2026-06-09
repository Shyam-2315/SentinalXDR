from pydantic import BaseModel

from app.models.event import EventSeverity
from app.schemas.alerts import AlertRead
from app.schemas.attack_chains import AttackChainRead
from app.schemas.incidents import IncidentRead

# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------


class DashboardSummary(BaseModel):
    total_agents: int
    online_agents: int
    offline_agents: int
    disabled_agents: int
    total_events: int
    total_alerts: int
    open_alerts: int
    total_incidents: int
    open_incidents: int
    total_attack_chains: int
    active_attack_chains: int
    critical_alerts: int
    high_alerts: int
    risk_score_average: float


# ---------------------------------------------------------------------------
# Security posture
# ---------------------------------------------------------------------------


class SecurityPosture(BaseModel):
    posture_score: int  # 0-100
    posture_label: str  # excellent | good | moderate | risky | critical
    top_risks: list[str]
    recommended_actions: list[str]


# ---------------------------------------------------------------------------
# Recent items
# ---------------------------------------------------------------------------


class RecentAlertsResponse(BaseModel):
    alerts: list[AlertRead]
    count: int


class RecentIncidentsResponse(BaseModel):
    incidents: list[IncidentRead]
    count: int


class RecentAttackChainsResponse(BaseModel):
    attack_chains: list[AttackChainRead]
    count: int


# ---------------------------------------------------------------------------
# MITRE summary
# ---------------------------------------------------------------------------


class MitreTechniqueCount(BaseModel):
    technique: str
    severity: EventSeverity
    count: int


class MitreTacticGroup(BaseModel):
    tactic: str
    total: int
    techniques: list[MitreTechniqueCount]


class MitreSummary(BaseModel):
    tactics: list[MitreTacticGroup]


# ---------------------------------------------------------------------------
# Severity trends
# ---------------------------------------------------------------------------


class SeverityDayBucket(BaseModel):
    date: str  # ISO date string, e.g. "2026-06-09"
    info: int
    low: int
    medium: int
    high: int
    critical: int


class SeverityTrendsResponse(BaseModel):
    days: list[SeverityDayBucket]


# ---------------------------------------------------------------------------
# Agent health
# ---------------------------------------------------------------------------


class AgentStatusGroup(BaseModel):
    status: str
    count: int


class AgentHealthResponse(BaseModel):
    by_status: list[AgentStatusGroup]
    stale_count: int  # online but no heartbeat in > 5 minutes
    recently_active_count: int  # heartbeat within last 5 minutes
    disabled_count: int
    total: int
