from collections.abc import Iterator
from datetime import UTC, datetime
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from app.api.dependencies import (
    get_agent_repository,
    get_organization_repository,
    get_user_repository,
)
from app.core.config import get_settings
from app.core.security import create_token, hash_password, verify_agent_api_key
from app.main import app
from app.models.agent import Agent, AgentStatus, OSType
from app.models.auth import Role, UserStatus
from app.models.organization import Organization
from app.models.user import User


class AgentTestStore:
    def __init__(self) -> None:
        self.users: dict[str, User] = {}
        self.organizations: dict[str, Organization] = {}
        self.agents: dict[str, Agent] = {}


class FakeOrganizationRepository:
    def __init__(self, store: AgentTestStore) -> None:
        self.store = store

    async def count(self) -> int:
        return len(self.store.organizations)

    async def create(self, name: str) -> Organization:
        organization = create_organization(self.store, name=name)
        return organization

    async def find_by_id(self, organization_id: str) -> Organization | None:
        return self.store.organizations.get(organization_id)


class FakeUserRepository:
    def __init__(self, store: AgentTestStore) -> None:
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
    def __init__(self, store: AgentTestStore) -> None:
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
        now = datetime.now(UTC)
        agent = Agent(
            id=f"agt_{uuid4().hex}",
            organization_id=organization_id,
            name=name,
            hostname=hostname,
            os_type=os_type,
            agent_version=agent_version,
            status=AgentStatus.OFFLINE,
            api_key_hash=api_key_hash,
            last_seen_at=None,
            ip_address=ip_address,
            tags=tags or [],
            created_at=now,
            updated_at=now,
        )
        self.store.agents[agent.id] = agent
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
                "ip_address": ip_address,
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


@pytest.fixture(autouse=True)
def clear_settings_cache() -> Iterator[None]:
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


@pytest.fixture
def store() -> AgentTestStore:
    return AgentTestStore()


@pytest.fixture
def client(store: AgentTestStore) -> Iterator[TestClient]:
    app.dependency_overrides[get_user_repository] = lambda: FakeUserRepository(store)
    app.dependency_overrides[get_organization_repository] = (
        lambda: FakeOrganizationRepository(store)
    )
    app.dependency_overrides[get_agent_repository] = lambda: FakeAgentRepository(store)
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


def create_organization(store: AgentTestStore, *, name: str) -> Organization:
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
    store: AgentTestStore,
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


def register_org_admin(client: TestClient) -> dict:
    response = client.post(
        "/api/auth/register",
        json={
            "email": "admin@example.com",
            "password": "password123",
            "display_name": "Admin User",
            "organization_name": "Acme Security",
        },
    )
    assert response.status_code == 201
    return response.json()


def register_agent(client: TestClient, access_token: str, *, name: str = "workstation-1") -> dict:
    response = client.post(
        "/api/agents/register",
        headers={"Authorization": f"Bearer {access_token}"},
        json={
            "name": name,
            "hostname": f"{name}.local",
            "os_type": "linux",
            "agent_version": "1.0.0",
            "tags": ["lab", "endpoint"],
        },
    )
    assert response.status_code == 201
    return response.json()


def test_register_agent_success(client: TestClient, store: AgentTestStore) -> None:
    admin = register_org_admin(client)
    body = register_agent(client, admin["access_token"])

    assert body["api_key"].startswith("sxag_")
    assert body["agent"]["organization_id"] == admin["organization"]["id"]
    assert body["agent"]["status"] == "offline"
    assert body["agent"]["os_type"] == "linux"
    assert "api_key_hash" not in body["agent"]

    stored_agent = store.agents[body["agent"]["id"]]
    assert stored_agent.api_key_hash != body["api_key"]


def test_api_key_returned_only_on_register(client: TestClient) -> None:
    admin = register_org_admin(client)
    registered_agent = register_agent(client, admin["access_token"])

    list_response = client.get(
        "/api/agents",
        headers={"Authorization": f"Bearer {admin['access_token']}"},
    )
    detail_response = client.get(
        f"/api/agents/{registered_agent['agent']['id']}",
        headers={"Authorization": f"Bearer {admin['access_token']}"},
    )

    assert "api_key" not in list_response.json()["agents"][0]
    assert "api_key_hash" not in list_response.json()["agents"][0]
    assert "api_key" not in detail_response.json()
    assert "api_key_hash" not in detail_response.json()


