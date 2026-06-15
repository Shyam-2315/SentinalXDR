"""Tests for GET /api/dashboard/* endpoints (Phase 8).

Uses the same fake-repository pattern as the rest of the test suite.
No real MongoDB or Redis connections are made.
"""

from collections.abc import Iterator
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from app.api.dependencies import (
    get_agent_repository,
    get_alert_repository,
    get_attack_chain_repository,
    get_dashboard_repository,
    get_event_repository,
    get_incident_repository,
    get_organization_repository,
    get_user_repository,
)
from app.core.config import get_settings
from app.core.security import create_token, hash_agent_api_key, hash_password
from app.main import app
from app.models.agent import Agent, AgentStatus, OSType
from app.models.alert import Alert, AlertStatus
from app.models.attack_chain import (
    AttackChain,
    AttackChainStatus,
)
from app.models.auth import Role, UserStatus
from app.models.event import Event, EventSeverity, EventSource
from app.models.incident import Incident, IncidentStatus
from app.models.organization import Organization
from app.models.user import User

# ---------------------------------------------------------------------------
# Shared in-memory store
# ---------------------------------------------------------------------------


class DashboardTestStore:
    def __init__(self) -> None:
        self.users: dict[str, User] = {}
        self.organizations: dict[str, Organization] = {}
        self.agents: dict[str, Agent] = {}
        self.events: dict[str, Event] = {}
        self.alerts: dict[str, Alert] = {}
        self.incidents: dict[str, Incident] = {}
        self.attack_chains: dict[str, AttackChain] = {}


# ---------------------------------------------------------------------------
# Fake repositories
# ---------------------------------------------------------------------------


class FakeOrganizationRepository:
    def __init__(self, store: DashboardTestStore) -> None:
        self.store = store

    async def find_by_id(self, organization_id: str) -> Organization | None:
        return self.store.organizations.get(organization_id)

    async def create(self, name: str) -> Organization:
        now = datetime.now(UTC)
        org = Organization(
            id=f"org_{uuid4().hex}",
            name=name,
            created_at=now,
            updated_at=now,
        )
        self.store.organizations[org.id] = org
        return org


class FakeUserRepository:
    def __init__(self, store: DashboardTestStore) -> None:
        self.store = store

    async def count(self) -> int:
        return len(self.store.users)

    async def create(
        self,
        *,
        email: str,
        display_name: str,
        organization_id: str,
        role: Role,
        hashed_password: str,
        status: UserStatus = UserStatus.ACTIVE,
    ) -> User:
        now = datetime.now(UTC)
        user = User(
            id=f"usr_{uuid4().hex}",
            organization_id=organization_id,
            email=email.lower(),
            display_name=display_name,
            role=role,
            status=status,
            hashed_password=hashed_password,
            created_at=now,
            updated_at=now,
        )
        self.store.users[user.id] = user
        return user

    async def find_by_email(self, email: str) -> User | None:
        normalized = email.lower()
        return next(
            (u for u in self.store.users.values() if u.email == normalized), None
        )

    async def find_by_id(self, user_id: str) -> User | None:
        return self.store.users.get(user_id)


class FakeAgentRepository:
    def __init__(self, store: DashboardTestStore) -> None:
        self.store = store

    async def list_by_organization(self, organization_id: str) -> list[Agent]:
        return [a for a in self.store.agents.values() if a.organization_id == organization_id]

    async def find_by_id_for_organization(
        self, *, agent_id: str, organization_id: str
    ) -> Agent | None:
        a = self.store.agents.get(agent_id)
        if a is None or a.organization_id != organization_id:
            return None
        return a

    async def find_by_api_key(self, api_key: str) -> Agent | None:
        return None

    async def find_many_by_ids_for_organization(
        self, *, agent_ids: list[str], organization_id: str
    ) -> list[Agent]:
        return [
            a
            for a in self.store.agents.values()
            if a.id in agent_ids and a.organization_id == organization_id
        ]


class FakeEventRepository:
    def __init__(self, store: DashboardTestStore) -> None:
        self.store = store

    async def list_by_organization(
        self,
        *,
        organization_id: str,
        severity: EventSeverity | None = None,
        source: EventSource | None = None,
        event_type: str | None = None,
        agent_id: str | None = None,
        limit: int = 100,
        skip: int = 0,
    ) -> list[Event]:
        evts = [
            e
            for e in self.store.events.values()
            if e.organization_id == organization_id
            and (severity is None or e.severity == severity)
            and (source is None or e.source == source)
            and (event_type is None or e.event_type == event_type)
            and (agent_id is None or e.agent_id == agent_id)
        ]
        evts.sort(key=lambda e: e.received_at, reverse=True)
        return evts[skip : skip + limit]

    async def find_by_id_for_organization(
        self, *, event_id: str, organization_id: str
    ) -> Event | None:
        e = self.store.events.get(event_id)
        if e is None or e.organization_id != organization_id:
            return None
        return e

    async def find_many_by_ids_for_organization(
        self, *, event_ids: list[str], organization_id: str
    ) -> list[Event]:
        return [
            e
            for e in self.store.events.values()
            if e.id in event_ids and e.organization_id == organization_id
        ]


