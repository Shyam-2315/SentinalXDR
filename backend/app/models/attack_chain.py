from datetime import UTC, datetime
from enum import StrEnum

from pydantic import BaseModel, Field

from app.models.event import EventSeverity


class AttackChainStatus(StrEnum):
    ACTIVE = "active"
    CONTAINED = "contained"
    RESOLVED = "resolved"


class TimelineNodeType(StrEnum):
    EVENT = "event"
    DETECTION = "detection"
    ALERT = "alert"
    INCIDENT = "incident"
    ACTION = "action"


class GraphNodeType(StrEnum):
    AGENT = "agent"
    EVENT = "event"
    DETECTION = "detection"
    ALERT = "alert"
    INCIDENT = "incident"
    TECHNIQUE = "technique"


class TimelineNode(BaseModel):
    timestamp: datetime
    type: TimelineNodeType
    title: str
    description: str
    severity: EventSeverity
    mitre_tactic: str | None = None
    mitre_technique: str | None = None
    reference_id: str
    source: str


class AttackGraphNode(BaseModel):
    id: str
    label: str
    type: GraphNodeType
    severity: EventSeverity | None = None


class AttackGraphEdge(BaseModel):
    source: str
    target: str
    relationship: str


class AttackGraph(BaseModel):
    nodes: list[AttackGraphNode] = Field(default_factory=list)
    edges: list[AttackGraphEdge] = Field(default_factory=list)


class AttackChain(BaseModel):
    id: str
    organization_id: str
    incident_id: str
    agent_ids: list[str] = Field(default_factory=list)
    alert_ids: list[str] = Field(default_factory=list)
    detection_result_ids: list[str] = Field(default_factory=list)
    event_ids: list[str] = Field(default_factory=list)
    title: str
    summary: str
    severity: EventSeverity
    risk_score: float
    confidence_score: float
    kill_chain_phases: list[str] = Field(default_factory=list)
    mitre_tactics: list[str] = Field(default_factory=list)
    mitre_techniques: list[str] = Field(default_factory=list)
    timeline: list[TimelineNode] = Field(default_factory=list)
    graph: AttackGraph = Field(default_factory=AttackGraph)
    story: str
    recommended_actions: list[str] = Field(default_factory=list)
    status: AttackChainStatus = AttackChainStatus.ACTIVE
    first_seen_at: datetime
    last_seen_at: datetime
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
