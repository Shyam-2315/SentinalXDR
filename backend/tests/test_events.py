from collections.abc import Iterator
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from app.api.dependencies import (
    get_agent_repository,
    get_alert_repository,
    get_detection_result_repository,
    get_detection_rule_repository,
    get_event_repository,
    get_incident_repository,
    get_organization_repository,
    get_user_repository,
)
from app.core.config import get_settings
from app.core.security import (
    create_token,
    hash_agent_api_key,
    hash_password,
    verify_agent_api_key,
)
from app.main import app
from app.models.agent import Agent, AgentStatus, OSType
from app.models.alert import Alert, AlertStatus
from app.models.auth import Role, UserStatus
from app.models.detection import DetectionResult, DetectionRule
from app.models.event import Event, EventSeverity, EventSource
from app.models.incident import Incident, IncidentStatus
from app.models.organization import Organization
from app.models.user import User
from app.repositories.detections import builtin_detection_rules
from app.repositories.incidents import append_unique, max_severity, merge_unique
from app.schemas.events import EventIngestItem


class EventTestStore:
    def __init__(self) -> None:
        self.users: dict[str, User] = {}
        self.organizations: dict[str, Organization] = {}
        self.agents: dict[str, Agent] = {}
        self.events: dict[str, Event] = {}
        self.rules: dict[str, DetectionRule] = {}
        self.results: dict[str, DetectionResult] = {}
        self.alerts: dict[str, Alert] = {}
        self.incidents: dict[str, Incident] = {}


class FakeOrganizationRepository:
    def __init__(self, store: EventTestStore) -> None:
        self.store = store

    async def create(self, name: str) -> Organization:
        organization = create_organization(self.store, name=name)
        return organization

    async def find_by_id(self, organization_id: str) -> Organization | None:
        return self.store.organizations.get(organization_id)


class FakeUserRepository:
    def __init__(self, store: EventTestStore) -> None:
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
        normalized_email = email.lower()
        return next(
            (user for user in self.store.users.values() if user.email == normalized_email),
            None,
        )

    async def find_by_id(self, user_id: str) -> User | None:
        return self.store.users.get(user_id)


class FakeAgentRepository:
    def __init__(self, store: EventTestStore) -> None:
        self.store = store

    async def create(
        self,
        *,
        organization_id: str,
        name: str,
        hostname: str,
        os_type: OSType,
        agent_version: str | None,
        api_key_hash: str,
        ip_address: str | None = None,
        tags: list[str] | None = None,
    ) -> Agent:
        agent = create_agent(
            self.store,
            organization_id=organization_id,
            api_key_hash=api_key_hash,
            name=name,
            hostname=hostname,
            os_type=os_type,
            agent_version=agent_version,
            ip_address=ip_address,
            tags=tags,
        )
        return agent

    async def list_by_organization(self, organization_id: str) -> list[Agent]:
        return [
            agent
            for agent in self.store.agents.values()
            if agent.organization_id == organization_id
        ]

    async def find_by_id_for_organization(
        self,
        *,
        agent_id: str,
        organization_id: str,
    ) -> Agent | None:
        agent = self.store.agents.get(agent_id)
        if agent is None or agent.organization_id != organization_id:
            return None
        return agent

    async def find_by_api_key(self, api_key: str) -> Agent | None:
        return next(
            (
                agent
                for agent in self.store.agents.values()
                if verify_agent_api_key(api_key, agent.api_key_hash)
            ),
            None,
        )

    async def update_heartbeat(
        self,
        *,
        agent_id: str,
        ip_address: str | None,
        agent_version: str | None,
    ) -> Agent | None:
        agent = self.store.agents.get(agent_id)
        if agent is None:
            return None
        updated = agent.model_copy(
            update={
                "status": AgentStatus.ONLINE,
                "last_seen_at": datetime.now(UTC),
                "ip_address": ip_address or agent.ip_address,
                "agent_version": agent_version or agent.agent_version,
                "updated_at": datetime.now(UTC),
            },
        )
        self.store.agents[agent.id] = updated
        return updated

    async def disable(self, *, agent_id: str, organization_id: str) -> Agent | None:
        agent = await self.find_by_id_for_organization(
            agent_id=agent_id,
            organization_id=organization_id,
        )
        if agent is None:
            return None
        updated = agent.model_copy(
            update={"status": AgentStatus.DISABLED, "updated_at": datetime.now(UTC)},
        )
        self.store.agents[agent.id] = updated
        return updated


class FakeEventRepository:
    def __init__(self, store: EventTestStore) -> None:
        self.store = store

    async def create_many(
        self,
        *,
        organization_id: str,
        agent_id: str,
        event_items: list[EventIngestItem],
    ) -> list[Event]:
        received_at = datetime.now(UTC)
        events = [
            Event(
                id=f"evt_{uuid4().hex}",
                organization_id=organization_id,
                agent_id=agent_id,
                event_type=item.event_type,
                severity=item.severity,
                source=item.source,
                title=item.title,
                description=item.description,
                raw_event=item.raw_event,
                normalized_fields=item.normalized_fields,
                tags=item.tags,
                timestamp=item.timestamp or received_at,
                received_at=received_at,
            )
            for item in event_items
        ]
        for event in events:
            self.store.events[event.id] = event
        return events

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
        events = [
            event
            for event in self.store.events.values()
            if event.organization_id == organization_id
            and (severity is None or event.severity == severity)
            and (source is None or event.source == source)
            and (event_type is None or event.event_type == event_type)
            and (agent_id is None or event.agent_id == agent_id)
        ]
        events.sort(key=lambda event: event.received_at, reverse=True)
        return events[skip : skip + limit]

    async def find_by_id_for_organization(
        self,
        *,
        event_id: str,
        organization_id: str,
    ) -> Event | None:
        event = self.store.events.get(event_id)
        if event is None or event.organization_id != organization_id:
            return None
        return event


