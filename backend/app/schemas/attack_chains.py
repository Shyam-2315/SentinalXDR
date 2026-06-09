from datetime import datetime

from pydantic import BaseModel

from app.models.attack_chain import (
    AttackChainStatus,
    AttackGraph,
    TimelineNode,
)
from app.models.event import EventSeverity


class AttackChainRead(BaseModel):
    id: str
    organization_id: str
    incident_id: str
    agent_ids: list[str]
    alert_ids: list[str]
    detection_result_ids: list[str]
    event_ids: list[str]
    title: str
    summary: str
    severity: EventSeverity
    risk_score: float
    confidence_score: float
    kill_chain_phases: list[str]
    mitre_tactics: list[str]
    mitre_techniques: list[str]
    timeline: list[TimelineNode]
    graph: AttackGraph
    story: str
    recommended_actions: list[str]
    status: AttackChainStatus
    first_seen_at: datetime
    last_seen_at: datetime
    created_at: datetime
    updated_at: datetime


class AttackChainListResponse(BaseModel):
    attack_chains: list[AttackChainRead]
    count: int
    limit: int
    skip: int


class AttackChainStatusUpdate(BaseModel):
    status: AttackChainStatus
