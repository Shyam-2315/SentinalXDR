"""Dashboard service — assembles repository data into dashboard response models."""

from datetime import UTC, datetime, timedelta

from app.models.agent import AgentStatus
from app.models.event import EventSeverity
from app.repositories.agents import AgentRepository
from app.repositories.alerts import AlertRepository
from app.repositories.attack_chains import AttackChainRepository
from app.repositories.dashboard import DashboardRepository
from app.repositories.events import EventRepository
from app.repositories.incidents import IncidentRepository
from app.schemas.alerts import AlertRead
from app.schemas.attack_chains import AttackChainRead
from app.schemas.dashboard import (
    AgentHealthResponse,
    AgentStatusGroup,
    DashboardSummary,
    MitreSummary,
    MitreTacticGroup,
    MitreTechniqueCount,
    RecentAlertsResponse,
    RecentAttackChainsResponse,
    RecentIncidentsResponse,
    SecurityPosture,
    SeverityDayBucket,
    SeverityTrendsResponse,
)
from app.schemas.incidents import IncidentRead

_STALE_THRESHOLD_MINUTES = 5

# Ordered severity list from lowest to highest for posture scoring
_SEVERITY_RANK = {
    EventSeverity.INFO: 0,
    EventSeverity.LOW: 1,
    EventSeverity.MEDIUM: 2,
    EventSeverity.HIGH: 3,
    EventSeverity.CRITICAL: 4,
}


def _compute_posture(
    *,
    critical_alerts: int,
    high_alerts: int,
    open_incidents: int,
    active_attack_chains: int,
    total_agents: int,
    online_agents: int,
) -> SecurityPosture:
    """Derive a 0-100 posture score from key risk signals.

    Scoring starts at 100 and deducts points for open risk items:
      - Each critical alert: -10 (cap at -40)
      - Each high alert:     -4  (cap at -20)
      - Each open incident:  -5  (cap at -15)
      - Each active chain:   -5  (cap at -15)
      - Agent coverage gap:  up to -10

    Minimum score is 0; maximum is 100.
    """
    score = 100

    score -= min(critical_alerts * 10, 40)
    score -= min(high_alerts * 4, 20)
    score -= min(open_incidents * 5, 15)
    score -= min(active_attack_chains * 5, 15)

    if total_agents > 0:
        coverage_ratio = online_agents / total_agents
        gap_penalty = round((1.0 - coverage_ratio) * 10)
        score -= gap_penalty

    score = max(0, min(100, score))

    if score >= 90:
        label = "excellent"
    elif score >= 75:
        label = "good"
    elif score >= 55:
        label = "moderate"
    elif score >= 35:
        label = "risky"
    else:
        label = "critical"

    top_risks: list[str] = []
    if critical_alerts > 0:
        top_risks.append(f"{critical_alerts} critical alert(s) require immediate attention")
    if high_alerts > 0:
        top_risks.append(f"{high_alerts} high-severity alert(s) unresolved")
    if open_incidents > 0:
        top_risks.append(f"{open_incidents} open incident(s) under investigation")
    if active_attack_chains > 0:
        top_risks.append(f"{active_attack_chains} active attack chain(s) detected")
    if total_agents > 0 and online_agents < total_agents:
        offline = total_agents - online_agents
        top_risks.append(f"{offline} agent(s) offline or unreachable")

    recommended_actions: list[str] = []
    if critical_alerts > 0:
        recommended_actions.append("Triage and resolve all critical alerts immediately")
    if high_alerts > 0:
        recommended_actions.append("Review and close high-severity alerts")
    if open_incidents > 0:
        recommended_actions.append("Assign open incidents to analysts for investigation")
    if active_attack_chains > 0:
        recommended_actions.append("Contain or resolve active attack chains")
    if total_agents > 0 and online_agents < total_agents:
        recommended_actions.append("Investigate and restore offline agents")
    if not recommended_actions:
        recommended_actions.append("No immediate actions required — maintain monitoring")

    return SecurityPosture(
        posture_score=score,
        posture_label=label,
        top_risks=top_risks,
        recommended_actions=recommended_actions,
    )