class FakeDetectionRuleRepository:
    def __init__(self, store: EventTestStore) -> None:
        self.store = store

    async def list_for_organization(self, organization_id: str) -> list[DetectionRule]:
        custom_rules = [
            rule for rule in self.store.rules.values() if rule.organization_id == organization_id
        ]
        return [*builtin_detection_rules(), *custom_rules]

    async def list_enabled_for_organization(self, organization_id: str) -> list[DetectionRule]:
        return [rule for rule in await self.list_for_organization(organization_id) if rule.enabled]

    async def find_by_id_for_organization(
        self,
        *,
        rule_id: str,
        organization_id: str,
    ) -> DetectionRule | None:
        builtin = next((rule for rule in builtin_detection_rules() if rule.id == rule_id), None)
        if builtin is not None:
            return builtin
        rule = self.store.rules.get(rule_id)
        if rule is None or rule.organization_id != organization_id:
            return None
        return rule

    async def create(self, *, organization_id: str, rule: Any) -> DetectionRule:
        now = datetime.now(UTC)
        detection_rule = DetectionRule(
            id=f"rule_{uuid4().hex}",
            organization_id=organization_id,
            name=rule.name,
            description=rule.description,
            enabled=rule.enabled,
            severity=rule.severity,
            source=rule.source,
            event_type=rule.event_type,
            conditions=rule.conditions,
            mitre_tactics=rule.mitre_tactics,
            mitre_techniques=rule.mitre_techniques,
            tags=rule.tags,
            created_at=now,
            updated_at=now,
        )
        self.store.rules[detection_rule.id] = detection_rule
        return detection_rule

    async def update(
        self,
        *,
        rule_id: str,
        organization_id: str,
        updates: dict[str, Any],
    ) -> DetectionRule | None:
        rule = await self.find_by_id_for_organization(
            rule_id=rule_id,
            organization_id=organization_id,
        )
        if rule is None or rule.organization_id is None:
            return None
        updated = rule.model_copy(update={**updates, "updated_at": datetime.now(UTC)})
        self.store.rules[rule.id] = updated
        return updated

    async def set_enabled(
        self,
        *,
        rule_id: str,
        organization_id: str,
        enabled: bool,
    ) -> DetectionRule | None:
        return await self.update(
            rule_id=rule_id,
            organization_id=organization_id,
            updates={"enabled": enabled},
        )


class FakeDetectionResultRepository:
    def __init__(self, store: EventTestStore) -> None:
        self.store = store

    async def create(
        self,
        *,
        event: Event,
        rule: DetectionRule,
        matched_fields: dict[str, Any],
    ) -> DetectionResult:
        result = DetectionResult(
            id=f"det_{uuid4().hex}",
            organization_id=event.organization_id,
            agent_id=event.agent_id,
            event_id=event.id,
            rule_id=rule.id,
            rule_name=rule.name,
            severity=rule.severity,
            title=rule.name,
            description=rule.description,
            mitre_tactics=rule.mitre_tactics,
            mitre_techniques=rule.mitre_techniques,
            matched_fields=matched_fields,
            created_at=datetime.now(UTC),
        )
        self.store.results[result.id] = result
        return result

    async def list_by_organization(
        self,
        *,
        organization_id: str,
        limit: int = 100,
        skip: int = 0,
    ) -> list[DetectionResult]:
        results = [
            result
            for result in self.store.results.values()
            if result.organization_id == organization_id
        ]
        results.sort(key=lambda result: result.created_at, reverse=True)
        return results[skip : skip + limit]

    async def find_by_id_for_organization(
        self,
        *,
        result_id: str,
        organization_id: str,
    ) -> DetectionResult | None:
        result = self.store.results.get(result_id)
        if result is None or result.organization_id != organization_id:
            return None
        return result


class FakeAlertRepository:
    def __init__(self, store: EventTestStore) -> None:
        self.store = store

    async def create_from_detection_result(
        self,
        result: DetectionResult,
        tags: list[str] | None = None,
    ) -> Alert:
        now = datetime.now(UTC)
        alert = Alert(
            id=f"alr_{uuid4().hex}",
            organization_id=result.organization_id,
            agent_id=result.agent_id,
            event_id=result.event_id,
            detection_result_id=result.id,
            title=result.title,
            description=result.description,
            severity=result.severity,
            status=AlertStatus.OPEN,
            mitre_tactics=result.mitre_tactics,
            mitre_techniques=result.mitre_techniques,
            tags=tags or [],
            created_at=now,
            updated_at=now,
        )
        self.store.alerts[alert.id] = alert
        return alert

    async def list_by_organization(
        self,
        *,
        organization_id: str,
        limit: int = 100,
        skip: int = 0,
    ) -> list[Alert]:
        alerts = [
            alert
            for alert in self.store.alerts.values()
            if alert.organization_id == organization_id
        ]
        alerts.sort(key=lambda alert: alert.created_at, reverse=True)
        return alerts[skip : skip + limit]

    async def find_by_id_for_organization(
        self,
        *,
        alert_id: str,
        organization_id: str,
    ) -> Alert | None:
        alert = self.store.alerts.get(alert_id)
        if alert is None or alert.organization_id != organization_id:
            return None
        return alert

    async def update_status(
        self,
        *,
        alert_id: str,
        organization_id: str,
        status: AlertStatus,
    ) -> Alert | None:
        alert = await self.find_by_id_for_organization(
            alert_id=alert_id,
            organization_id=organization_id,
        )
        if alert is None:
            return None
        updated = alert.model_copy(update={"status": status, "updated_at": datetime.now(UTC)})
        self.store.alerts[alert.id] = updated
        return updated


