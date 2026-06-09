from collections import Counter
from datetime import UTC, datetime
from uuid import uuid4

from app.models.agent import Agent
from app.models.alert import Alert
from app.models.attack_chain import (
    AttackChain,
    AttackChainStatus,
    AttackGraph,
    AttackGraphEdge,
    AttackGraphNode,
    GraphNodeType,
    TimelineNode,
    TimelineNodeType,
)
from app.models.detection import DetectionResult
from app.models.event import Event, EventSeverity
from app.models.incident import Incident
from app.repositories.agents import AgentRepository
from app.repositories.alerts import AlertRepository
from app.repositories.attack_chains import AttackChainRepository
from app.repositories.detections import DetectionResultRepository
from app.repositories.events import EventRepository

SEVERITY_WEIGHT: dict[EventSeverity, float] = {
    EventSeverity.INFO: 10,
    EventSeverity.LOW: 20,
    EventSeverity.MEDIUM: 40,
    EventSeverity.HIGH: 65,
    EventSeverity.CRITICAL: 80,
}

TACTIC_PHASE_MAP = {
    "reconnaissance": "reconnaissance",
    "initial access": "initial_access",
    "execution": "execution",
    "persistence": "persistence",
    "privilege escalation": "privilege_escalation",
    "defense evasion": "defense_evasion",
    "credential access": "credential_access",
    "discovery": "discovery",
    "lateral movement": "lateral_movement",
    "collection": "collection",
    "command and control": "command_and_control",
    "exfiltration": "exfiltration",
    "impact": "impact",
}

TECHNIQUE_PHASE_MAP = {
    "T1595": "reconnaissance",
    "T1059": "execution",
    "T1059.001": "execution",
    "T1053.003": "persistence",
    "T1027": "defense_evasion",
    "T1003": "credential_access",
    "T1110": "credential_access",
    "T1041": "exfiltration",
}


class AttackChainEngine:
    def __init__(
        self,
        chains: AttackChainRepository,
        events: EventRepository,
        results: DetectionResultRepository,
        alerts: AlertRepository,
        agents: AgentRepository,
    ) -> None:
        self.chains = chains
        self.events = events
        self.results = results
        self.alerts = alerts
        self.agents = agents

    async def process_incidents(self, incidents: list[Incident]) -> list[AttackChain]:
        chains: list[AttackChain] = []
        for incident in incidents:
            events = await self.events.find_many_by_ids_for_organization(
                event_ids=incident.event_ids,
                organization_id=incident.organization_id,
            )
            results = await self.results.find_many_by_ids_for_organization(
                result_ids=incident.detection_result_ids,
                organization_id=incident.organization_id,
            )
            alerts = await self.alerts.find_many_by_ids_for_organization(
                alert_ids=incident.alert_ids,
                organization_id=incident.organization_id,
            )
            agents = await self.agents.find_many_by_ids_for_organization(
                agent_ids=incident.agent_ids,
                organization_id=incident.organization_id,
            )
            chains.append(
                await self.chains.upsert_for_incident(
                    build_attack_chain(
                        incident=incident,
                        events=events,
                        results=results,
                        alerts=alerts,
                        agents=agents,
                    )
                )
            )
        return chains


def build_attack_chain(
    *,
    incident: Incident,
    events: list[Event],
    results: list[DetectionResult],
    alerts: list[Alert],
    agents: list[Agent],
) -> AttackChain:
    risk_score = calculate_risk_score(incident, alerts, results)
    confidence_score = calculate_confidence_score(events, results, alerts)
    phases = kill_chain_phases(incident.mitre_tactics, incident.mitre_techniques)
    recommended_actions = build_recommended_actions(
        severity=incident.severity,
        mitre_tactics=incident.mitre_tactics,
        mitre_techniques=incident.mitre_techniques,
        results=results,
    )
    story = build_story(
        incident=incident,
        agents=agents,
        alert_count=len(alerts),
        risk_score=risk_score,
        phases=phases,
        actions=recommended_actions,
    )
    return AttackChain(
        id=f"chain_{uuid4().hex}",
        organization_id=incident.organization_id,
        incident_id=incident.id,
        agent_ids=dedupe(incident.agent_ids),
        alert_ids=dedupe(incident.alert_ids),
        detection_result_ids=dedupe(incident.detection_result_ids),
        event_ids=dedupe(incident.event_ids),
        title=f"Attack chain: {incident.title}",
        summary=incident.summary or incident.description,
        severity=incident.severity,
        risk_score=risk_score,
        confidence_score=confidence_score,
        kill_chain_phases=phases,
        mitre_tactics=dedupe(incident.mitre_tactics),
        mitre_techniques=dedupe(incident.mitre_techniques),
        timeline=build_timeline(incident, events, results, alerts),
        graph=build_graph(incident, events, results, alerts, agents),
        story=story,
        recommended_actions=recommended_actions,
        status=AttackChainStatus.ACTIVE,
        first_seen_at=incident.first_seen_at,
        last_seen_at=incident.last_seen_at,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )


