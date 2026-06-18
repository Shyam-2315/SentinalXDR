from collections.abc import Iterator
from datetime import UTC, datetime
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from app.api.dependencies import (
    get_agent_repository,
    get_alert_repository,
    get_audit_repository,
    get_audit_service,
    get_incident_repository,
    get_organization_repository,
    get_user_repository,
)
from app.core.config import get_settings
from app.core.security import create_token, hash_password
from app.main import app
from app.models.agent import Agent, AgentStatus, OSType
from app.models.alert import Alert, AlertStatus
from app.models.audit_log import AuditLog, AuditStatus
from app.models.auth import Role, UserStatus
from app.models.event import EventSeverity
from app.models.incident import Incident, IncidentStatus
from app.models.organization import Organization
from app.models.user import User
from app.services.audit_service import AuditService


class AuditTestStore:
    def __init__(self) -> None:
        self.users: dict[str, User] = {}
        self.organizations: dict[str, Organization] = {}
        self.agents: dict[str, Agent] = {}
        self.alerts: dict[str, Alert] = {}
        self.incidents: dict[str, Incident] = {}
        self.audit_logs: dict[str, AuditLog] = {}


class FakeOrganizationRepository:
    def __init__(self, store: AuditTestStore) -> None:
        self.store = store

    async def count(self) -> int:
        return len(self.store.organizations)

    async def create(self, name: str) -> Organization:
        organization = create_organization(self.store, name=name)
        return organization

    async def find_by_id(self, organization_id: str) -> Organization | None:
        return self.store.organizations.get(organization_id)


class FakeUserRepository:
    def __init__(self, store: AuditTestStore) -> None:
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
        user = create_user(
            self.store,
            organization_id=organization_id,
            role=role,
            email=email,
            hashed_password=hashed_password,
            display_name=display_name,
            status=status,
        )
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
    def __init__(self, store: AuditTestStore) -> None:
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
            ip_address=ip_address,
            tags=tags or [],
            created_at=now,
            updated_at=now,
        )
        self.store.agents[agent.id] = agent
        return agent

    async def find_by_api_key(self, api_key: str) -> Agent | None:
        return None


class FakeAlertRepository:
    def __init__(self, store: AuditTestStore) -> None:
        self.store = store

    async def update_status(
        self,
        *,
        alert_id: str,
        organization_id: str,
        status: AlertStatus,
    ) -> Alert | None:
        alert = self.store.alerts.get(alert_id)
        if alert is None or alert.organization_id != organization_id:
            return None
        updated = alert.model_copy(update={"status": status, "updated_at": datetime.now(UTC)})
        self.store.alerts[updated.id] = updated
        return updated


class FakeIncidentRepository:
    def __init__(self, store: AuditTestStore) -> None:
        self.store = store

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

    async def update_assignment(
        self,
        *,
        incident_id: str,
        organization_id: str,
        assigned_to_user_id: str | None,
    ) -> Incident | None:
        incident = await self.find_by_id_for_organization(
            incident_id=incident_id,
            organization_id=organization_id,
        )
        if incident is None:
            return None
        updated = incident.model_copy(
            update={
                "assigned_to_user_id": assigned_to_user_id,
                "updated_at": datetime.now(UTC),
            },
        )
        self.store.incidents[updated.id] = updated
        return updated


class FakeAuditLogRepository:
    def __init__(self, store: AuditTestStore) -> None:
        self.store = store

    async def create(self, audit_log: AuditLog) -> AuditLog:
        self.store.audit_logs[audit_log.id] = audit_log
        return audit_log

    async def list_for_organization(
        self,
        *,
        organization_id: str,
        action: str | None = None,
        resource_type: str | None = None,
        actor_user_id: str | None = None,
        status: AuditStatus | None = None,
        date_from: datetime | None = None,
        date_to: datetime | None = None,
        limit: int = 100,
        skip: int = 0,
    ) -> list[AuditLog]:
        logs = [
            audit_log
            for audit_log in self.store.audit_logs.values()
            if audit_log.organization_id == organization_id
            and (action is None or audit_log.action == action)
            and (resource_type is None or audit_log.resource_type == resource_type)
            and (actor_user_id is None or audit_log.actor_user_id == actor_user_id)
            and (status is None or audit_log.status == status)
            and (date_from is None or audit_log.created_at >= date_from)
            and (date_to is None or audit_log.created_at <= date_to)
        ]
        logs.sort(key=lambda audit_log: audit_log.created_at, reverse=True)
        return logs[skip : skip + limit]

    async def find_by_id_for_organization(
        self,
        *,
        audit_id: str,
        organization_id: str,
    ) -> AuditLog | None:
        audit_log = self.store.audit_logs.get(audit_id)
        if audit_log is None or audit_log.organization_id != organization_id:
            return None
        return audit_log