class FakeIncidentRepository:
    def __init__(self, store: EventTestStore) -> None:
        self.store = store

    async def find_matching_open_incident(
        self,
        *,
        alert: Alert,
        correlation_window_minutes: int,
    ) -> Incident | None:
        earliest = alert.created_at - timedelta(minutes=correlation_window_minutes)
        candidates = [
            incident
            for incident in self.store.incidents.values()
            if incident.organization_id == alert.organization_id
            and alert.agent_id in incident.agent_ids
            and incident.status in {IncidentStatus.OPEN, IncidentStatus.INVESTIGATING}
            and incident.last_seen_at >= earliest
            and (
                incident.title == alert.title
                or bool(set(incident.mitre_techniques) & set(alert.mitre_techniques[:1]))
            )
        ]
        candidates.sort(key=lambda incident: incident.last_seen_at, reverse=True)
        return candidates[0] if candidates else None

    async def create_from_alert(self, alert: Alert) -> Incident:
        now = datetime.now(UTC)
        incident = Incident(
            id=f"inc_{uuid4().hex}",
            organization_id=alert.organization_id,
            title=alert.title,
            description=alert.description,
            severity=alert.severity,
            status=IncidentStatus.OPEN,
            alert_ids=[alert.id],
            detection_result_ids=[alert.detection_result_id],
            event_ids=[alert.event_id],
            agent_ids=[alert.agent_id],
            mitre_tactics=alert.mitre_tactics,
            mitre_techniques=alert.mitre_techniques,
            tags=alert.tags,
            first_seen_at=alert.created_at,
            last_seen_at=alert.created_at,
            created_at=now,
            updated_at=now,
        )
        self.store.incidents[incident.id] = incident
        return incident

    async def append_alert(self, *, incident: Incident, alert: Alert) -> Incident:
        updated = incident.model_copy(
            update={
                "severity": max_severity(incident.severity, alert.severity),
                "alert_ids": append_unique(incident.alert_ids, [alert.id]),
                "detection_result_ids": append_unique(
                    incident.detection_result_ids,
                    [alert.detection_result_id],
                ),
                "event_ids": append_unique(incident.event_ids, [alert.event_id]),
                "agent_ids": append_unique(incident.agent_ids, [alert.agent_id]),
                "mitre_tactics": merge_unique(incident.mitre_tactics, alert.mitre_tactics),
                "mitre_techniques": merge_unique(
                    incident.mitre_techniques,
                    alert.mitre_techniques,
                ),
                "tags": merge_unique(incident.tags, alert.tags),
                "last_seen_at": max(incident.last_seen_at, alert.created_at),
                "updated_at": datetime.now(UTC),
            },
        )
        self.store.incidents[incident.id] = updated
        return updated

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
        incidents = [
            incident
            for incident in self.store.incidents.values()
            if incident.organization_id == organization_id
            and (status is None or incident.status == status)
            and (severity is None or incident.severity == severity)
            and (agent_id is None or agent_id in incident.agent_ids)
            and (mitre_technique is None or mitre_technique in incident.mitre_techniques)
        ]
        incidents.sort(key=lambda incident: incident.updated_at, reverse=True)
        return incidents[skip : skip + limit]

    async def find_by_id_for_organization(
        self,
        *,
        incident_id: str,
        organization_id: str,
    ) -> Incident | None:
        incident = self.store.incidents.get(incident_id)
        if incident is None or incident.organization_id != organization_id:
            return None
        return incident

    async def update_status(
        self,
        *,
        incident_id: str,
        organization_id: str,
        status: IncidentStatus,
    ) -> Incident | None:
        return await self._update(
            incident_id=incident_id,
            organization_id=organization_id,
            fields={"status": status},
        )

    async def update_assignment(
        self,
        *,
        incident_id: str,
        organization_id: str,
        assigned_to_user_id: str | None,
    ) -> Incident | None:
        return await self._update(
            incident_id=incident_id,
            organization_id=organization_id,
            fields={"assigned_to_user_id": assigned_to_user_id},
        )

    async def update_summary(
        self,
        *,
        incident_id: str,
        organization_id: str,
        summary: str | None,
    ) -> Incident | None:
        return await self._update(
            incident_id=incident_id,
            organization_id=organization_id,
            fields={"summary": summary},
        )

    async def _update(
        self,
        *,
        incident_id: str,
        organization_id: str,
        fields: dict[str, Any],
    ) -> Incident | None:
        incident = await self.find_by_id_for_organization(
            incident_id=incident_id,
            organization_id=organization_id,
        )
        if incident is None:
            return None
        updated = incident.model_copy(update={**fields, "updated_at": datetime.now(UTC)})
        self.store.incidents[incident.id] = updated
        return updated


@pytest.fixture(autouse=True)
def clear_settings_cache() -> Iterator[None]:
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


@pytest.fixture
def store() -> EventTestStore:
    return EventTestStore()


@pytest.fixture
def client(store: EventTestStore) -> Iterator[TestClient]:
    app.dependency_overrides[get_user_repository] = lambda: FakeUserRepository(store)
    app.dependency_overrides[get_organization_repository] = (
        lambda: FakeOrganizationRepository(store)
    )
    app.dependency_overrides[get_agent_repository] = lambda: FakeAgentRepository(store)
    app.dependency_overrides[get_event_repository] = lambda: FakeEventRepository(store)
    app.dependency_overrides[get_detection_rule_repository] = (
        lambda: FakeDetectionRuleRepository(store)
    )
    app.dependency_overrides[get_detection_result_repository] = (
        lambda: FakeDetectionResultRepository(store)
    )
    app.dependency_overrides[get_alert_repository] = lambda: FakeAlertRepository(store)
    app.dependency_overrides[get_incident_repository] = lambda: FakeIncidentRepository(store)
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


def create_organization(store: EventTestStore, *, name: str) -> Organization:
    now = datetime.now(UTC)
    organization = Organization(
        id=f"org_{uuid4().hex}",
        name=name,
        created_at=now,
        updated_at=now,
    )
    store.organizations[organization.id] = organization
    return organization


def create_user(
    store: EventTestStore,
    *,
    organization_id: str,
    role: Role,
    email: str,
) -> tuple[User, str]:
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


def create_agent(
    store: EventTestStore,
    *,
    organization_id: str,
    api_key_hash: str,
    name: str = "agent-1",
    hostname: str = "agent-1.local",
    os_type: OSType = OSType.LINUX,
    agent_version: str | None = "1.0.0",
    ip_address: str | None = None,
    tags: list[str] | None = None,
    status: AgentStatus = AgentStatus.OFFLINE,
) -> Agent:
    now = datetime.now(UTC)
    agent = Agent(
        id=f"agt_{uuid4().hex}",
        organization_id=organization_id,
        name=name,
        hostname=hostname,
        os_type=os_type,
        agent_version=agent_version,
        status=status,
        api_key_hash=api_key_hash,
        last_seen_at=None,
        ip_address=ip_address,
        tags=tags or [],
        created_at=now,
        updated_at=now,
    )
    store.agents[agent.id] = agent
    return agent


def seed_principal(
    store: EventTestStore,
    *,
    role: Role = Role.ORG_ADMIN,
    email: str = "admin@example.com",
) -> tuple[Organization, User, str]:
    organization = create_organization(store, name=f"Org {uuid4().hex[:6]}")
    user, token = create_user(
        store,
        organization_id=organization.id,
        role=role,
        email=email,
    )
    return organization, user, token