def calculate_risk_score(
    incident: Incident,
    alerts: list[Alert],
    results: list[DetectionResult],
) -> float:
    score = SEVERITY_WEIGHT[incident.severity]
    score += min(len(alerts) * 3, 15)
    score += min(len(set(incident.mitre_techniques)) * 5, 20)
    score += min(
        sum(
            1
            for result in results
            if result.severity in {EventSeverity.HIGH, EventSeverity.CRITICAL}
        )
        * 5,
        20,
    )
    result_names = " ".join(result.rule_name.lower() for result in results)
    if "vm-based attacker fingerprint" in result_names:
        score += 10
    if "large outbound transfer" in result_names or "T1041" in incident.mitre_techniques:
        score += 10
    return min(round(score, 2), 100.0)


def calculate_confidence_score(
    events: list[Event],
    results: list[DetectionResult],
    alerts: list[Alert],
) -> float:
    event_types = {event.event_type for event in events}
    techniques = {technique for result in results for technique in result.mitre_techniques}
    detections_by_agent = Counter(result.agent_id for result in results)
    repeated_agent_boost = 10 if any(count > 1 for count in detections_by_agent.values()) else 0
    score = (
        30
        + min(len(alerts), 5) * 8
        + len(event_types) * 8
        + len(techniques) * 6
        + repeated_agent_boost
    )
    return min(round(score, 2), 100.0)


def kill_chain_phases(tactics: list[str], techniques: list[str]) -> list[str]:
    phases: list[str] = []
    for tactic in tactics:
        phase = TACTIC_PHASE_MAP.get(tactic.lower())
        if phase and phase not in phases:
            phases.append(phase)
    for technique in techniques:
        phase = TECHNIQUE_PHASE_MAP.get(technique)
        if phase and phase not in phases:
            phases.append(phase)
    return phases


def build_recommended_actions(
    *,
    severity: EventSeverity,
    mitre_tactics: list[str],
    mitre_techniques: list[str],
    results: list[DetectionResult],
) -> list[str]:
    actions: list[str] = []
    phases = set(kill_chain_phases(mitre_tactics, mitre_techniques))
    result_names = " ".join(result.rule_name.lower() for result in results)
    if severity in {EventSeverity.HIGH, EventSeverity.CRITICAL}:
        actions.extend(["isolate endpoint", "collect evidence", "reset credentials"])
    if "credential_access" in phases:
        actions.extend(["reset credentials", "inspect LSASS/auth logs"])
    if "execution" in phases:
        actions.extend(["review process tree", "quarantine binary/script"])
    if "persistence" in phases:
        actions.append("inspect cron/startup/registry autoruns")
    if "exfiltration" in phases:
        actions.extend(["block outbound destination", "review data access logs"])
    if "reconnaissance" in phases:
        actions.extend(["block source IP", "monitor repeated scanning"])
    if "vm-based attacker fingerprint" in result_names:
        actions.append("investigate lab/unknown VM source and NAT host")
    return dedupe(actions)


def build_story(
    *,
    incident: Incident,
    agents: list[Agent],
    alert_count: int,
    risk_score: float,
    phases: list[str],
    actions: list[str],
) -> str:
    host = agents[0].hostname if agents else incident.agent_ids[0]
    phase_text = ", followed by ".join(phases) if phases else "security-relevant activity"
    technique_count = len(set(incident.mitre_techniques))
    return (
        f"SentinelXDR observed suspicious activity on host {host}. "
        f"The attack chain includes {phase_text}. "
        f"The incident currently has {alert_count} alerts, {technique_count} MITRE techniques, "
        f"and risk score {risk_score:.0f}. "
        f"Recommended actions: {', '.join(actions) if actions else 'continue monitoring'}."
    )