class FakeAlertRepository:
    def __init__(self, store: DashboardTestStore) -> None:
        self.store = store

    async def list_by_organization(
        self,
        *,
        organization_id: str,
        limit: int = 100,
        skip: int = 0,
    ) -> list[Alert]:
        alerts = [
            a for a in self.store.alerts.values() if a.organization_id == organization_id
        ]
        alerts.sort(key=lambda a: a.created_at, reverse=True)
        return alerts[skip : skip + limit]

    async def find_by_id_for_organization(
        self, *, alert_id: str, organization_id: str
    ) -> Alert | None:
        a = self.store.alerts.get(alert_id)
        if a is None or a.organization_id != organization_id:
            return None
        return a

    async def find_many_by_ids_for_organization(
        self, *, alert_ids: list[str], organization_id: str
    ) -> list[Alert]:
        return [
            a
            for a in self.store.alerts.values()
            if a.id in alert_ids and a.organization_id == organization_id
        ]

    async def update_status(
        self, *, alert_id: str, organization_id: str, status: AlertStatus
    ) -> Alert | None:
        a = await self.find_by_id_for_organization(
            alert_id=alert_id, organization_id=organization_id
        )
        if a is None:
            return None
        updated = a.model_copy(update={"status": status, "updated_at": datetime.now(UTC)})
        self.store.alerts[a.id] = updated
        return updated


class FakeIncidentRepository:
    def __init__(self, store: DashboardTestStore) -> None:
        self.store = store

    async def list_by_organization(
        self,
        *,
        organization_id: str,
        status: IncidentStatus | None = None,
        severity: EventSeverity | None = None,
        agent_id: str | None = None,
        mitre_technique: str | None = None,
        limit: int = 100,
        skip: int = 0,
    ) -> list[Incident]:
        incs = [
            i
            for i in self.store.incidents.values()
            if i.organization_id == organization_id
            and (status is None or i.status == status)
            and (severity is None or i.severity == severity)
            and (agent_id is None or agent_id in i.agent_ids)
            and (mitre_technique is None or mitre_technique in i.mitre_techniques)
        ]
        incs.sort(key=lambda i: i.updated_at, reverse=True)
        return incs[skip : skip + limit]

    async def find_by_id_for_organization(
        self, *, incident_id: str, organization_id: str
    ) -> Incident | None:
        i = self.store.incidents.get(incident_id)
        if i is None or i.organization_id != organization_id:
            return None
        return i


class FakeAttackChainRepository:
    def __init__(self, store: DashboardTestStore) -> None:
        self.store = store

    async def list_by_organization(
        self,
        *,
        organization_id: str,
        status: AttackChainStatus | None = None,
        severity: EventSeverity | None = None,
        agent_id: str | None = None,
        mitre_technique: str | None = None,
        min_risk_score: float | None = None,
        limit: int = 100,
        skip: int = 0,
    ) -> list[AttackChain]:
        chains = [
            c
            for c in self.store.attack_chains.values()
            if c.organization_id == organization_id
            and (status is None or c.status == status)
            and (severity is None or c.severity == severity)
            and (agent_id is None or agent_id in c.agent_ids)
            and (mitre_technique is None or mitre_technique in c.mitre_techniques)
            and (min_risk_score is None or c.risk_score >= min_risk_score)
        ]
        chains.sort(key=lambda c: c.updated_at, reverse=True)
        return chains[skip : skip + limit]

    async def find_by_id_for_organization(
        self, *, chain_id: str, organization_id: str
    ) -> AttackChain | None:
        c = self.store.attack_chains.get(chain_id)
        if c is None or c.organization_id != organization_id:
            return None
        return c

    async def find_by_incident_for_organization(
        self, *, incident_id: str, organization_id: str
    ) -> AttackChain | None:
        return next(
            (
                c
                for c in self.store.attack_chains.values()
                if c.incident_id == incident_id and c.organization_id == organization_id
            ),
            None,
        )