@pytest.fixture(autouse=True)
def clear_settings_cache() -> Iterator[None]:
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


@pytest.fixture
def store() -> AuditTestStore:
    return AuditTestStore()


@pytest.fixture
def client(store: AuditTestStore) -> Iterator[TestClient]:
    audit_repo = FakeAuditLogRepository(store)
    app.dependency_overrides[get_user_repository] = lambda: FakeUserRepository(store)
    app.dependency_overrides[get_organization_repository] = (
        lambda: FakeOrganizationRepository(store)
    )
    app.dependency_overrides[get_agent_repository] = lambda: FakeAgentRepository(store)
    app.dependency_overrides[get_alert_repository] = lambda: FakeAlertRepository(store)
    app.dependency_overrides[get_incident_repository] = lambda: FakeIncidentRepository(store)
    app.dependency_overrides[get_audit_repository] = lambda: audit_repo
    app.dependency_overrides[get_audit_service] = lambda: AuditService(
        audit_repo,  # type: ignore[arg-type]
    )
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


def create_organization(store: AuditTestStore, *, name: str) -> Organization:
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
    store: AuditTestStore,
    *,
    organization_id: str,
    role: Role,
    email: str,
    hashed_password: str | None = None,
    display_name: str | None = None,
    status: UserStatus = UserStatus.ACTIVE,
) -> User:
    now = datetime.now(UTC)
    user = User(
        id=f"usr_{uuid4().hex}",
        organization_id=organization_id,
        email=email.lower(),
        display_name=display_name or email.split("@")[0],
        role=role,
        status=status,
        hashed_password=hashed_password or hash_password("password123"),
        created_at=now,
        updated_at=now,
    )
    store.users[user.id] = user
    return user


def auth_headers(user: User) -> dict[str, str]:
    return {"Authorization": f"Bearer {create_token(user, 'access')}"}


def seed_principal(
    store: AuditTestStore,
    *,
    role: Role = Role.ORG_ADMIN,
    email: str = "admin@example.com",
) -> tuple[Organization, User]:
    organization = create_organization(store, name=f"{email} Org")
    user = create_user(store, organization_id=organization.id, role=role, email=email)
    return organization, user


def seed_alert(store: AuditTestStore, *, organization_id: str) -> Alert:
    now = datetime.now(UTC)
    alert = Alert(
        id=f"alr_{uuid4().hex}",
        organization_id=organization_id,
        agent_id=f"agt_{uuid4().hex}",
        event_id=f"evt_{uuid4().hex}",
        detection_result_id=f"det_{uuid4().hex}",
        title="Suspicious login",
        description="Multiple failed logins",
        severity=EventSeverity.HIGH,
        status=AlertStatus.OPEN,
        created_at=now,
        updated_at=now,
    )
    store.alerts[alert.id] = alert
    return alert


def seed_incident(store: AuditTestStore, *, organization_id: str) -> Incident:
    now = datetime.now(UTC)
    incident = Incident(
        id=f"inc_{uuid4().hex}",
        organization_id=organization_id,
        title="Credential access",
        description="Credential access incident",
        severity=EventSeverity.HIGH,
        status=IncidentStatus.OPEN,
        first_seen_at=now,
        last_seen_at=now,
        created_at=now,
        updated_at=now,
    )
    store.incidents[incident.id] = incident
    return incident


def seed_audit_log(
    store: AuditTestStore,
    *,
    organization_id: str,
    actor_user_id: str | None = None,
    action: str = "user.login",
) -> AuditLog:
    audit_log = AuditLog(
        id=f"aud_{uuid4().hex}",
        organization_id=organization_id,
        actor_user_id=actor_user_id,
        actor_email="admin@example.com",
        actor_role=Role.ORG_ADMIN.value,
        action=action,
        resource_type="user",
        resource_id=actor_user_id,
        status=AuditStatus.SUCCESS,
        description="Seeded audit log",
    )
    store.audit_logs[audit_log.id] = audit_log
    return audit_log


def latest_audit(store: AuditTestStore) -> AuditLog:
    return max(store.audit_logs.values(), key=lambda audit_log: audit_log.created_at)


def test_login_creates_audit_log(client: TestClient, store: AuditTestStore) -> None:
    _, user = seed_principal(store, email="login@example.com")

    response = client.post(
        "/api/auth/login",
        json={"email": user.email, "password": "password123"},
    )

    assert response.status_code == 200
    audit_log = latest_audit(store)
    assert audit_log.action == "user.login"
    assert audit_log.status == AuditStatus.SUCCESS
    assert audit_log.actor_user_id == user.id