def test_list_agents_organization_scoped(client: TestClient, store: AgentTestStore) -> None:
    admin = register_org_admin(client)
    register_agent(client, admin["access_token"], name="org-one-agent")

    other_org = create_organization(store, name="Other Org")
    _, other_token = create_user(
        store,
        organization_id=other_org.id,
        role=Role.ORG_ADMIN,
        email="other-admin@example.com",
    )
    register_agent(client, other_token, name="org-two-agent")

    response = client.get(
        "/api/agents",
        headers={"Authorization": f"Bearer {admin['access_token']}"},
    )

    assert response.status_code == 200
    agents = response.json()["agents"]
    assert len(agents) == 1
    assert agents[0]["name"] == "org-one-agent"


def test_get_agent_by_id(client: TestClient) -> None:
    admin = register_org_admin(client)
    registered_agent = register_agent(client, admin["access_token"])

    response = client.get(
        f"/api/agents/{registered_agent['agent']['id']}",
        headers={"Authorization": f"Bearer {admin['access_token']}"},
    )

    assert response.status_code == 200
    assert response.json()["id"] == registered_agent["agent"]["id"]


def test_cross_org_access_blocked(client: TestClient, store: AgentTestStore) -> None:
    admin = register_org_admin(client)
    registered_agent = register_agent(client, admin["access_token"])

    other_org = create_organization(store, name="Other Org")
    _, other_token = create_user(
        store,
        organization_id=other_org.id,
        role=Role.ORG_ADMIN,
        email="other-admin@example.com",
    )

    response = client.get(
        f"/api/agents/{registered_agent['agent']['id']}",
        headers={"Authorization": f"Bearer {other_token}"},
    )

    assert response.status_code == 404


def test_heartbeat_success_with_valid_key(client: TestClient, store: AgentTestStore) -> None:
    admin = register_org_admin(client)
    registered_agent = register_agent(client, admin["access_token"])

    response = client.post(
        "/api/agents/heartbeat",
        headers={"X-Agent-Key": registered_agent["api_key"]},
        json={"agent_version": "1.0.1", "ip_address": "10.0.0.5"},
    )

    assert response.status_code == 200
    assert response.json()["status"] == "ok"

    stored_agent = store.agents[registered_agent["agent"]["id"]]
    assert stored_agent.status == AgentStatus.ONLINE
    assert stored_agent.agent_version == "1.0.1"
    assert stored_agent.ip_address == "10.0.0.5"
    assert stored_agent.last_seen_at is not None


def test_heartbeat_fails_with_invalid_key(client: TestClient) -> None:
    response = client.post(
        "/api/agents/heartbeat",
        headers={"X-Agent-Key": "invalid-key"},
        json={},
    )

    assert response.status_code == 401


def test_disabled_agent_heartbeat_blocked(client: TestClient) -> None:
    admin = register_org_admin(client)
    registered_agent = register_agent(client, admin["access_token"])
    disable_response = client.post(
        f"/api/agents/{registered_agent['agent']['id']}/disable",
        headers={"Authorization": f"Bearer {admin['access_token']}"},
    )
    assert disable_response.status_code == 200

    heartbeat_response = client.post(
        "/api/agents/heartbeat",
        headers={"X-Agent-Key": registered_agent["api_key"]},
        json={},
    )

    assert heartbeat_response.status_code == 403


def test_viewer_can_list_read_but_cannot_register_disable(client: TestClient) -> None:
    admin = register_org_admin(client)
    registered_agent = register_agent(client, admin["access_token"])
    viewer = client.post(
        "/api/auth/register",
        json={
            "email": "viewer@example.com",
            "password": "password123",
            "display_name": "Viewer User",
            "organization_id": admin["organization"]["id"],
        },
    ).json()

    list_response = client.get(
        "/api/agents",
        headers={"Authorization": f"Bearer {viewer['access_token']}"},
    )
    detail_response = client.get(
        f"/api/agents/{registered_agent['agent']['id']}",
        headers={"Authorization": f"Bearer {viewer['access_token']}"},
    )
    register_response = client.post(
        "/api/agents/register",
        headers={"Authorization": f"Bearer {viewer['access_token']}"},
        json={
            "name": "not-allowed",
            "hostname": "not-allowed.local",
            "os_type": "linux",
        },
    )
    disable_response = client.post(
        f"/api/agents/{registered_agent['agent']['id']}/disable",
        headers={"Authorization": f"Bearer {viewer['access_token']}"},
    )

    assert list_response.status_code == 200
    assert detail_response.status_code == 200
    assert register_response.status_code == 403
    assert disable_response.status_code == 403


def test_org_admin_can_disable(client: TestClient) -> None:
    admin = register_org_admin(client)
    registered_agent = register_agent(client, admin["access_token"])

    response = client.post(
        f"/api/agents/{registered_agent['agent']['id']}/disable",
        headers={"Authorization": f"Bearer {admin['access_token']}"},
    )

    assert response.status_code == 200
    assert response.json()["agent"]["status"] == "disabled"