class FakeDashboardRepository:
    """In-memory implementation of DashboardRepository for tests."""

    def __init__(self, store: DashboardTestStore) -> None:
        self.store = store

    # --- agents ---

    async def count_agents_by_status(self, organization_id: str) -> dict[str, int]:
        result: dict[str, int] = {
            AgentStatus.ONLINE.value: 0,
            AgentStatus.OFFLINE.value: 0,
            AgentStatus.DISABLED.value: 0,
        }
        for a in self.store.agents.values():
            if a.organization_id == organization_id:
                result[a.status.value] += 1
        result["total"] = sum(result.values())
        return result

    async def count_stale_agents(self, organization_id: str) -> int:
        threshold = datetime.now(UTC) - timedelta(minutes=5)
        return sum(
            1
            for a in self.store.agents.values()
            if a.organization_id == organization_id
            and a.status == AgentStatus.ONLINE
            and (a.last_seen_at is None or a.last_seen_at < threshold)
        )

    async def count_recently_active_agents(self, organization_id: str) -> int:
        threshold = datetime.now(UTC) - timedelta(minutes=5)
        return sum(
            1
            for a in self.store.agents.values()
            if a.organization_id == organization_id
            and a.status == AgentStatus.ONLINE
            and a.last_seen_at is not None
            and a.last_seen_at >= threshold
        )

    # --- events ---

    async def count_events(self, organization_id: str) -> int:
        return sum(
            1
            for e in self.store.events.values()
            if e.organization_id == organization_id
        )

    # --- alerts ---

    async def count_alerts(self, organization_id: str) -> int:
        return sum(
            1
            for a in self.store.alerts.values()
            if a.organization_id == organization_id
        )

    async def count_open_alerts(self, organization_id: str) -> int:
        return sum(
            1
            for a in self.store.alerts.values()
            if a.organization_id == organization_id and a.status == AlertStatus.OPEN
        )

    async def count_alerts_by_severity(self, organization_id: str) -> dict[str, int]:
        result: dict[str, int] = {}
        for a in self.store.alerts.values():
            if a.organization_id == organization_id:
                key = a.severity.value
                result[key] = result.get(key, 0) + 1
        return result

    async def average_attack_chain_risk_score(self, organization_id: str) -> float:
        scores = [
            c.risk_score
            for c in self.store.attack_chains.values()
            if c.organization_id == organization_id
        ]
        if not scores:
            return 0.0
        return round(sum(scores) / len(scores), 2)

    # --- incidents ---

    async def count_incidents(self, organization_id: str) -> int:
        return sum(
            1
            for i in self.store.incidents.values()
            if i.organization_id == organization_id
        )

    async def count_open_incidents(self, organization_id: str) -> int:
        open_statuses = {IncidentStatus.OPEN, IncidentStatus.INVESTIGATING}
        return sum(
            1
            for i in self.store.incidents.values()
            if i.organization_id == organization_id and i.status in open_statuses
        )

    # --- attack chains ---

    async def count_attack_chains(self, organization_id: str) -> int:
        return sum(
            1
            for c in self.store.attack_chains.values()
            if c.organization_id == organization_id
        )

    async def count_active_attack_chains(self, organization_id: str) -> int:
        return sum(
            1
            for c in self.store.attack_chains.values()
            if c.organization_id == organization_id
            and c.status == AttackChainStatus.ACTIVE
        )

    # --- MITRE ---

    async def mitre_tactic_technique_counts(
        self, organization_id: str
    ) -> list[dict[str, Any]]:
        counts: dict[tuple[str, str, str], int] = {}
        for a in self.store.alerts.values():
            if a.organization_id != organization_id:
                continue
            tactics = a.mitre_tactics or []
            techniques = a.mitre_techniques or [""]
            for tactic in tactics:
                for technique in techniques:
                    key = (tactic, technique, a.severity.value)
                    counts[key] = counts.get(key, 0) + 1
        return [
            {"tactic": tactic, "technique": tech, "severity": sev, "count": cnt}
            for (tactic, tech, sev), cnt in sorted(counts.items(), key=lambda x: -x[1])
        ]

    # --- severity trends ---

    async def alert_severity_by_day(
        self, organization_id: str, days: int = 7
    ) -> list[dict[str, Any]]:
        since = datetime.now(UTC) - timedelta(days=days)
        counts: dict[tuple[str, str], int] = {}
        for a in self.store.alerts.values():
            if a.organization_id != organization_id:
                continue
            if a.created_at < since:
                continue
            day = a.created_at.strftime("%Y-%m-%d")
            key = (day, a.severity.value)
            counts[key] = counts.get(key, 0) + 1
        return [
            {"date": day, "severity": sev, "count": cnt}
            for (day, sev), cnt in sorted(counts.items())
        ]


# ---------------------------------------------------------------------------
# Pytest fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def clear_settings_cache() -> Iterator[None]:
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


@pytest.fixture
def store() -> DashboardTestStore:
    return DashboardTestStore()


