from collections.abc import Iterator
from datetime import UTC, datetime
from uuid import uuid4

import pytest
from fastapi import HTTPException, Request, Response

from app.api.routes.reports import (
    export_attack_chain_report,
    export_audit_csv,
    export_evidence_report,
    export_executive_summary,
    export_incident_report,
)
from app.core.config import get_settings
from app.core.security import hash_password
from app.models.alert import Alert, AlertStatus
from app.models.attack_chain import AttackChain, AttackChainStatus, TimelineNode, TimelineNodeType
from app.models.audit_log import AuditLog, AuditStatus
from app.models.auth import Role, UserStatus
from app.models.event import EventSeverity
from app.models.evidence import Evidence, EvidenceCustodyAction, EvidenceCustodyEvent
from app.models.incident import Incident, IncidentStatus
from app.models.organization import Organization
from app.models.user import User
from app.services.audit_service import AuditService
from app.services.report_service import ReportService


class ReportTestStore:
    def __init__(self) -> None:
        self.users: dict[str, User] = {}
        self.organizations: dict[str, Organization] = {}
        self.alerts: dict[str, Alert] = {}
        self.incidents: dict[str, Incident] = {}
        self.attack_chains: dict[str, AttackChain] = {}
        self.evidence: dict[str, Evidence] = {}
        self.custody: list[EvidenceCustodyEvent] = []
        self.audit_logs: dict[str, AuditLog] = {}


class FakeOrganizationRepository:
    def __init__(self, store: ReportTestStore) -> None:
        self.store = store

    async def count(self) -> int:
        return len(self.store.organizations)

    async def create(self, name: str) -> Organization:
        organization = create_organization(self.store, name=name)
        return organization

    async def find_by_id(self, organization_id: str) -> Organization | None:
        return self.store.organizations.get(organization_id)


class FakeUserRepository:
    def __init__(self, store: ReportTestStore) -> None:
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
            display_name=display_name,
            hashed_password=hashed_password,
            status=status,
        )
        return user

    async def find_by_email(self, email: str) -> User | None:
        return next(
            (user for user in self.store.users.values() if user.email == email.lower()),
            None,
        )

    async def find_by_id(self, user_id: str) -> User | None:
        return self.store.users.get(user_id)


class FakeAlertRepository:
    def __init__(self, store: ReportTestStore) -> None:
        self.store = store

    async def list_by_organization(
        self,
        *,
        organization_id: str,
        limit: int = 100,
        skip: int = 0,
    ) -> list[Alert]:
        rows = [
            item
            for item in self.store.alerts.values()
            if item.organization_id == organization_id
        ]
        rows.sort(key=lambda item: item.created_at, reverse=True)
        return rows[skip : skip + limit]

    async def find_many_by_ids_for_organization(
        self,
        *,
        alert_ids: list[str],
        organization_id: str,
    ) -> list[Alert]:
        return [
            item
            for item in self.store.alerts.values()
            if item.id in alert_ids and item.organization_id == organization_id
        ]


class FakeIncidentRepository:
    def __init__(self, store: ReportTestStore) -> None:
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
        rows = [
            item
            for item in self.store.incidents.values()
            if item.organization_id == organization_id
            and (status is None or item.status == status)
            and (severity is None or item.severity == severity)
            and (agent_id is None or agent_id in item.agent_ids)
            and (mitre_technique is None or mitre_technique in item.mitre_techniques)
        ]
        rows.sort(key=lambda item: item.updated_at, reverse=True)
        return rows[skip : skip + limit]

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