def seed_agent(store: EventTestStore, *, organization_id: str) -> tuple[Agent, str]:
    api_key = f"sxag_test_{uuid4().hex}"
    agent = create_agent(
        store,
        organization_id=organization_id,
        api_key_hash=hash_agent_api_key(api_key),
    )
    return agent, api_key


def event_payload(**overrides: Any) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "event_type": "process_start",
        "severity": "info",
        "source": "linux",
        "title": "Process started",
        "description": "bash started",
        "raw_event": {"pid": 1234, "process_name": "bash"},
        "normalized_fields": {"process.name": "bash"},
        "tags": ["process"],
    }
    payload.update(overrides)
    return payload


def ingest_events(client: TestClient, api_key: str, events: list[dict[str, Any]]) -> dict:
    response = client.post(
        "/api/events/ingest",
        headers={"X-Agent-Key": api_key},
        json={"events": events},
    )
    assert response.status_code == 201
    return response.json()


def test_valid_batch_ingest_stores_events(client: TestClient, store: EventTestStore) -> None:
    organization, _, _ = seed_principal(store)
    agent, api_key = seed_agent(store, organization_id=organization.id)

    body = ingest_events(
        client,
        api_key,
        [event_payload(), event_payload(event_type="network_connect", source="network")],
    )

    assert body["accepted"] == 2
    assert len(store.events) == 2
    assert store.agents[agent.id].status == AgentStatus.ONLINE
    assert store.agents[agent.id].last_seen_at is not None


def test_ingest_without_agent_key_rejected(client: TestClient) -> None:
    response = client.post("/api/events/ingest", json={"events": [event_payload()]})

    assert response.status_code == 401


def test_ingest_invalid_agent_key_rejected(client: TestClient) -> None:
    response = client.post(
        "/api/events/ingest",
        headers={"X-Agent-Key": "invalid-key"},
        json={"events": [event_payload()]},
    )

    assert response.status_code == 401


def test_disabled_agent_cannot_ingest(client: TestClient, store: EventTestStore) -> None:
    organization, _, _ = seed_principal(store)
    agent, api_key = seed_agent(store, organization_id=organization.id)
    store.agents[agent.id] = agent.model_copy(update={"status": AgentStatus.DISABLED})

    response = client.post(
        "/api/events/ingest",
        headers={"X-Agent-Key": api_key},
        json={"events": [event_payload()]},
    )

    assert response.status_code == 403
    assert len(store.events) == 0


def test_organization_id_and_agent_id_are_server_assigned(
    client: TestClient,
    store: EventTestStore,
) -> None:
    organization, _, _ = seed_principal(store)
    agent, api_key = seed_agent(store, organization_id=organization.id)

    body = ingest_events(
        client,
        api_key,
        [
            event_payload(
                organization_id="org_client_supplied",
                agent_id="agt_client_supplied",
            ),
        ],
    )

    event = body["events"][0]
    assert event["organization_id"] == organization.id
    assert event["agent_id"] == agent.id


def test_missing_timestamp_gets_server_timestamp(
    client: TestClient,
    store: EventTestStore,
) -> None:
    organization, _, _ = seed_principal(store)
    _, api_key = seed_agent(store, organization_id=organization.id)

    before = datetime.now(UTC)
    body = ingest_events(client, api_key, [event_payload()])
    after = datetime.now(UTC)

    event_timestamp = datetime.fromisoformat(body["events"][0]["timestamp"])
    assert before <= event_timestamp <= after