@pytest.fixture
def client(store: DashboardTestStore) -> Iterator[TestClient]:
    app.dependency_overrides[get_user_repository] = lambda: FakeUserRepository(store)
    app.dependency_overrides[get_organization_repository] = (
        lambda: FakeOrganizationRepository(store)
    )
    app.dependency_overrides[get_agent_repository] = lambda: FakeAgentRepository(store)
    app.dependency_overrides[get_event_repository] = lambda: FakeEventRepository(store)
    app.dependency_overrides[get_alert_repository] = lambda: FakeAlertRepository(store)
    app.dependency_overrides[get_incident_repository] = (
        lambda: FakeIncidentRepository(store)
    )
    app.dependency_overrides[get_attack_chain_repository] = (
        lambda: FakeAttackChainRepository(store)
    )
    app.dependency_overrides[get_dashboard_repository] = (
        lambda: FakeDashboardRepository(store)
    )
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# Helper builders
# ---------------------------------------------------------------------------


def _org(store: DashboardTestStore, *, name: str = "Acme") -> Organization:
    now = datetime.now(UTC)
    org = Organization(
        id=f"org_{uuid4().hex}",
        name=name,
        created_at=now,
        updated_at=now,
    )
    store.organizations[org.id] = org
    return org


def _user(
    store: DashboardTestStore,
    *,
    organization_id: str,
    role: Role = Role.ORG_ADMIN,
    email: str | None = None,
) -> tuple[User, str]:
    email = email or f"user-{uuid4().hex[:6]}@example.com"
    now = datetime.now(UTC)
    user = User(
        id=f"usr_{uuid4().hex}",
        organization_id=organization_id,
        email=email,
        display_name=email.split("@")[0],
        role=role,
        status=UserStatus.ACTIVE,
        hashed_password=hash_password("password123"),
        created_at=now,
        updated_at=now,
    )
    store.users[user.id] = user
    return user, create_token(user, "access")


def _agent(
    store: DashboardTestStore,
    *,
    organization_id: str,
    status: AgentStatus = AgentStatus.ONLINE,
    last_seen_at: datetime | None = None,
) -> Agent:
    now = datetime.now(UTC)
    agent = Agent(
        id=f"agt_{uuid4().hex}",
        organization_id=organization_id,
        name=f"agent-{uuid4().hex[:4]}",
        hostname=f"host-{uuid4().hex[:4]}.local",
        os_type=OSType.LINUX,
        agent_version="1.0.0",
        status=status,
        api_key_hash=hash_agent_api_key(f"sxag_test_{uuid4().hex}"),
        last_seen_at=last_seen_at or now,
        created_at=now,
        updated_at=now,
    )
    store.agents[agent.id] = agent
    return agent


def _event(store: DashboardTestStore, *, organization_id: str, agent_id: str) -> Event:
    now = datetime.now(UTC)
    event = Event(
        id=f"evt_{uuid4().hex}",
        organization_id=organization_id,
        agent_id=agent_id,
        event_type="process_start",
        severity=EventSeverity.INFO,
        source=EventSource.LINUX,
        title="Test event",
        raw_event={"pid": 1},
        timestamp=now,
        received_at=now,
    )
    store.events[event.id] = event
    return event


def _alert(
    store: DashboardTestStore,
    *,
    organization_id: str,
    agent_id: str,
    severity: EventSeverity = EventSeverity.MEDIUM,
    status: AlertStatus = AlertStatus.OPEN,
    mitre_tactics: list[str] | None = None,
    mitre_techniques: list[str] | None = None,
    created_at: datetime | None = None,
) -> Alert:
    now = created_at or datetime.now(UTC)
    alert = Alert(
        id=f"alr_{uuid4().hex}",
        organization_id=organization_id,
        agent_id=agent_id,
        event_id=f"evt_{uuid4().hex}",
        detection_result_id=f"det_{uuid4().hex}",
        title="Test alert",
        description="Test alert description",
        severity=severity,
        status=status,
        mitre_tactics=mitre_tactics or [],
        mitre_techniques=mitre_techniques or [],
        created_at=now,
        updated_at=now,
    )
    store.alerts[alert.id] = alert
    return alert


def _incident(
    store: DashboardTestStore,
    *,
    organization_id: str,
    status: IncidentStatus = IncidentStatus.OPEN,
) -> Incident:
    now = datetime.now(UTC)
    incident = Incident(
        id=f"inc_{uuid4().hex}",
        organization_id=organization_id,
        title="Test incident",
        description="Test incident description",
        severity=EventSeverity.HIGH,
        status=status,
        first_seen_at=now,
        last_seen_at=now,
        created_at=now,
        updated_at=now,
    )
    store.incidents[incident.id] = incident
    return incident


def _attack_chain(
    store: DashboardTestStore,
    *,
    organization_id: str,
    incident_id: str,
    status: AttackChainStatus = AttackChainStatus.ACTIVE,
    risk_score: float = 75.0,
) -> AttackChain:
    now = datetime.now(UTC)
    chain = AttackChain(
        id=f"atc_{uuid4().hex}",
        organization_id=organization_id,
        incident_id=incident_id,
        title="Test chain",
        summary="Test summary",
        severity=EventSeverity.HIGH,
        risk_score=risk_score,
        confidence_score=0.9,
        story="Test story",
        status=status,
        first_seen_at=now,
        last_seen_at=now,
        created_at=now,
        updated_at=now,
    )
    store.attack_chains[chain.id] = chain
    return chain