class FakeAttackChainRepository:
    def __init__(self, store: ReportTestStore) -> None:
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
        rows = [
            item
            for item in self.store.attack_chains.values()
            if item.organization_id == organization_id
            and (status is None or item.status == status)
            and (severity is None or item.severity == severity)
            and (agent_id is None or agent_id in item.agent_ids)
            and (mitre_technique is None or mitre_technique in item.mitre_techniques)
            and (min_risk_score is None or item.risk_score >= min_risk_score)
        ]
        rows.sort(key=lambda item: item.updated_at, reverse=True)
        return rows[skip : skip + limit]

    async def find_by_id_for_organization(
        self,
        *,
        chain_id: str,
        organization_id: str,
    ) -> AttackChain | None:
        chain = self.store.attack_chains.get(chain_id)
        if chain is None or chain.organization_id != organization_id:
            return None
        return chain

    async def find_by_incident_for_organization(
        self,
        *,
        incident_id: str,
        organization_id: str,
    ) -> AttackChain | None:
        return next(
            (
                item
                for item in self.store.attack_chains.values()
                if item.incident_id == incident_id and item.organization_id == organization_id
            ),
            None,
        )


class FakeEvidenceRepository:
    def __init__(self, store: ReportTestStore) -> None:
        self.store = store

    async def list_by_organization(
        self,
        *,
        organization_id: str,
        incident_id: str | None = None,
        status: object | None = None,
        verification_status: object | None = None,
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


class FakeEvidenceCustodyRepository:
    def __init__(self, store: ReportTestStore) -> None:
        self.store = store

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
            item
            for item in self.store.custody
            if item.organization_id == organization_id and item.evidence_id == evidence_id
        ]
        rows.sort(key=lambda item: item.created_at, reverse=newest_first)
        return rows[skip : skip + limit]


class FakeAuditLogRepository:
    def __init__(self, store: ReportTestStore) -> None:
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
        rows = [
            item
            for item in self.store.audit_logs.values()
            if item.organization_id == organization_id
            and (action is None or item.action == action)
            and (resource_type is None or item.resource_type == resource_type)
            and (actor_user_id is None or item.actor_user_id == actor_user_id)
            and (status is None or item.status == status)
            and (date_from is None or item.created_at >= date_from)
            and (date_to is None or item.created_at <= date_to)
        ]
        rows.sort(key=lambda item: item.created_at, reverse=True)
        return rows[skip : skip + limit]

    async def list_for_resource(
        self,
        *,
        organization_id: str,
        resource_type: str,
        resource_id: str,
        limit: int = 100,
        skip: int = 0,
    ) -> list[AuditLog]:
        rows = [
            item
            for item in self.store.audit_logs.values()
            if item.organization_id == organization_id
            and item.resource_type == resource_type
            and item.resource_id == resource_id
        ]
        rows.sort(key=lambda item: item.created_at, reverse=True)
        return rows[skip : skip + limit]


@pytest.fixture(autouse=True)
def clear_settings_cache() -> Iterator[None]:
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


@pytest.fixture
def store() -> ReportTestStore:
    return ReportTestStore()


def create_organization(store: ReportTestStore, *, name: str) -> Organization:
    now = datetime.now(UTC)
    organization = Organization(id=f"org_{uuid4().hex}", name=name, created_at=now, updated_at=now)
    store.organizations[organization.id] = organization
    return organization