def test_batch_size_limit_enforced(
    client: TestClient,
    store: EventTestStore,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    organization, _, _ = seed_principal(store)
    _, api_key = seed_agent(store, organization_id=organization.id)
    monkeypatch.setenv("EVENT_INGEST_BATCH_SIZE_LIMIT", "1")
    get_settings.cache_clear()

    response = client.post(
        "/api/events/ingest",
        headers={"X-Agent-Key": api_key},
        json={"events": [event_payload(), event_payload(event_type="file_write")]},
    )

    assert response.status_code == 413


def test_invalid_event_payload_returns_clean_422(client: TestClient, store: EventTestStore) -> None:
    organization, _, _ = seed_principal(store)
    _, api_key = seed_agent(store, organization_id=organization.id)

    response = client.post(
        "/api/events/ingest",
        headers={"X-Agent-Key": api_key},
        json={"events": [event_payload(raw_event="not-an-object")]},
    )

    assert response.status_code == 422
    assert "detail" in response.json()


def test_list_events_organization_scoped(client: TestClient, store: EventTestStore) -> None:
    org_one, _, token_one = seed_principal(store, email="one@example.com")
    org_two, _, _ = seed_principal(store, email="two@example.com")
    _, key_one = seed_agent(store, organization_id=org_one.id)
    _, key_two = seed_agent(store, organization_id=org_two.id)
    ingest_events(client, key_one, [event_payload(title="Org one event")])
    ingest_events(client, key_two, [event_payload(title="Org two event")])

    response = client.get("/api/events", headers={"Authorization": f"Bearer {token_one}"})

    assert response.status_code == 200
    body = response.json()
    assert body["count"] == 1
    assert body["events"][0]["title"] == "Org one event"


@pytest.mark.parametrize(
    ("filter_name", "filter_value", "expected_title"),
    [
        ("severity", "critical", "Critical event"),
        ("source", "network", "Network event"),
        ("event_type", "file_write", "File event"),
    ],
)
def test_filters_work_for_severity_source_event_type(
    client: TestClient,
    store: EventTestStore,
    filter_name: str,
    filter_value: str,
    expected_title: str,
) -> None:
    organization, _, token = seed_principal(store)
    _, api_key = seed_agent(store, organization_id=organization.id)
    ingest_events(
        client,
        api_key,
        [
            event_payload(title="Critical event", severity="critical"),
            event_payload(title="Network event", source="network"),
            event_payload(title="File event", event_type="file_write"),
        ],
    )

    response = client.get(
        "/api/events",
        params={filter_name: filter_value},
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    titles = {event["title"] for event in response.json()["events"]}
    assert expected_title in titles


def test_filter_works_for_agent_id(client: TestClient, store: EventTestStore) -> None:
    organization, _, token = seed_principal(store)
    agent_one, key_one = seed_agent(store, organization_id=organization.id)
    agent_two, key_two = seed_agent(store, organization_id=organization.id)
    ingest_events(client, key_one, [event_payload(title="Agent one event")])
    ingest_events(client, key_two, [event_payload(title="Agent two event")])

    response = client.get(
        "/api/events",
        params={"agent_id": agent_one.id},
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["count"] == 1
    assert body["events"][0]["agent_id"] == agent_one.id
    assert body["events"][0]["agent_id"] != agent_two.id


def test_get_event_by_id_works(client: TestClient, store: EventTestStore) -> None:
    organization, _, token = seed_principal(store)
    _, api_key = seed_agent(store, organization_id=organization.id)
    ingested = ingest_events(client, api_key, [event_payload()])
    event_id = ingested["events"][0]["id"]

    response = client.get(
        f"/api/events/{event_id}",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    assert response.json()["id"] == event_id


def test_cross_org_event_access_blocked(client: TestClient, store: EventTestStore) -> None:
    org_one, _, _ = seed_principal(store, email="one@example.com")
    _, key_one = seed_agent(store, organization_id=org_one.id)
    org_two, _, token_two = seed_principal(store, email="two@example.com")
    assert org_two.id != org_one.id
    ingested = ingest_events(client, key_one, [event_payload()])
    event_id = ingested["events"][0]["id"]

    response = client.get(
        f"/api/events/{event_id}",
        headers={"Authorization": f"Bearer {token_two}"},
    )

    assert response.status_code == 404


def test_viewer_can_list_read_events(client: TestClient, store: EventTestStore) -> None:
    organization, _, _ = seed_principal(store)
    _, viewer_token = create_user(
        store,
        organization_id=organization.id,
        role=Role.VIEWER,
        email="viewer@example.com",
    )
    _, api_key = seed_agent(store, organization_id=organization.id)
    ingested = ingest_events(client, api_key, [event_payload()])
    event_id = ingested["events"][0]["id"]

    list_response = client.get(
        "/api/events",
        headers={"Authorization": f"Bearer {viewer_token}"},
    )
    detail_response = client.get(
        f"/api/events/{event_id}",
        headers={"Authorization": f"Bearer {viewer_token}"},
    )

    assert list_response.status_code == 200
    assert detail_response.status_code == 200


def powershell_event() -> dict[str, Any]:
    return event_payload(
        event_type="process_start",
        severity="info",
        source="windows",
        title="PowerShell started",
        raw_event={"image": "powershell.exe"},
        normalized_fields={"command_line": "powershell.exe -NoP -enc SQBFAFgA"},
    )


def mimikatz_event() -> dict[str, Any]:
    return event_payload(
        event_type="process_start",
        severity="high",
        source="windows",
        title="Suspicious credential tool",
        raw_event={"image": "mimikatz.exe"},
        normalized_fields={"command_line": "mimikatz.exe sekurlsa::logonpasswords"},
    )


def custom_rule_payload(**overrides: Any) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "name": "Custom Curl Download",
        "description": "Curl download command observed",
        "enabled": True,
        "severity": "medium",
        "source": "linux",
        "event_type": "process_start",
        "conditions": {
            "all": [
                {
                    "field": "normalized_fields.command_line",
                    "operator": "contains",
                    "value": "curl",
                }
            ]
        },
        "mitre_tactics": ["Command and Control"],
        "mitre_techniques": ["T1105"],
        "tags": ["custom"],
    }
    payload.update(overrides)
    return payload


def test_builtin_rules_are_available_listable(client: TestClient, store: EventTestStore) -> None:
    _, _, token = seed_principal(store)

    response = client.get(
        "/api/detections/rules",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    rules = response.json()["rules"]
    assert len(rules) >= 10
    assert "Suspicious PowerShell Encoded Command" in {rule["name"] for rule in rules}


def test_ingestion_creates_detection_and_alert_for_powershell(
    client: TestClient,
    store: EventTestStore,
) -> None:
    organization, _, _ = seed_principal(store)
    _, api_key = seed_agent(store, organization_id=organization.id)

    body = ingest_events(client, api_key, [powershell_event()])

    assert body["detections_created"] == 1
    assert body["alerts_created"] == 1
    assert next(iter(store.results.values())).rule_name == "Suspicious PowerShell Encoded Command"
    assert next(iter(store.alerts.values())).title == "Suspicious PowerShell Encoded Command"


def test_ingestion_creates_detection_and_alert_for_mimikatz(
    client: TestClient,
    store: EventTestStore,
) -> None:
    organization, _, _ = seed_principal(store)
    _, api_key = seed_agent(store, organization_id=organization.id)

    body = ingest_events(client, api_key, [mimikatz_event()])

    assert body["detections_created"] == 1
    assert body["alerts_created"] == 1
    assert next(iter(store.results.values())).rule_name == "Possible Mimikatz Execution"


def test_non_matching_event_creates_no_detection(
    client: TestClient,
    store: EventTestStore,
) -> None:
    organization, _, _ = seed_principal(store)
    _, api_key = seed_agent(store, organization_id=organization.id)

    body = ingest_events(client, api_key, [event_payload()])

    assert body["detections_created"] == 0
    assert body["alerts_created"] == 0
    assert store.results == {}
    assert store.alerts == {}


def test_invalid_rule_condition_rejected(client: TestClient, store: EventTestStore) -> None:
    _, _, token = seed_principal(store, role=Role.ANALYST)

    response = client.post(
        "/api/detections/rules",
        headers={"Authorization": f"Bearer {token}"},
        json=custom_rule_payload(
            conditions={
                "all": [
                    {
                        "field": "normalized_fields.command_line",
                        "operator": "eval",
                        "value": "curl",
                    }
                ]
            },
        ),
    )

    assert response.status_code == 422


def test_viewer_can_list_read_rules_results_alerts(
    client: TestClient,
    store: EventTestStore,
) -> None:
    organization, _, _ = seed_principal(store)
    _, viewer_token = create_user(
        store,
        organization_id=organization.id,
        role=Role.VIEWER,
        email="viewer-detection@example.com",
    )
    _, api_key = seed_agent(store, organization_id=organization.id)
    ingest_events(client, api_key, [powershell_event()])
    result_id = next(iter(store.results))
    alert_id = next(iter(store.alerts))

    rules_response = client.get(
        "/api/detections/rules",
        headers={"Authorization": f"Bearer {viewer_token}"},
    )
    result_response = client.get(
        f"/api/detections/results/{result_id}",
        headers={"Authorization": f"Bearer {viewer_token}"},
    )
    alert_response = client.get(
        f"/api/alerts/{alert_id}",
        headers={"Authorization": f"Bearer {viewer_token}"},
    )

    assert rules_response.status_code == 200
    assert result_response.status_code == 200
    assert alert_response.status_code == 200


def test_viewer_cannot_create_update_rules(client: TestClient, store: EventTestStore) -> None:
    organization, _, _ = seed_principal(store)
    _, viewer_token = create_user(
        store,
        organization_id=organization.id,
        role=Role.VIEWER,
        email="viewer-rules@example.com",
    )

    create_response = client.post(
        "/api/detections/rules",
        headers={"Authorization": f"Bearer {viewer_token}"},
        json=custom_rule_payload(),
    )
    update_response = client.patch(
        "/api/detections/rules/rule_missing",
        headers={"Authorization": f"Bearer {viewer_token}"},
        json={"enabled": False},
    )

    assert create_response.status_code == 403
    assert update_response.status_code == 403


def test_analyst_can_create_custom_rule(client: TestClient, store: EventTestStore) -> None:
    _, _, token = seed_principal(store, role=Role.ANALYST)

    response = client.post(
        "/api/detections/rules",
        headers={"Authorization": f"Bearer {token}"},
        json=custom_rule_payload(),
    )

    assert response.status_code == 201
    assert response.json()["organization_id"] is not None
    assert response.json()["name"] == "Custom Curl Download"


def test_custom_rule_triggers_on_matching_event(client: TestClient, store: EventTestStore) -> None:
    organization, _, token = seed_principal(store, role=Role.ANALYST)
    _, api_key = seed_agent(store, organization_id=organization.id)
    create_response = client.post(
        "/api/detections/rules",
        headers={"Authorization": f"Bearer {token}"},
        json=custom_rule_payload(),
    )
    assert create_response.status_code == 201

    body = ingest_events(
        client,
        api_key,
        [
            event_payload(
                normalized_fields={"command_line": "curl http://example.test/payload.sh"}
            )
        ],
    )

    assert body["detections_created"] == 1
    assert next(iter(store.results.values())).rule_name == "Custom Curl Download"


def test_disabled_custom_rule_does_not_trigger(
    client: TestClient,
    store: EventTestStore,
) -> None:
    organization, _, token = seed_principal(store, role=Role.ORG_ADMIN)
    _, api_key = seed_agent(store, organization_id=organization.id)
    create_response = client.post(
        "/api/detections/rules",
        headers={"Authorization": f"Bearer {token}"},
        json=custom_rule_payload(),
    )
    rule_id = create_response.json()["id"]
    disable_response = client.post(
        f"/api/detections/rules/{rule_id}/disable",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert disable_response.status_code == 200

    body = ingest_events(
        client,
        api_key,
        [
            event_payload(
                normalized_fields={"command_line": "curl http://example.test/payload.sh"}
            )
        ],
    )

    assert body["detections_created"] == 0
    assert store.results == {}


def test_alert_status_update_works_for_analyst(
    client: TestClient,
    store: EventTestStore,
) -> None:
    organization, _, token = seed_principal(store, role=Role.ANALYST)
    _, api_key = seed_agent(store, organization_id=organization.id)
    ingest_events(client, api_key, [powershell_event()])
    alert_id = next(iter(store.alerts))

    response = client.patch(
        f"/api/alerts/{alert_id}/status",
        headers={"Authorization": f"Bearer {token}"},
        json={"status": "investigating"},
    )

    assert response.status_code == 200
    assert response.json()["status"] == "investigating"


def test_cross_org_detection_result_access_blocked(
    client: TestClient,
    store: EventTestStore,
) -> None:
    org_one, _, _ = seed_principal(store, email="det-one@example.com")
    _, key_one = seed_agent(store, organization_id=org_one.id)
    _, _, token_two = seed_principal(store, email="det-two@example.com")
    ingest_events(client, key_one, [powershell_event()])
    result_id = next(iter(store.results))

    response = client.get(
        f"/api/detections/results/{result_id}",
        headers={"Authorization": f"Bearer {token_two}"},
    )

    assert response.status_code == 404


def test_cross_org_alert_access_blocked(client: TestClient, store: EventTestStore) -> None:
    org_one, _, _ = seed_principal(store, email="alert-one@example.com")
    _, key_one = seed_agent(store, organization_id=org_one.id)
    _, _, token_two = seed_principal(store, email="alert-two@example.com")
    ingest_events(client, key_one, [powershell_event()])
    alert_id = next(iter(store.alerts))

    response = client.get(
        f"/api/alerts/{alert_id}",
        headers={"Authorization": f"Bearer {token_two}"},
    )

    assert response.status_code == 404


def test_ingestion_response_includes_detection_and_alert_counts(
    client: TestClient,
    store: EventTestStore,
) -> None:
    organization, _, _ = seed_principal(store)
    _, api_key = seed_agent(store, organization_id=organization.id)

    body = ingest_events(client, api_key, [powershell_event()])

    assert body["accepted"] == 1
    assert body["detections_created"] == 1
    assert body["alerts_created"] == 1


def test_ingestion_creates_incident_when_alert_created(
    client: TestClient,
    store: EventTestStore,
) -> None:
    organization, _, _ = seed_principal(store)
    _, api_key = seed_agent(store, organization_id=organization.id)

    body = ingest_events(client, api_key, [powershell_event()])

    assert body["incidents_created"] == 1
    assert body["incidents_updated"] == 0
    incident = next(iter(store.incidents.values()))
    assert incident.alert_ids == [next(iter(store.alerts))]


def test_second_matching_alert_updates_existing_incident(
    client: TestClient,
    store: EventTestStore,
) -> None:
    organization, _, _ = seed_principal(store)
    _, api_key = seed_agent(store, organization_id=organization.id)

    ingest_events(client, api_key, [powershell_event()])
    second = ingest_events(client, api_key, [powershell_event()])

    assert second["incidents_created"] == 0
    assert second["incidents_updated"] == 1
    assert len(store.incidents) == 1
    assert len(next(iter(store.incidents.values())).alert_ids) == 2


def test_non_matching_alert_creates_separate_incident(
    client: TestClient,
    store: EventTestStore,
) -> None:
    organization, _, _ = seed_principal(store)
    _, api_key = seed_agent(store, organization_id=organization.id)

    ingest_events(client, api_key, [powershell_event()])
    ingest_events(client, api_key, [mimikatz_event()])

    assert len(store.incidents) == 2


def test_incident_severity_becomes_max_linked_alert_severity(
    client: TestClient,
    store: EventTestStore,
) -> None:
    organization, _, _ = seed_principal(store)
    _, api_key = seed_agent(store, organization_id=organization.id)
    low_rule = custom_rule_payload(name="Repeated Tool", severity="low")
    critical_rule = custom_rule_payload(name="Critical Repeated Tool", severity="critical")
    for payload in [low_rule, critical_rule]:
        rule = DetectionRule(
            id=f"rule_{uuid4().hex}",
            organization_id=organization.id,
            name=payload["name"],
            description=payload["description"],
            enabled=True,
            severity=EventSeverity(payload["severity"]),
            source=EventSource(payload["source"]),
            event_type=payload["event_type"],
            conditions=payload["conditions"],
            mitre_tactics=payload["mitre_tactics"],
            mitre_techniques=["T1105"],
            tags=payload["tags"],
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )
        store.rules[rule.id] = rule

    ingest_events(
        client,
        api_key,
        [event_payload(normalized_fields={"command_line": "curl http://example.test/a"})],
    )

    incident = next(iter(store.incidents.values()))
    assert incident.severity == EventSeverity.CRITICAL
    assert len(incident.alert_ids) == 2


def test_ingestion_response_includes_incident_counts(
    client: TestClient,
    store: EventTestStore,
) -> None:
    organization, _, _ = seed_principal(store)
    _, api_key = seed_agent(store, organization_id=organization.id)

    first = ingest_events(client, api_key, [powershell_event()])
    second = ingest_events(client, api_key, [powershell_event()])

    assert first["incidents_created"] == 1
    assert first["incidents_updated"] == 0
    assert second["incidents_created"] == 0
    assert second["incidents_updated"] == 1


def test_list_incidents_org_scoped(client: TestClient, store: EventTestStore) -> None:
    org_one, _, token_one = seed_principal(store, email="inc-one@example.com")
    _, key_one = seed_agent(store, organization_id=org_one.id)
    org_two, _, _ = seed_principal(store, email="inc-two@example.com")
    _, key_two = seed_agent(store, organization_id=org_two.id)
    ingest_events(client, key_one, [powershell_event()])
    ingest_events(client, key_two, [powershell_event()])

    response = client.get("/api/incidents", headers={"Authorization": f"Bearer {token_one}"})

    assert response.status_code == 200
    assert response.json()["count"] == 1


@pytest.mark.parametrize(
    ("params", "expected_count"),
    [
        ({"status": "open"}, 2),
        ({"severity": "critical"}, 1),
        ({"mitre_technique": "T1003"}, 1),
    ],
)
def test_incident_filters_work_for_status_severity_mitre(
    client: TestClient,
    store: EventTestStore,
    params: dict[str, str],
    expected_count: int,
) -> None:
    organization, _, token = seed_principal(store)
    _, api_key = seed_agent(store, organization_id=organization.id)
    ingest_events(client, api_key, [powershell_event()])
    ingest_events(client, api_key, [mimikatz_event()])

    response = client.get(
        "/api/incidents",
        params=params,
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    assert response.json()["count"] == expected_count


def test_incident_filter_works_for_agent_id(client: TestClient, store: EventTestStore) -> None:
    organization, _, token = seed_principal(store)
    agent_one, key_one = seed_agent(store, organization_id=organization.id)
    _, key_two = seed_agent(store, organization_id=organization.id)
    ingest_events(client, key_one, [powershell_event()])
    ingest_events(client, key_two, [powershell_event()])

    response = client.get(
        "/api/incidents",
        params={"agent_id": agent_one.id},
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    assert response.json()["count"] == 1
    assert response.json()["incidents"][0]["agent_ids"] == [agent_one.id]


def test_get_incident_by_id_works(client: TestClient, store: EventTestStore) -> None:
    organization, _, token = seed_principal(store)
    _, api_key = seed_agent(store, organization_id=organization.id)
    ingest_events(client, api_key, [powershell_event()])
    incident_id = next(iter(store.incidents))

    response = client.get(
        f"/api/incidents/{incident_id}",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    assert response.json()["id"] == incident_id


def test_cross_org_incident_access_blocked(client: TestClient, store: EventTestStore) -> None:
    org_one, _, _ = seed_principal(store, email="inc-cross-one@example.com")
    _, key_one = seed_agent(store, organization_id=org_one.id)
    _, _, token_two = seed_principal(store, email="inc-cross-two@example.com")
    ingest_events(client, key_one, [powershell_event()])
    incident_id = next(iter(store.incidents))

    response = client.get(
        f"/api/incidents/{incident_id}",
        headers={"Authorization": f"Bearer {token_two}"},
    )

    assert response.status_code == 404


def test_viewer_can_list_read_but_cannot_update_incident(
    client: TestClient,
    store: EventTestStore,
) -> None:
    organization, _, _ = seed_principal(store)
    _, viewer_token = create_user(
        store,
        organization_id=organization.id,
        role=Role.VIEWER,
        email="viewer-incidents@example.com",
    )
    _, api_key = seed_agent(store, organization_id=organization.id)
    ingest_events(client, api_key, [powershell_event()])
    incident_id = next(iter(store.incidents))

    list_response = client.get(
        "/api/incidents",
        headers={"Authorization": f"Bearer {viewer_token}"},
    )
    detail_response = client.get(
        f"/api/incidents/{incident_id}",
        headers={"Authorization": f"Bearer {viewer_token}"},
    )
    status_response = client.patch(
        f"/api/incidents/{incident_id}/status",
        headers={"Authorization": f"Bearer {viewer_token}"},
        json={"status": "investigating"},
    )

    assert list_response.status_code == 200
    assert detail_response.status_code == 200
    assert status_response.status_code == 403


def test_analyst_can_update_incident_status(client: TestClient, store: EventTestStore) -> None:
    organization, _, token = seed_principal(store, role=Role.ANALYST)
    _, api_key = seed_agent(store, organization_id=organization.id)
    ingest_events(client, api_key, [powershell_event()])
    incident_id = next(iter(store.incidents))

    response = client.patch(
        f"/api/incidents/{incident_id}/status",
        headers={"Authorization": f"Bearer {token}"},
        json={"status": "investigating"},
    )

    assert response.status_code == 200
    assert response.json()["status"] == "investigating"


def test_invalid_incident_status_transition_rejected(
    client: TestClient,
    store: EventTestStore,
) -> None:
    organization, _, token = seed_principal(store, role=Role.ANALYST)
    _, api_key = seed_agent(store, organization_id=organization.id)
    ingest_events(client, api_key, [powershell_event()])
    incident_id = next(iter(store.incidents))
    first = client.patch(
        f"/api/incidents/{incident_id}/status",
        headers={"Authorization": f"Bearer {token}"},
        json={"status": "resolved"},
    )
    assert first.status_code == 200

    response = client.patch(
        f"/api/incidents/{incident_id}/status",
        headers={"Authorization": f"Bearer {token}"},
        json={"status": "investigating"},
    )

    assert response.status_code == 400


def test_org_admin_can_reopen_resolved_incident(client: TestClient, store: EventTestStore) -> None:
    organization, _, token = seed_principal(store, role=Role.ORG_ADMIN)
    _, api_key = seed_agent(store, organization_id=organization.id)
    ingest_events(client, api_key, [powershell_event()])
    incident_id = next(iter(store.incidents))
    resolved = client.patch(
        f"/api/incidents/{incident_id}/status",
        headers={"Authorization": f"Bearer {token}"},
        json={"status": "resolved"},
    )
    assert resolved.status_code == 200

    response = client.patch(
        f"/api/incidents/{incident_id}/status",
        headers={"Authorization": f"Bearer {token}"},
        json={"status": "open"},
    )

    assert response.status_code == 200
    assert response.json()["status"] == "open"


def test_assign_incident_to_same_org_user_works(
    client: TestClient,
    store: EventTestStore,
) -> None:
    organization, _, token = seed_principal(store, role=Role.ANALYST)
    assignee, _ = create_user(
        store,
        organization_id=organization.id,
        role=Role.ANALYST,
        email="assignee@example.com",
    )
    _, api_key = seed_agent(store, organization_id=organization.id)
    ingest_events(client, api_key, [powershell_event()])
    incident_id = next(iter(store.incidents))

    response = client.patch(
        f"/api/incidents/{incident_id}/assign",
        headers={"Authorization": f"Bearer {token}"},
        json={"assigned_to_user_id": assignee.id},
    )

    assert response.status_code == 200
    assert response.json()["assigned_to_user_id"] == assignee.id


def test_cross_org_assignment_blocked(client: TestClient, store: EventTestStore) -> None:
    organization, _, token = seed_principal(store, role=Role.ANALYST)
    other_org, _, _ = seed_principal(store, email="other-assignee-org@example.com")
    other_user, _ = create_user(
        store,
        organization_id=other_org.id,
        role=Role.ANALYST,
        email="other-assignee@example.com",
    )
    _, api_key = seed_agent(store, organization_id=organization.id)
    ingest_events(client, api_key, [powershell_event()])
    incident_id = next(iter(store.incidents))

    response = client.patch(
        f"/api/incidents/{incident_id}/assign",
        headers={"Authorization": f"Bearer {token}"},
        json={"assigned_to_user_id": other_user.id},
    )

    assert response.status_code == 404


def test_clearing_incident_assignment_works(client: TestClient, store: EventTestStore) -> None:
    organization, _, token = seed_principal(store, role=Role.ANALYST)
    assignee, _ = create_user(
        store,
        organization_id=organization.id,
        role=Role.ANALYST,
        email="clear-assignee@example.com",
    )
    _, api_key = seed_agent(store, organization_id=organization.id)
    ingest_events(client, api_key, [powershell_event()])
    incident_id = next(iter(store.incidents))
    assigned = client.patch(
        f"/api/incidents/{incident_id}/assign",
        headers={"Authorization": f"Bearer {token}"},
        json={"assigned_to_user_id": assignee.id},
    )
    assert assigned.status_code == 200

    response = client.patch(
        f"/api/incidents/{incident_id}/assign",
        headers={"Authorization": f"Bearer {token}"},
        json={"assigned_to_user_id": None},
    )

    assert response.status_code == 200
    assert response.json()["assigned_to_user_id"] is None


def test_updating_incident_summary_works(client: TestClient, store: EventTestStore) -> None:
    organization, _, token = seed_principal(store, role=Role.ANALYST)
    _, api_key = seed_agent(store, organization_id=organization.id)
    ingest_events(client, api_key, [powershell_event()])
    incident_id = next(iter(store.incidents))

    response = client.patch(
        f"/api/incidents/{incident_id}/summary",
        headers={"Authorization": f"Bearer {token}"},
        json={"summary": "Encoded PowerShell activity under investigation."},
    )

    assert response.status_code == 200
    assert response.json()["summary"] == "Encoded PowerShell activity under investigation."


def test_duplicate_incident_references_are_not_added(
    client: TestClient,
    store: EventTestStore,
) -> None:
    organization, _, _ = seed_principal(store)
    _, api_key = seed_agent(store, organization_id=organization.id)
    ingest_events(client, api_key, [powershell_event()])
    incident = next(iter(store.incidents.values()))
    alert = next(iter(store.alerts.values()))

    updated = awaitable_append_duplicate(store, incident, alert)

    assert len(updated.alert_ids) == 1
    assert len(updated.detection_result_ids) == 1
    assert len(updated.event_ids) == 1
    assert len(updated.agent_ids) == 1


def awaitable_append_duplicate(
    store: EventTestStore,
    incident: Incident,
    alert: Alert,
) -> Incident:
    updated = incident.model_copy(
        update={
            "alert_ids": append_unique(incident.alert_ids, [alert.id]),
            "detection_result_ids": append_unique(
                incident.detection_result_ids,
                [alert.detection_result_id],
            ),
            "event_ids": append_unique(incident.event_ids, [alert.event_id]),
            "agent_ids": append_unique(incident.agent_ids, [alert.agent_id]),
        },
    )
    store.incidents[incident.id] = updated
    return updated