# ---------------------------------------------------------------------------
# Tests — dashboard summary
# ---------------------------------------------------------------------------


def test_summary_returns_correct_counts(
    client: TestClient, store: DashboardTestStore
) -> None:
    org = _org(store)
    _, token = _user(store, organization_id=org.id)
    agent = _agent(store, organization_id=org.id, status=AgentStatus.ONLINE)
    _agent(store, organization_id=org.id, status=AgentStatus.OFFLINE)
    _agent(store, organization_id=org.id, status=AgentStatus.DISABLED)
    _event(store, organization_id=org.id, agent_id=agent.id)
    _event(store, organization_id=org.id, agent_id=agent.id)
    _alert(store, organization_id=org.id, agent_id=agent.id, severity=EventSeverity.CRITICAL)
    _alert(
        store,
        organization_id=org.id,
        agent_id=agent.id,
        severity=EventSeverity.HIGH,
        status=AlertStatus.RESOLVED,
    )
    inc = _incident(store, organization_id=org.id)
    _incident(store, organization_id=org.id, status=IncidentStatus.RESOLVED)
    _attack_chain(
        store, organization_id=org.id, incident_id=inc.id, status=AttackChainStatus.ACTIVE
    )
    _attack_chain(
        store,
        organization_id=org.id,
        incident_id=f"inc_{uuid4().hex}",
        status=AttackChainStatus.RESOLVED,
    )

    resp = client.get("/api/dashboard/summary", headers={"Authorization": f"Bearer {token}"})

    assert resp.status_code == 200
    data = resp.json()
    assert data["total_agents"] == 3
    assert data["online_agents"] == 1
    assert data["offline_agents"] == 1
    assert data["disabled_agents"] == 1
    assert data["total_events"] == 2
    assert data["total_alerts"] == 2
    assert data["open_alerts"] == 1
    assert data["total_incidents"] == 2
    assert data["open_incidents"] == 1
    assert data["total_attack_chains"] == 2
    assert data["active_attack_chains"] == 1
    assert data["critical_alerts"] == 1
    assert data["high_alerts"] == 1


def test_summary_is_organization_scoped(
    client: TestClient, store: DashboardTestStore
) -> None:
    org_a = _org(store, name="Org A")
    org_b = _org(store, name="Org B")
    _, token_a = _user(store, organization_id=org_a.id)
    agent_a = _agent(store, organization_id=org_a.id)
    agent_b = _agent(store, organization_id=org_b.id)
    # Org A has 2 alerts; Org B has 5
    for _ in range(2):
        _alert(store, organization_id=org_a.id, agent_id=agent_a.id)
    for _ in range(5):
        _alert(store, organization_id=org_b.id, agent_id=agent_b.id)

    resp = client.get(
        "/api/dashboard/summary", headers={"Authorization": f"Bearer {token_a}"}
    )

    assert resp.status_code == 200
    data = resp.json()
    assert data["total_alerts"] == 2  # Only Org A's alerts


def test_summary_empty_org_returns_zeros(
    client: TestClient, store: DashboardTestStore
) -> None:
    org = _org(store)
    _, token = _user(store, organization_id=org.id)

    resp = client.get("/api/dashboard/summary", headers={"Authorization": f"Bearer {token}"})

    assert resp.status_code == 200
    data = resp.json()
    assert data["total_agents"] == 0
    assert data["total_alerts"] == 0
    assert data["risk_score_average"] == 0.0


# ---------------------------------------------------------------------------
# Tests — security posture
# ---------------------------------------------------------------------------


def test_security_posture_perfect_when_no_alerts(
    client: TestClient, store: DashboardTestStore
) -> None:
    org = _org(store)
    _, token = _user(store, organization_id=org.id)
    _agent(store, organization_id=org.id, status=AgentStatus.ONLINE)

    resp = client.get(
        "/api/dashboard/security-posture", headers={"Authorization": f"Bearer {token}"}
    )

    assert resp.status_code == 200
    data = resp.json()
    assert data["posture_score"] == 100
    assert data["posture_label"] == "excellent"


def test_security_posture_degrades_with_critical_alerts(
    client: TestClient, store: DashboardTestStore
) -> None:
    org = _org(store)
    _, token = _user(store, organization_id=org.id)
    agent = _agent(store, organization_id=org.id)
    for _ in range(3):
        _alert(
            store,
            organization_id=org.id,
            agent_id=agent.id,
            severity=EventSeverity.CRITICAL,
        )

    resp = client.get(
        "/api/dashboard/security-posture", headers={"Authorization": f"Bearer {token}"}
    )

    assert resp.status_code == 200
    data = resp.json()
    assert data["posture_score"] < 100
    assert data["posture_label"] in ("risky", "critical", "moderate")