class DashboardService:
    def __init__(
        self,
        dashboard_repo: DashboardRepository,
        agent_repo: AgentRepository,
        alert_repo: AlertRepository,
        incident_repo: IncidentRepository,
        attack_chain_repo: AttackChainRepository,
        event_repo: EventRepository,
    ) -> None:
        self._dash = dashboard_repo
        self._agents = agent_repo
        self._alerts = alert_repo
        self._incidents = incident_repo
        self._chains = attack_chain_repo
        self._events = event_repo

    # ------------------------------------------------------------------
    # Summary
    # ------------------------------------------------------------------

    async def get_summary(self, organization_id: str) -> DashboardSummary:
        agent_counts = await self._dash.count_agents_by_status(organization_id)
        severity_counts = await self._dash.count_alerts_by_severity(organization_id)

        return DashboardSummary(
            total_agents=agent_counts.get("total", 0),
            online_agents=agent_counts.get(AgentStatus.ONLINE.value, 0),
            offline_agents=agent_counts.get(AgentStatus.OFFLINE.value, 0),
            disabled_agents=agent_counts.get(AgentStatus.DISABLED.value, 0),
            total_events=await self._dash.count_events(organization_id),
            total_alerts=await self._dash.count_alerts(organization_id),
            open_alerts=await self._dash.count_open_alerts(organization_id),
            total_incidents=await self._dash.count_incidents(organization_id),
            open_incidents=await self._dash.count_open_incidents(organization_id),
            total_attack_chains=await self._dash.count_attack_chains(organization_id),
            active_attack_chains=await self._dash.count_active_attack_chains(organization_id),
            critical_alerts=severity_counts.get(EventSeverity.CRITICAL.value, 0),
            high_alerts=severity_counts.get(EventSeverity.HIGH.value, 0),
            risk_score_average=await self._dash.average_attack_chain_risk_score(organization_id),
        )

    # ------------------------------------------------------------------
    # Security posture
    # ------------------------------------------------------------------

    async def get_security_posture(self, organization_id: str) -> SecurityPosture:
        agent_counts = await self._dash.count_agents_by_status(organization_id)
        severity_counts = await self._dash.count_alerts_by_severity(organization_id)

        return _compute_posture(
            critical_alerts=severity_counts.get(EventSeverity.CRITICAL.value, 0),
            high_alerts=severity_counts.get(EventSeverity.HIGH.value, 0),
            open_incidents=await self._dash.count_open_incidents(organization_id),
            active_attack_chains=await self._dash.count_active_attack_chains(organization_id),
            total_agents=agent_counts.get("total", 0),
            online_agents=agent_counts.get(AgentStatus.ONLINE.value, 0),
        )

    # ------------------------------------------------------------------
    # Recent items
    # ------------------------------------------------------------------

    async def get_recent_alerts(
        self, organization_id: str, limit: int = 10
    ) -> RecentAlertsResponse:
        alerts = await self._alerts.list_by_organization(
            organization_id=organization_id, limit=limit
        )
        return RecentAlertsResponse(
            alerts=[AlertRead(**a.model_dump()) for a in alerts],
            count=len(alerts),
        )

    async def get_recent_incidents(
        self, organization_id: str, limit: int = 10
    ) -> RecentIncidentsResponse:
        incidents = await self._incidents.list_by_organization(
            organization_id=organization_id, limit=limit
        )
        return RecentIncidentsResponse(
            incidents=[IncidentRead(**i.model_dump()) for i in incidents],
            count=len(incidents),
        )

    async def get_recent_attack_chains(
        self, organization_id: str, limit: int = 10
    ) -> RecentAttackChainsResponse:
        chains = await self._chains.list_by_organization(
            organization_id=organization_id, limit=limit
        )
        return RecentAttackChainsResponse(
            attack_chains=[AttackChainRead(**c.model_dump()) for c in chains],
            count=len(chains),
        )

    # ------------------------------------------------------------------
    # MITRE summary
    # ------------------------------------------------------------------

    async def get_mitre_summary(self, organization_id: str) -> MitreSummary:
        rows = await self._dash.mitre_tactic_technique_counts(organization_id)

        # Group by tactic
        tactic_map: dict[str, list[MitreTechniqueCount]] = {}
        for row in rows:
            tactic = row["tactic"]
            if tactic not in tactic_map:
                tactic_map[tactic] = []
            tactic_map[tactic].append(
                MitreTechniqueCount(
                    technique=row["technique"],
                    severity=EventSeverity(row["severity"]),
                    count=row["count"],
                )
            )

        tactics = [
            MitreTacticGroup(
                tactic=tactic,
                total=sum(t.count for t in techs),
                techniques=techs,
            )
            for tactic, techs in sorted(tactic_map.items())
        ]
        return MitreSummary(tactics=tactics)

    # ------------------------------------------------------------------
    # Severity trends
    # ------------------------------------------------------------------

    async def get_severity_trends(
        self, organization_id: str, days: int = 7
    ) -> SeverityTrendsResponse:
        rows = await self._dash.alert_severity_by_day(organization_id, days=days)

        # Build a lookup: date -> severity -> count
        bucket_map: dict[str, dict[str, int]] = {}
        for row in rows:
            d = row["date"]
            if d not in bucket_map:
                bucket_map[d] = {}
            bucket_map[d][row["severity"]] = row["count"]

        # Fill in all days in range (even if no alerts)
        today = datetime.now(UTC).date()
        result: list[SeverityDayBucket] = []
        for offset in range(days - 1, -1, -1):
            day = today - timedelta(days=offset)
            day_str = day.isoformat()
            counts = bucket_map.get(day_str, {})
            result.append(
                SeverityDayBucket(
                    date=day_str,
                    info=counts.get(EventSeverity.INFO.value, 0),
                    low=counts.get(EventSeverity.LOW.value, 0),
                    medium=counts.get(EventSeverity.MEDIUM.value, 0),
                    high=counts.get(EventSeverity.HIGH.value, 0),
                    critical=counts.get(EventSeverity.CRITICAL.value, 0),
                )
            )
        return SeverityTrendsResponse(days=result)

    # ------------------------------------------------------------------
    # Agent health
    # ------------------------------------------------------------------

    async def get_agent_health(self, organization_id: str) -> AgentHealthResponse:
        agent_counts = await self._dash.count_agents_by_status(organization_id)
        stale = await self._dash.count_stale_agents(organization_id)
        recently_active = await self._dash.count_recently_active_agents(organization_id)

        by_status = [
            AgentStatusGroup(status=status, count=count)
            for status, count in agent_counts.items()
            if status != "total"
        ]

        return AgentHealthResponse(
            by_status=by_status,
            stale_count=stale,
            recently_active_count=recently_active,
            disabled_count=agent_counts.get(AgentStatus.DISABLED.value, 0),
            total=agent_counts.get("total", 0),
        )