def build_timeline(
    incident: Incident,
    events: list[Event],
    results: list[DetectionResult],
    alerts: list[Alert],
) -> list[TimelineNode]:
    timeline: list[TimelineNode] = []
    for event in events:
        timeline.append(
            TimelineNode(
                timestamp=event.timestamp,
                type=TimelineNodeType.EVENT,
                title=event.title,
                description=event.description or event.event_type,
                severity=event.severity,
                reference_id=event.id,
                source=event.source.value,
            )
        )
    for result in results:
        timeline.append(
            TimelineNode(
                timestamp=result.created_at,
                type=TimelineNodeType.DETECTION,
                title=result.title,
                description=result.description,
                severity=result.severity,
                mitre_tactic=first_or_none(result.mitre_tactics),
                mitre_technique=first_or_none(result.mitre_techniques),
                reference_id=result.id,
                source="detection",
            )
        )
    for alert in alerts:
        timeline.append(
            TimelineNode(
                timestamp=alert.created_at,
                type=TimelineNodeType.ALERT,
                title=alert.title,
                description=alert.description,
                severity=alert.severity,
                mitre_tactic=first_or_none(alert.mitre_tactics),
                mitre_technique=first_or_none(alert.mitre_techniques),
                reference_id=alert.id,
                source="alert",
            )
        )
    timeline.append(
        TimelineNode(
            timestamp=incident.created_at,
            type=TimelineNodeType.INCIDENT,
            title=incident.title,
            description=incident.description,
            severity=incident.severity,
            mitre_tactic=first_or_none(incident.mitre_tactics),
            mitre_technique=first_or_none(incident.mitre_techniques),
            reference_id=incident.id,
            source="incident",
        )
    )
    timeline.sort(key=lambda node: node.timestamp)
    return timeline


def build_graph(
    incident: Incident,
    events: list[Event],
    results: list[DetectionResult],
    alerts: list[Alert],
    agents: list[Agent],
) -> AttackGraph:
    nodes: dict[str, AttackGraphNode] = {}
    edges: list[AttackGraphEdge] = []
    for agent_id in incident.agent_ids:
        agent = next((item for item in agents if item.id == agent_id), None)
        nodes[agent_id] = AttackGraphNode(
            id=agent_id,
            label=agent.hostname if agent else agent_id,
            type=GraphNodeType.AGENT,
        )
    for event in events:
        nodes[event.id] = AttackGraphNode(
            id=event.id,
            label=event.title,
            type=GraphNodeType.EVENT,
            severity=event.severity,
        )
        edges.append(
            AttackGraphEdge(source=event.agent_id, target=event.id, relationship="emitted")
        )
    for result in results:
        nodes[result.id] = AttackGraphNode(
            id=result.id,
            label=result.rule_name,
            type=GraphNodeType.DETECTION,
            severity=result.severity,
        )
        edges.append(
            AttackGraphEdge(source=result.event_id, target=result.id, relationship="matched")
        )
    for alert in alerts:
        nodes[alert.id] = AttackGraphNode(
            id=alert.id,
            label=alert.title,
            type=GraphNodeType.ALERT,
            severity=alert.severity,
        )
        edges.append(
            AttackGraphEdge(
                source=alert.detection_result_id,
                target=alert.id,
                relationship="raised",
            )
        )
    nodes[incident.id] = AttackGraphNode(
        id=incident.id,
        label=incident.title,
        type=GraphNodeType.INCIDENT,
        severity=incident.severity,
    )
    for alert_id in incident.alert_ids:
        edges.append(AttackGraphEdge(source=alert_id, target=incident.id, relationship="grouped"))
    for technique in incident.mitre_techniques:
        nodes[technique] = AttackGraphNode(
            id=technique,
            label=technique,
            type=GraphNodeType.TECHNIQUE,
        )
        edges.append(
            AttackGraphEdge(source=incident.id, target=technique, relationship="maps_to")
        )
    return AttackGraph(nodes=list(nodes.values()), edges=dedupe_edges(edges))


def dedupe(values: list[str]) -> list[str]:
    result: list[str] = []
    for value in values:
        if value not in result:
            result.append(value)
    return result


def dedupe_edges(edges: list[AttackGraphEdge]) -> list[AttackGraphEdge]:
    result: list[AttackGraphEdge] = []
    seen: set[tuple[str, str, str]] = set()
    for edge in edges:
        key = (edge.source, edge.target, edge.relationship)
        if key not in seen:
            seen.add(key)
            result.append(edge)
    return result


def first_or_none(values: list[str]) -> str | None:
    return values[0] if values else None
