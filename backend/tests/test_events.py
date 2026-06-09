from collections.abc import Iterator
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from app.api.dependencies import (
    get_agent_repository,
    get_event_repository,
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
from app.models.auth import Role, UserStatus
from app.models.event import Event, EventSeverity, EventSource
from app.models.organization import Organization
from app.models.user import User
from app.schemas.events import EventIngestItem


class EventTestStore:
    def __init__(self) -> None:
        self.users: dict[str, User] = {}
        self.organizations: dict[str, Organization] = {}
        self.agents: dict[str, Agent] = {}
        self.events: dict[str, Event] = {}


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