def test_security_posture_has_required_fields(
    client: TestClient, store: DashboardTestStore
) -> None:
    org = _org(store)
    _, token = _user(store, organization_id=org.id)

    resp = client.get(
        "/api/dashboard/security-posture", headers={"Authorization": f"Bearer {token}"}
    )

    assert resp.status_code == 200
    data = resp.json()
    assert "posture_score" in data
    assert "posture_label" in data
    assert "top_risks" in data
    assert "recommended_actions" in data
    assert 0 <= data["posture_score"] <= 100


# ---------------------------------------------------------------------------
# Tests — recent alerts
# ---------------------------------------------------------------------------


def test_recent_alerts_returns_latest_items(
    client: TestClient, store: DashboardTestStore
) -> None:
    org = _org(store)
    _, token = _user(store, organization_id=org.id)
    agent = _agent(store, organization_id=org.id)
    now = datetime.now(UTC)
    for i in range(5):
        _alert(
            store,
            organization_id=org.id,
            agent_id=agent.id,
            created_at=now - timedelta(minutes=i),
        )

    resp = client.get(
        "/api/dashboard/recent-alerts?limit=3",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert resp.status_code == 200
    data = resp.json()
    assert data["count"] == 3
    assert len(data["alerts"]) == 3


def test_recent_alerts_default_limit(
    client: TestClient, store: DashboardTestStore
) -> None:
    org = _org(store)
    _, token = _user(store, organization_id=org.id)
    agent = _agent(store, organization_id=org.id)
    for _ in range(15):
        _alert(store, organization_id=org.id, agent_id=agent.id)

    resp = client.get(
        "/api/dashboard/recent-alerts", headers={"Authorization": f"Bearer {token}"}
    )

    assert resp.status_code == 200
    assert resp.json()["count"] == 10  # default limit


def test_recent_alerts_org_scoped(
    client: TestClient, store: DashboardTestStore
) -> None:
    org_a = _org(store, name="A")
    org_b = _org(store, name="B")
    _, token_a = _user(store, organization_id=org_a.id)
    agent_a = _agent(store, organization_id=org_a.id)
    agent_b = _agent(store, organization_id=org_b.id)
    _alert(store, organization_id=org_a.id, agent_id=agent_a.id)
    for _ in range(4):
        _alert(store, organization_id=org_b.id, agent_id=agent_b.id)

    resp = client.get(
        "/api/dashboard/recent-alerts", headers={"Authorization": f"Bearer {token_a}"}
    )

    assert resp.status_code == 200
    assert resp.json()["count"] == 1


# ---------------------------------------------------------------------------
# Tests — recent incidents
# ---------------------------------------------------------------------------


def test_recent_incidents_returns_latest_items(
    client: TestClient, store: DashboardTestStore
) -> None:
    org = _org(store)
    _, token = _user(store, organization_id=org.id)
    for _ in range(5):
        _incident(store, organization_id=org.id)

    resp = client.get(
        "/api/dashboard/recent-incidents?limit=3",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert resp.status_code == 200
    data = resp.json()
    assert data["count"] == 3
    assert len(data["incidents"]) == 3


def test_recent_incidents_default_limit(
    client: TestClient, store: DashboardTestStore
) -> None:
    org = _org(store)
    _, token = _user(store, organization_id=org.id)
    for _ in range(15):
        _incident(store, organization_id=org.id)

    resp = client.get(
        "/api/dashboard/recent-incidents", headers={"Authorization": f"Bearer {token}"}
    )

    assert resp.status_code == 200
    assert resp.json()["count"] == 10


# ---------------------------------------------------------------------------
# Tests — recent attack chains
# ---------------------------------------------------------------------------


def test_recent_attack_chains_returns_latest_items(
    client: TestClient, store: DashboardTestStore
) -> None:
    org = _org(store)
    _, token = _user(store, organization_id=org.id)
    for _ in range(5):
        inc = _incident(store, organization_id=org.id)
        _attack_chain(store, organization_id=org.id, incident_id=inc.id)

    resp = client.get(
        "/api/dashboard/recent-attack-chains?limit=3",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert resp.status_code == 200
    data = resp.json()
    assert data["count"] == 3
    assert len(data["attack_chains"]) == 3


def test_recent_attack_chains_default_limit(
    client: TestClient, store: DashboardTestStore
) -> None:
    org = _org(store)
    _, token = _user(store, organization_id=org.id)
    for _ in range(15):
        inc = _incident(store, organization_id=org.id)
        _attack_chain(store, organization_id=org.id, incident_id=inc.id)

    resp = client.get(
        "/api/dashboard/recent-attack-chains", headers={"Authorization": f"Bearer {token}"}
    )

    assert resp.status_code == 200
    assert resp.json()["count"] == 10


# ---------------------------------------------------------------------------
# Tests — MITRE summary
# ---------------------------------------------------------------------------


def test_mitre_summary_groups_tactics_and_techniques(
    client: TestClient, store: DashboardTestStore
) -> None:
    org = _org(store)
    _, token = _user(store, organization_id=org.id)
    agent = _agent(store, organization_id=org.id)
    _alert(
        store,
        organization_id=org.id,
        agent_id=agent.id,
        severity=EventSeverity.HIGH,
        mitre_tactics=["Execution"],
        mitre_techniques=["T1059"],
    )
    _alert(
        store,
        organization_id=org.id,
        agent_id=agent.id,
        severity=EventSeverity.CRITICAL,
        mitre_tactics=["Execution"],
        mitre_techniques=["T1059"],
    )
    _alert(
        store,
        organization_id=org.id,
        agent_id=agent.id,
        severity=EventSeverity.MEDIUM,
        mitre_tactics=["Persistence"],
        mitre_techniques=["T1053"],
    )

    resp = client.get(
        "/api/dashboard/mitre-summary", headers={"Authorization": f"Bearer {token}"}
    )

    assert resp.status_code == 200
    data = resp.json()
    tactic_names = [t["tactic"] for t in data["tactics"]]
    assert "Execution" in tactic_names
    assert "Persistence" in tactic_names

    exec_group = next(t for t in data["tactics"] if t["tactic"] == "Execution")
    assert exec_group["total"] >= 2


def test_mitre_summary_empty_returns_empty_tactics(
    client: TestClient, store: DashboardTestStore
) -> None:
    org = _org(store)
    _, token = _user(store, organization_id=org.id)

    resp = client.get(
        "/api/dashboard/mitre-summary", headers={"Authorization": f"Bearer {token}"}
    )

    assert resp.status_code == 200
    assert resp.json()["tactics"] == []


def test_mitre_summary_org_scoped(
    client: TestClient, store: DashboardTestStore
) -> None:
    org_a = _org(store, name="A")
    org_b = _org(store, name="B")
    _, token_a = _user(store, organization_id=org_a.id)
    agent_a = _agent(store, organization_id=org_a.id)
    agent_b = _agent(store, organization_id=org_b.id)
    _alert(
        store,
        organization_id=org_a.id,
        agent_id=agent_a.id,
        mitre_tactics=["Execution"],
        mitre_techniques=["T1059"],
    )
    _alert(
        store,
        organization_id=org_b.id,
        agent_id=agent_b.id,
        mitre_tactics=["Persistence"],
        mitre_techniques=["T1053"],
    )

    resp = client.get(
        "/api/dashboard/mitre-summary", headers={"Authorization": f"Bearer {token_a}"}
    )

    assert resp.status_code == 200
    tactic_names = [t["tactic"] for t in resp.json()["tactics"]]
    assert "Execution" in tactic_names
    assert "Persistence" not in tactic_names


# ---------------------------------------------------------------------------
# Tests — severity trends
# ---------------------------------------------------------------------------


def test_severity_trends_returns_7_days(
    client: TestClient, store: DashboardTestStore
) -> None:
    org = _org(store)
    _, token = _user(store, organization_id=org.id)

    resp = client.get(
        "/api/dashboard/severity-trends", headers={"Authorization": f"Bearer {token}"}
    )

    assert resp.status_code == 200
    data = resp.json()
    assert len(data["days"]) == 7


def test_severity_trends_counts_correctly(
    client: TestClient, store: DashboardTestStore
) -> None:
    org = _org(store)
    _, token = _user(store, organization_id=org.id)
    agent = _agent(store, organization_id=org.id)
    today = datetime.now(UTC)
    _alert(
        store,
        organization_id=org.id,
        agent_id=agent.id,
        severity=EventSeverity.CRITICAL,
        created_at=today,
    )
    _alert(
        store,
        organization_id=org.id,
        agent_id=agent.id,
        severity=EventSeverity.HIGH,
        created_at=today,
    )

    resp = client.get(
        "/api/dashboard/severity-trends", headers={"Authorization": f"Bearer {token}"}
    )

    assert resp.status_code == 200
    days = resp.json()["days"]
    today_str = today.strftime("%Y-%m-%d")
    today_bucket = next(d for d in days if d["date"] == today_str)
    assert today_bucket["critical"] == 1
    assert today_bucket["high"] == 1
    assert today_bucket["medium"] == 0


def test_severity_trends_all_severities_present(
    client: TestClient, store: DashboardTestStore
) -> None:
    org = _org(store)
    _, token = _user(store, organization_id=org.id)

    resp = client.get(
        "/api/dashboard/severity-trends", headers={"Authorization": f"Bearer {token}"}
    )

    assert resp.status_code == 200
    days = resp.json()["days"]
    severity_keys = {"info", "low", "medium", "high", "critical"}
    assert all(severity_keys <= d.keys() for d in days)


# ---------------------------------------------------------------------------
# Tests — agent health
# ---------------------------------------------------------------------------


def test_agent_health_returns_all_status_groups(
    client: TestClient, store: DashboardTestStore
) -> None:
    org = _org(store)
    _, token = _user(store, organization_id=org.id)
    recently = datetime.now(UTC) - timedelta(minutes=1)
    stale_time = datetime.now(UTC) - timedelta(minutes=10)
    _agent(
        store, organization_id=org.id, status=AgentStatus.ONLINE, last_seen_at=recently
    )
    _agent(
        store, organization_id=org.id, status=AgentStatus.ONLINE, last_seen_at=stale_time
    )
    _agent(store, organization_id=org.id, status=AgentStatus.OFFLINE)
    _agent(store, organization_id=org.id, status=AgentStatus.DISABLED)

    resp = client.get(
        "/api/dashboard/agent-health", headers={"Authorization": f"Bearer {token}"}
    )

    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 4
    assert data["disabled_count"] == 1
    assert data["recently_active_count"] == 1
    assert data["stale_count"] == 1
    statuses = {g["status"] for g in data["by_status"]}
    assert AgentStatus.ONLINE.value in statuses
    assert AgentStatus.OFFLINE.value in statuses
    assert AgentStatus.DISABLED.value in statuses


def test_agent_health_org_scoped(
    client: TestClient, store: DashboardTestStore
) -> None:
    org_a = _org(store, name="A")
    org_b = _org(store, name="B")
    _, token_a = _user(store, organization_id=org_a.id)
    _agent(store, organization_id=org_a.id)
    for _ in range(3):
        _agent(store, organization_id=org_b.id)

    resp = client.get(
        "/api/dashboard/agent-health", headers={"Authorization": f"Bearer {token_a}"}
    )

    assert resp.status_code == 200
    assert resp.json()["total"] == 1


# ---------------------------------------------------------------------------
# Tests — RBAC
# ---------------------------------------------------------------------------


def test_viewer_can_access_all_dashboard_endpoints(
    client: TestClient, store: DashboardTestStore
) -> None:
    org = _org(store)
    _, token = _user(store, organization_id=org.id, role=Role.VIEWER)

    endpoints = [
        "/api/dashboard/summary",
        "/api/dashboard/security-posture",
        "/api/dashboard/recent-alerts",
        "/api/dashboard/recent-incidents",
        "/api/dashboard/recent-attack-chains",
        "/api/dashboard/mitre-summary",
        "/api/dashboard/severity-trends",
        "/api/dashboard/agent-health",
    ]
    for endpoint in endpoints:
        resp = client.get(endpoint, headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 200, f"{endpoint} returned {resp.status_code}"


def test_analyst_can_access_dashboard(
    client: TestClient, store: DashboardTestStore
) -> None:
    org = _org(store)
    _, token = _user(store, organization_id=org.id, role=Role.ANALYST)

    resp = client.get(
        "/api/dashboard/summary", headers={"Authorization": f"Bearer {token}"}
    )
    assert resp.status_code == 200


def test_unauthenticated_request_rejected(
    client: TestClient, store: DashboardTestStore
) -> None:
    endpoints = [
        "/api/dashboard/summary",
        "/api/dashboard/security-posture",
        "/api/dashboard/recent-alerts",
        "/api/dashboard/recent-incidents",
        "/api/dashboard/recent-attack-chains",
        "/api/dashboard/mitre-summary",
        "/api/dashboard/severity-trends",
        "/api/dashboard/agent-health",
    ]
    for endpoint in endpoints:
        resp = client.get(endpoint)
        assert resp.status_code == 401, f"{endpoint} should be 401 but got {resp.status_code}"


@pytest.mark.parametrize("prefix", ["/api", "/api/v1"])
def test_dashboard_summary_requires_auth_at_supported_api_prefixes(
    client: TestClient, prefix: str
) -> None:
    resp = client.get(f"{prefix}/dashboard/summary")

    assert resp.status_code == 401


def test_cross_org_data_not_leaked(
    client: TestClient, store: DashboardTestStore
) -> None:
    """User from Org B cannot see Org A's data."""
    org_a = _org(store, name="Org A")
    org_b = _org(store, name="Org B")
    _, token_b = _user(store, organization_id=org_b.id)
    agent_a = _agent(store, organization_id=org_a.id)
    for _ in range(10):
        _alert(store, organization_id=org_a.id, agent_id=agent_a.id)

    resp = client.get(
        "/api/dashboard/summary", headers={"Authorization": f"Bearer {token_b}"}
    )

    assert resp.status_code == 200
    data = resp.json()
    assert data["total_alerts"] == 0  # Org B has no alerts
