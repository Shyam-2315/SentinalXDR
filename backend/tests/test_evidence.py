from collections.abc import Iterator
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from app.api.dependencies import (
    get_audit_repository,
    get_audit_service,
    get_evidence_custody_repository,
    get_evidence_repository,
    get_incident_repository,
    get_organization_repository,
    get_user_repository,
)
from app.core.config import get_settings
from app.core.security import create_token, hash_password
from app.main import app
from app.models.audit_log import AuditLog
from app.models.auth import Role, UserStatus
from app.models.event import EventSeverity
from app.models.evidence import (
    Evidence,
    EvidenceCustodyEvent,
    EvidenceStatus,
    EvidenceVerificationStatus,
)
from app.models.incident import Incident, IncidentStatus
from app.models.organization import Organization
from app.models.user import User
from app.services.audit_service import AuditService


class EvidenceTestStore:
    def __init__(self) -> None:
        self.users: dict[str, User] = {}
        self.organizations: dict[str, Organization] = {}
        self.incidents: dict[str, Incident] = {}
        self.evidence: dict[str, Evidence] = {}
        self.custody: list[EvidenceCustodyEvent] = []
        self.audit_logs: dict[str, AuditLog] = {}


class FakeOrganizationRepository:
    def __init__(self, store: EvidenceTestStore) -> None:
        self.store = store

    async def count(self) -> int:
        return len(self.store.organizations)

    async def create(self, name: str) -> Organization:
        return create_organization(self.store, name=name)

    async def find_by_id(self, organization_id: str) -> Organization | None:
        return self.store.organizations.get(organization_id)


class FakeUserRepository:
    def __init__(self, store: EvidenceTestStore) -> None:
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
        return create_user(
            self.store,
            organization_id=organization_id,
            role=role,
            email=email,
            display_name=display_name,
            hashed_password=hashed_password,
            status=status,
        )

    async def find_by_email(self, email: str) -> User | None:
        return next(
            (user for user in self.store.users.values() if user.email == email.lower()),
            None,
        )

    async def find_by_id(self, user_id: str) -> User | None:
        return self.store.users.get(user_id)


class FakeIncidentRepository:
    def __init__(self, store: EvidenceTestStore) -> None:
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


class FakeEvidenceRepository:
    def __init__(self, store: EvidenceTestStore) -> None:
        self.store = store

    async def create(self, evidence: Evidence) -> Evidence:
        self.store.evidence[evidence.id] = evidence
        return evidence

    async def list_by_organization(
        self,
        *,
        organization_id: str,
        incident_id: str | None = None,
        status: EvidenceStatus | None = None,
        verification_status: EvidenceVerificationStatus | None = None,
        tag: str | None = None,
        limit: int = 100,
        skip: int = 0,
    ) -> list[Evidence]:
        rows = [
            item
            for item in self.store.evidence.values()
            if item.organization_id == organization_id
            and (incident_id is None or item.incident_id == incident_id)
            and (status is None or item.status == status)
            and (verification_status is None or item.verification_status == verification_status)
            and (tag is None or tag in item.tags)
        ]
        rows.sort(key=lambda item: item.created_at, reverse=True)
        return rows[skip : skip + limit]

    async def count_by_organization(
        self,
        *,
        organization_id: str,
        incident_id: str | None = None,
        status: EvidenceStatus | None = None,
        verification_status: EvidenceVerificationStatus | None = None,
        tag: str | None = None,
    ) -> int:
        return len(
            await self.list_by_organization(
                organization_id=organization_id,
                incident_id=incident_id,
                status=status,
                verification_status=verification_status,
                tag=tag,
            ),
        )

    async def find_by_id_for_organization(
        self,
        *,
        evidence_id: str,
        organization_id: str,
    ) -> Evidence | None:
        evidence = self.store.evidence.get(evidence_id)
        if evidence is None or evidence.organization_id != organization_id:
            return None
        return evidence

    async def set_incident(
        self,
        *,
        evidence_id: str,
        organization_id: str,
        incident_id: str | None,
    ) -> Evidence | None:
        return await self._set(evidence_id, organization_id, incident_id=incident_id)

    async def set_status(
        self,
        *,
        evidence_id: str,
        organization_id: str,
        status: EvidenceStatus,
    ) -> Evidence | None:
        return await self._set(evidence_id, organization_id, status=status)

    async def set_verification(
        self,
        *,
        evidence_id: str,
        organization_id: str,
        verification_status: EvidenceVerificationStatus,
        last_verified_at: datetime,
    ) -> Evidence | None:
        return await self._set(
            evidence_id,
            organization_id,
            verification_status=verification_status,
            last_verified_at=last_verified_at,
        )

    async def _set(
        self,
        evidence_id: str,
        organization_id: str,
        **fields: object,
    ) -> Evidence | None:
        evidence = await self.find_by_id_for_organization(
            evidence_id=evidence_id,
            organization_id=organization_id,
        )
        if evidence is None:
            return None
        updated = evidence.model_copy(update={**fields, "updated_at": datetime.now(UTC)})
        self.store.evidence[updated.id] = updated
        return updated