def create_user(
    store: ReportTestStore,
    *,
    organization_id: str,
    role: Role,
    email: str,
    display_name: str | None = None,
    hashed_password: str | None = None,
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


def report_service(store: ReportTestStore) -> ReportService:
    return ReportService(
        organizations=FakeOrganizationRepository(store),  # type: ignore[arg-type]
        incidents=FakeIncidentRepository(store),  # type: ignore[arg-type]
        attack_chains=FakeAttackChainRepository(store),  # type: ignore[arg-type]
        evidence=FakeEvidenceRepository(store),  # type: ignore[arg-type]
        custody=FakeEvidenceCustodyRepository(store),  # type: ignore[arg-type]
        alerts=FakeAlertRepository(store),  # type: ignore[arg-type]
        audit_logs=FakeAuditLogRepository(store),  # type: ignore[arg-type]
    )


def audit_service(store: ReportTestStore) -> AuditService:
    return AuditService(FakeAuditLogRepository(store))  # type: ignore[arg-type]


def request() -> Request:
    return Request(
        {
            "type": "http",
            "method": "GET",
            "path": "/api/reports",
            "headers": [],
            "client": ("testclient", 50000),
        }
    )


def seed_case(
    store: ReportTestStore,
    *,
    organization_id: str,
) -> tuple[Incident, AttackChain, Evidence]:
    now = datetime.now(UTC)
    alert = Alert(
        id=f"alr_{uuid4().hex}",
        organization_id=organization_id,
        agent_id="agt_1",
        event_id="evt_1",
        detection_result_id="det_1",
        title="Credential dumping detected",
        description="Suspicious LSASS access",
        severity=EventSeverity.CRITICAL,
        status=AlertStatus.OPEN,
        mitre_tactics=["credential_access"],
        mitre_techniques=["T1003"],
        created_at=now,
        updated_at=now,
    )
    store.alerts[alert.id] = alert
    incident = Incident(
        id=f"inc_{uuid4().hex}",
        organization_id=organization_id,
        title="Credential access incident",
        description="Credential dumping on endpoint",
        severity=EventSeverity.CRITICAL,
        status=IncidentStatus.OPEN,
        alert_ids=[alert.id],
        event_ids=[alert.event_id],
        agent_ids=[alert.agent_id],
        mitre_tactics=["credential_access"],
        mitre_techniques=["T1003"],
        first_seen_at=now,
        last_seen_at=now,
        created_at=now,
        updated_at=now,
    )
    store.incidents[incident.id] = incident
    chain = AttackChain(
        id=f"chn_{uuid4().hex}",
        organization_id=organization_id,
        incident_id=incident.id,
        agent_ids=[alert.agent_id],
        alert_ids=[alert.id],
        event_ids=[alert.event_id],
        title="Credential theft chain",
        summary="Credential theft activity",
        severity=EventSeverity.CRITICAL,
        risk_score=91.5,
        confidence_score=88.0,
        kill_chain_phases=["execution", "credential_access"],
        mitre_tactics=["credential_access"],
        mitre_techniques=["T1003"],
        timeline=[
            TimelineNode(
                timestamp=now,
                type=TimelineNodeType.ALERT,
                title=alert.title,
                description=alert.description,
                severity=alert.severity,
                mitre_tactic="credential_access",
                mitre_technique="T1003",
                reference_id=alert.id,
                source="alert",
            )
        ],
        story="Attacker accessed credential material.",
        recommended_actions=["Isolate host", "Reset affected credentials"],
        status=AttackChainStatus.ACTIVE,
        first_seen_at=now,
        last_seen_at=now,
        created_at=now,
        updated_at=now,
    )
    store.attack_chains[chain.id] = chain
    evidence = Evidence(
        id=f"evd_{uuid4().hex}",
        organization_id=organization_id,
        incident_id=incident.id,
        uploaded_by_user_id="usr_seed",
        uploaded_by_email="analyst@example.com",
        filename="artifact.bin",
        original_filename="memory.bin",
        content_type="application/octet-stream",
        size_bytes=128,
        sha256="a" * 64,
        storage_path="artifact.bin",
        description="Memory artifact",
        tags=["memory"],
        created_at=now,
        updated_at=now,
    )
    store.evidence[evidence.id] = evidence
    store.custody.append(
        EvidenceCustodyEvent(
            id=f"esc_{uuid4().hex}",
            organization_id=organization_id,
            evidence_id=evidence.id,
            actor_email="analyst@example.com",
            action=EvidenceCustodyAction.UPLOADED,
            description="Evidence uploaded",
            created_at=now,
        )
    )
    store.audit_logs[f"aud_{uuid4().hex}"] = AuditLog(
        id=f"aud_{uuid4().hex}",
        organization_id=organization_id,
        actor_email="analyst@example.com",
        actor_role=Role.ANALYST.value,
        action="incident.status_update",
        resource_type="incident",
        resource_id=incident.id,
        status=AuditStatus.SUCCESS,
        description="Seeded incident audit reference",
        created_at=now,
    )
    return incident, chain, evidence


def assert_pdf_response(response: Response) -> None:
    assert response.status_code == 200
    assert response.headers["content-type"] == "application/pdf"
    assert response.body.startswith(b"%PDF")
    assert "attachment;" in response.headers["content-disposition"]


@pytest.mark.asyncio
async def test_incident_report_export_works(
    store: ReportTestStore,
) -> None:
    org = create_organization(store, name="Acme SOC")
    user = create_user(store, organization_id=org.id, role=Role.VIEWER, email="viewer@example.com")
    incident, _, _ = seed_case(store, organization_id=org.id)

    response = await export_incident_report(
        incident.id,
        request(),
        user,
        report_service(store),
        audit_service(store),
    )

    assert_pdf_response(response)
    assert any(log.action == "report.incident_export" for log in store.audit_logs.values())


@pytest.mark.asyncio
async def test_attack_chain_report_export_works(
    store: ReportTestStore,
) -> None:
    org = create_organization(store, name="Acme SOC")
    user = create_user(store, organization_id=org.id, role=Role.ANALYST, email="a@example.com")
    _, chain, _ = seed_case(store, organization_id=org.id)

    response = await export_attack_chain_report(
        chain.id,
        request(),
        user,
        report_service(store),
        audit_service(store),
    )

    assert_pdf_response(response)
    assert any(log.action == "report.attack_chain_export" for log in store.audit_logs.values())


@pytest.mark.asyncio
async def test_evidence_report_export_works(
    store: ReportTestStore,
) -> None:
    org = create_organization(store, name="Acme SOC")
    user = create_user(store, organization_id=org.id, role=Role.ANALYST, email="a@example.com")
    _, _, evidence = seed_case(store, organization_id=org.id)

    response = await export_evidence_report(
        evidence.id,
        request(),
        user,
        report_service(store),
        audit_service(store),
    )

    assert_pdf_response(response)
    assert any(log.action == "report.evidence_export" for log in store.audit_logs.values())


@pytest.mark.asyncio
async def test_audit_csv_export_works(store: ReportTestStore) -> None:
    org = create_organization(store, name="Acme SOC")
    user = create_user(store, organization_id=org.id, role=Role.ANALYST, email="a@example.com")
    seed_case(store, organization_id=org.id)

    response = await export_audit_csv(request(), user, report_service(store), audit_service(store))

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/csv")
    csv_text = response.body.decode("utf-8")
    assert "id,organization_id,created_at" in csv_text
    assert "incident.status_update" in csv_text
    assert any(log.action == "report.audit_export" for log in store.audit_logs.values())


@pytest.mark.asyncio
async def test_report_export_cross_org_blocked(
    store: ReportTestStore,
) -> None:
    org_one = create_organization(store, name="One")
    org_two = create_organization(store, name="Two")
    user_two = create_user(
        store,
        organization_id=org_two.id,
        role=Role.ANALYST,
        email="two@example.com",
    )
    incident, _, _ = seed_case(store, organization_id=org_one.id)

    with pytest.raises(HTTPException) as exc_info:
        await export_incident_report(
            incident.id,
            request(),
            user_two,
            report_service(store),
            audit_service(store),
        )
    assert exc_info.value.status_code == 404


@pytest.mark.asyncio
async def test_executive_summary_export_creates_audit_log(
    store: ReportTestStore,
) -> None:
    org = create_organization(store, name="Acme SOC")
    user = create_user(store, organization_id=org.id, role=Role.ORG_ADMIN, email="o@example.com")
    seed_case(store, organization_id=org.id)

    response = await export_executive_summary(
        request(),
        user,
        report_service(store),
        audit_service(store),
    )

    assert_pdf_response(response)
    assert any(
        log.action == "report.executive_summary_export" for log in store.audit_logs.values()
    )