def test_failed_login_creates_failure_audit_log(
    client: TestClient,
    store: AuditTestStore,
) -> None:
    _, user = seed_principal(store, email="failed-login@example.com")

    response = client.post(
        "/api/auth/login",
        json={"email": user.email, "password": "wrong-password"},
    )

    assert response.status_code == 401
    audit_log = latest_audit(store)
    assert audit_log.action == "user.login"
    assert audit_log.status == AuditStatus.FAILURE
    assert audit_log.actor_email == user.email
    assert audit_log.metadata["reason"] == "invalid_credentials"


def test_agent_register_creates_audit_log(
    client: TestClient,
    store: AuditTestStore,
) -> None:
    _, user = seed_principal(store)

    response = client.post(
        "/api/agents/register",
        headers=auth_headers(user),
        json={
            "name": "workstation-1",
            "hostname": "workstation-1.local",
            "os_type": "linux",
            "agent_version": "1.0.0",
        },
    )

    assert response.status_code == 201
    audit_log = latest_audit(store)
    assert audit_log.action == "agent.register"
    assert audit_log.resource_type == "agent"
    assert "api_key" not in audit_log.metadata


def test_alert_status_update_creates_audit_log(
    client: TestClient,
    store: AuditTestStore,
) -> None:
    organization, user = seed_principal(store)
    alert = seed_alert(store, organization_id=organization.id)

    response = client.patch(
        f"/api/alerts/{alert.id}/status",
        headers=auth_headers(user),
        json={"status": "investigating"},
    )

    assert response.status_code == 200
    audit_log = latest_audit(store)
    assert audit_log.action == "alert.status_update"
    assert audit_log.resource_id == alert.id
    assert audit_log.metadata["status"] == "investigating"


def test_incident_assignment_creates_audit_log(
    client: TestClient,
    store: AuditTestStore,
) -> None:
    organization, user = seed_principal(store)
    assignee = create_user(
        store,
        organization_id=organization.id,
        role=Role.ANALYST,
        email="assignee@example.com",
    )
    incident = seed_incident(store, organization_id=organization.id)

    response = client.patch(
        f"/api/incidents/{incident.id}/assign",
        headers=auth_headers(user),
        json={"assigned_to_user_id": assignee.id},
    )

    assert response.status_code == 200
    audit_log = latest_audit(store)
    assert audit_log.action == "incident.assign"
    assert audit_log.resource_id == incident.id
    assert audit_log.metadata["assigned_to_user_id"] == assignee.id


def test_analyst_cannot_list_audit_logs(
    client: TestClient,
    store: AuditTestStore,
) -> None:
    organization, user = seed_principal(store, role=Role.ANALYST, email="analyst@example.com")
    seed_audit_log(store, organization_id=organization.id, actor_user_id=user.id)

    response = client.get("/api/audit", headers=auth_headers(user))

    assert response.status_code == 403


def test_org_admin_can_list_audit_logs(
    client: TestClient,
    store: AuditTestStore,
) -> None:
    organization, user = seed_principal(store)
    seed_audit_log(store, organization_id=organization.id, actor_user_id=user.id)

    response = client.get("/api/audit", headers=auth_headers(user))

    assert response.status_code == 200
    body = response.json()
    assert body["count"] == 1
    assert body["audit_logs"][0]["action"] == "user.login"


def test_cross_org_audit_access_blocked(
    client: TestClient,
    store: AuditTestStore,
) -> None:
    organization, user = seed_principal(store, email="one@example.com")
    _, other_user = seed_principal(store, email="two@example.com")
    audit_log = seed_audit_log(store, organization_id=organization.id, actor_user_id=user.id)

    response = client.get(f"/api/audit/{audit_log.id}", headers=auth_headers(other_user))

    assert response.status_code == 404


def test_sensitive_metadata_fields_are_redacted(store: AuditTestStore) -> None:
    import asyncio

    repository = FakeAuditLogRepository(store)
    service = AuditService(repository)  # type: ignore[arg-type]

    asyncio.run(
        service.log(
            action="user.login",
            resource_type="user",
            status=AuditStatus.SUCCESS,
            description="Sensitive metadata test",
            metadata={
                "password": "secret",
                "access_token": "token",
                "nested": {"refresh_token": "refresh", "agent_key": "agent"},
                "safe": "value",
            },
        )
    )

    audit_log = latest_audit(store)
    assert audit_log.metadata["password"] == "[REDACTED]"
    assert audit_log.metadata["access_token"] == "[REDACTED]"
    assert audit_log.metadata["nested"]["refresh_token"] == "[REDACTED]"
    assert audit_log.metadata["nested"]["agent_key"] == "[REDACTED]"
    assert audit_log.metadata["safe"] == "value"