class FakeEvidenceCustodyRepository:
    def __init__(self, store: EvidenceTestStore) -> None:
        self.store = store

    async def create(self, event: EvidenceCustodyEvent) -> EvidenceCustodyEvent:
        self.store.custody.append(event)
        return event

    async def list_for_evidence(
        self,
        *,
        organization_id: str,
        evidence_id: str,
        limit: int = 500,
        skip: int = 0,
        newest_first: bool = False,
    ) -> list[EvidenceCustodyEvent]:
        rows = [
            event
            for event in self.store.custody
            if event.organization_id == organization_id and event.evidence_id == evidence_id
        ]
        rows.sort(key=lambda event: event.created_at, reverse=newest_first)
        return rows[skip : skip + limit]


class FakeAuditLogRepository:
    def __init__(self, store: EvidenceTestStore) -> None:
        self.store = store

    async def create(self, audit_log: AuditLog) -> AuditLog:
        self.store.audit_logs[audit_log.id] = audit_log
        return audit_log


@pytest.fixture(autouse=True)
def clear_settings_cache() -> Iterator[None]:
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


@pytest.fixture
def store() -> EvidenceTestStore:
    return EvidenceTestStore()


@pytest.fixture
def client(
    store: EvidenceTestStore,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> Iterator[TestClient]:
    monkeypatch.setenv("EVIDENCE_STORAGE_ROOT", str(tmp_path / "evidence"))
    get_settings.cache_clear()
    audit_repo = FakeAuditLogRepository(store)
    app.dependency_overrides[get_user_repository] = lambda: FakeUserRepository(store)
    app.dependency_overrides[get_organization_repository] = (
        lambda: FakeOrganizationRepository(store)
    )
    app.dependency_overrides[get_incident_repository] = lambda: FakeIncidentRepository(store)
    app.dependency_overrides[get_evidence_repository] = lambda: FakeEvidenceRepository(store)
    app.dependency_overrides[get_evidence_custody_repository] = (
        lambda: FakeEvidenceCustodyRepository(store)
    )
    app.dependency_overrides[get_audit_repository] = lambda: audit_repo
    app.dependency_overrides[get_audit_service] = lambda: AuditService(audit_repo)
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


def create_organization(store: EvidenceTestStore, *, name: str) -> Organization:
    now = datetime.now(UTC)
    organization = Organization(id=f"org_{uuid4().hex}", name=name, created_at=now, updated_at=now)
    store.organizations[organization.id] = organization
    return organization


def create_user(
    store: EvidenceTestStore,
    *,
    organization_id: str,
    role: Role,
    email: str,
    display_name: str = "Test User",
    hashed_password: str | None = None,
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
        hashed_password=hashed_password or hash_password("Password123!"),
        created_at=now,
        updated_at=now,
    )
    store.users[user.id] = user
    return user


def create_incident(store: EvidenceTestStore, *, organization_id: str) -> Incident:
    now = datetime.now(UTC)
    incident = Incident(
        id=f"inc_{uuid4().hex}",
        organization_id=organization_id,
        title="Malware case",
        description="Case",
        severity=EventSeverity.HIGH,
        status=IncidentStatus.OPEN,
        first_seen_at=now,
        last_seen_at=now,
        created_at=now,
        updated_at=now,
    )
    store.incidents[incident.id] = incident
    return incident


def auth_headers(user: User) -> dict[str, str]:
    return {"Authorization": f"Bearer {create_token(user, 'access')}"}


def upload(
    client: TestClient,
    user: User,
    *,
    filename: str = "artifact.txt",
    content: bytes = b"forensic bytes",
    data: dict[str, str] | None = None,
) -> dict[str, object]:
    response = client.post(
        "/api/evidence",
        headers=auth_headers(user),
        data=data or {},
        files={"file": (filename, content, "text/plain")},
    )
    assert response.status_code == 201, response.text
    return response.json()


def test_upload_evidence_success(client: TestClient, store: EvidenceTestStore) -> None:
    org = create_organization(store, name="Acme")
    user = create_user(store, organization_id=org.id, role=Role.ANALYST, email="a@example.com")
    incident = create_incident(store, organization_id=org.id)

    body = upload(
        client,
        user,
        data={"incident_id": incident.id, "description": "memory dump", "tags": "host1, memory"},
    )

    assert body["incident_id"] == incident.id
    assert body["original_filename"] == "artifact.txt"
    assert body["size_bytes"] == len(b"forensic bytes")
    assert body["sha256"] == "1610d928f41c12d5ec5b015d2a3ad2ca0fff65734dc07bebd9029ca4040f9a33"
    assert "storage_path" not in body
    assert [event.action.value for event in store.custody] == ["uploaded", "linked_to_incident"]
    assert any(log.action == "evidence.upload" for log in store.audit_logs.values())


def test_viewer_cannot_upload(client: TestClient, store: EvidenceTestStore) -> None:
    org = create_organization(store, name="Acme")
    user = create_user(store, organization_id=org.id, role=Role.VIEWER, email="v@example.com")

    response = client.post(
        "/api/evidence",
        headers=auth_headers(user),
        files={"file": ("a.txt", b"x", "text/plain")},
    )

    assert response.status_code == 403


def test_list_evidence_org_scoped(client: TestClient, store: EvidenceTestStore) -> None:
    org1 = create_organization(store, name="One")
    org2 = create_organization(store, name="Two")
    user1 = create_user(store, organization_id=org1.id, role=Role.ANALYST, email="a1@example.com")
    user2 = create_user(store, organization_id=org2.id, role=Role.ANALYST, email="a2@example.com")
    own = upload(client, user1)
    upload(client, user2)

    response = client.get("/api/evidence", headers=auth_headers(user1))

    assert response.status_code == 200
    body = response.json()
    assert body["count"] == 1
    assert body["evidence"][0]["id"] == own["id"]


def test_get_evidence_cross_org_blocked(client: TestClient, store: EvidenceTestStore) -> None:
    org1 = create_organization(store, name="One")
    org2 = create_organization(store, name="Two")
    user1 = create_user(store, organization_id=org1.id, role=Role.ANALYST, email="a1@example.com")
    user2 = create_user(store, organization_id=org2.id, role=Role.ANALYST, email="a2@example.com")
    item = upload(client, user1)

    response = client.get(f"/api/evidence/{item['id']}", headers=auth_headers(user2))

    assert response.status_code == 404


def test_download_creates_custody_event(client: TestClient, store: EvidenceTestStore) -> None:
    org = create_organization(store, name="Acme")
    user = create_user(store, organization_id=org.id, role=Role.VIEWER, email="v@example.com")
    analyst = create_user(
        store,
        organization_id=org.id,
        role=Role.ANALYST,
        email="a@example.com",
    )
    item = upload(client, user=analyst)

    response = client.get(f"/api/evidence/{item['id']}/download", headers=auth_headers(user))

    assert response.status_code == 200
    assert response.content == b"forensic bytes"
    assert store.custody[-1].action.value == "downloaded"
    assert any(log.action == "evidence.download" for log in store.audit_logs.values())


def test_verify_success_updates_status(client: TestClient, store: EvidenceTestStore) -> None:
    org = create_organization(store, name="Acme")
    user = create_user(store, organization_id=org.id, role=Role.ANALYST, email="a@example.com")
    item = upload(client, user)

    response = client.post(f"/api/evidence/{item['id']}/verify", headers=auth_headers(user))

    assert response.status_code == 200
    body = response.json()
    assert body["matched"] is True
    assert body["evidence"]["verification_status"] == "verified"


def test_verify_fails_cleanly_if_file_modified_or_missing(
    client: TestClient,
    store: EvidenceTestStore,
    tmp_path: Path,
) -> None:
    org = create_organization(store, name="Acme")
    user = create_user(store, organization_id=org.id, role=Role.ANALYST, email="a@example.com")
    item = upload(client, user)
    evidence = store.evidence[str(item["id"])]
    (tmp_path / "evidence" / evidence.storage_path).write_bytes(b"tampered")

    modified = client.post(f"/api/evidence/{item['id']}/verify", headers=auth_headers(user))

    assert modified.status_code == 200
    assert modified.json()["matched"] is False
    assert modified.json()["evidence"]["verification_status"] == "failed"

    (tmp_path / "evidence" / evidence.storage_path).unlink()
    missing = client.post(f"/api/evidence/{item['id']}/verify", headers=auth_headers(user))

    assert missing.status_code == 200
    assert missing.json()["matched"] is False
    assert missing.json()["actual_sha256"] is None


def test_link_evidence_to_incident_same_org(client: TestClient, store: EvidenceTestStore) -> None:
    org = create_organization(store, name="Acme")
    user = create_user(store, organization_id=org.id, role=Role.ANALYST, email="a@example.com")
    incident = create_incident(store, organization_id=org.id)
    item = upload(client, user)

    response = client.patch(
        f"/api/evidence/{item['id']}/link",
        headers=auth_headers(user),
        json={"incident_id": incident.id},
    )

    assert response.status_code == 200
    assert response.json()["incident_id"] == incident.id
    assert store.custody[-1].action.value == "linked_to_incident"


def test_cross_org_incident_link_blocked(client: TestClient, store: EvidenceTestStore) -> None:
    org1 = create_organization(store, name="One")
    org2 = create_organization(store, name="Two")
    user = create_user(store, organization_id=org1.id, role=Role.ANALYST, email="a@example.com")
    other_incident = create_incident(store, organization_id=org2.id)
    item = upload(client, user)

    response = client.patch(
        f"/api/evidence/{item['id']}/link",
        headers=auth_headers(user),
        json={"incident_id": other_incident.id},
    )

    assert response.status_code == 404


def test_archive_restore_authorization(client: TestClient, store: EvidenceTestStore) -> None:
    org = create_organization(store, name="Acme")
    analyst = create_user(store, organization_id=org.id, role=Role.ANALYST, email="a@example.com")
    admin = create_user(store, organization_id=org.id, role=Role.ORG_ADMIN, email="o@example.com")
    item = upload(client, analyst)

    forbidden = client.post(f"/api/evidence/{item['id']}/archive", headers=auth_headers(analyst))
    archived = client.post(f"/api/evidence/{item['id']}/archive", headers=auth_headers(admin))
    restored = client.post(f"/api/evidence/{item['id']}/restore", headers=auth_headers(admin))

    assert forbidden.status_code == 403
    assert archived.status_code == 200
    assert archived.json()["status"] == "archived"
    assert restored.status_code == 200
    assert restored.json()["status"] == "active"


def test_custody_timeline_returned(client: TestClient, store: EvidenceTestStore) -> None:
    org = create_organization(store, name="Acme")
    user = create_user(store, organization_id=org.id, role=Role.ANALYST, email="a@example.com")
    item = upload(client, user)

    response = client.get(f"/api/evidence/{item['id']}/custody", headers=auth_headers(user))

    assert response.status_code == 200
    assert response.json()["custody"][0]["action"] == "uploaded"


def test_upload_size_limit_enforced(
    client: TestClient,
    store: EvidenceTestStore,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("EVIDENCE_MAX_UPLOAD_MB", "1")
    get_settings.cache_clear()
    org = create_organization(store, name="Acme")
    user = create_user(store, organization_id=org.id, role=Role.ANALYST, email="a@example.com")

    response = client.post(
        "/api/evidence",
        headers=auth_headers(user),
        files={"file": ("big.bin", b"x" * (1024 * 1024 + 1), "application/octet-stream")},
    )

    assert response.status_code == 413
    assert store.evidence == {}


def test_path_traversal_filename_sanitized(client: TestClient, store: EvidenceTestStore) -> None:
    org = create_organization(store, name="Acme")
    user = create_user(store, organization_id=org.id, role=Role.ANALYST, email="a@example.com")

    body = upload(client, user, filename="../../secret.txt")

    assert body["original_filename"] == "secret.txt"
    evidence = store.evidence[str(body["id"])]
    assert "/" not in evidence.filename
    assert ".." not in evidence.filename
