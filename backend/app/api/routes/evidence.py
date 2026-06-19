from __future__ import annotations

import hashlib
import json
import re
from datetime import UTC, datetime
from pathlib import Path, PurePath
from typing import Annotated, Any
from uuid import uuid4

from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    HTTPException,
    Query,
    Request,
    UploadFile,
    status,
)
from fastapi.responses import FileResponse

from app.api.dependencies import (
    get_audit_service,
    get_evidence_custody_repository,
    get_evidence_repository,
    get_incident_repository,
    require_roles,
)
from app.core.config import get_settings
from app.models.auth import Role
from app.models.evidence import (
    Evidence,
    EvidenceCustodyAction,
    EvidenceCustodyEvent,
    EvidenceStatus,
    EvidenceVerificationStatus,
)
from app.models.user import User
from app.repositories.evidence import EvidenceCustodyRepository, EvidenceRepository
from app.repositories.incidents import IncidentRepository
from app.schemas.evidence import (
    EvidenceCustodyListResponse,
    EvidenceCustodyRead,
    EvidenceLinkRequest,
    EvidenceListResponse,
    EvidenceRead,
    EvidenceVerifyResponse,
)
from app.services.audit_service import AuditService

router = APIRouter(prefix="/evidence", tags=["evidence"])

READ_ROLES = (Role.SUPER_ADMIN, Role.ORG_ADMIN, Role.ANALYST, Role.VIEWER)
WRITE_ROLES = (Role.SUPER_ADMIN, Role.ORG_ADMIN, Role.ANALYST)
ADMIN_ROLES = (Role.SUPER_ADMIN, Role.ORG_ADMIN)
CHUNK_SIZE = 1024 * 1024


def to_evidence_read(evidence: Evidence) -> EvidenceRead:
    data = evidence.model_dump(exclude={"storage_path"})
    return EvidenceRead(**data)


def to_custody_read(event: EvidenceCustodyEvent) -> EvidenceCustodyRead:
    return EvidenceCustodyRead(**event.model_dump())


def sanitize_filename(filename: str | None) -> str:
    base = PurePath(filename or "evidence.bin").name
    base = base.replace("\x00", "")
    base = re.sub(r"[^A-Za-z0-9._-]+", "_", base).strip("._")
    return base[:180] or "evidence.bin"


def parse_tags(raw_tags: str | None) -> list[str]:
    if not raw_tags:
        return []
    raw_tags = raw_tags.strip()
    values: list[Any]
    if raw_tags.startswith("["):
        try:
            parsed = json.loads(raw_tags)
        except json.JSONDecodeError as exc:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid JSON tags",
            ) from exc
        if not isinstance(parsed, list):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Tags JSON must be a list",
            )
        values = parsed
    else:
        values = raw_tags.split(",")
    tags: list[str] = []
    for value in values:
        tag = str(value).strip()
        if tag and tag not in tags:
            tags.append(tag[:64])
    return tags


def storage_root() -> Path:
    root = Path(get_settings().evidence_storage_root).expanduser()
    root.mkdir(parents=True, exist_ok=True)
    return root.resolve()


def resolve_storage_path(relative_path: str) -> Path:
    root = storage_root()
    candidate = (root / relative_path).resolve()
    if root != candidate and root not in candidate.parents:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Evidence file not found")
    return candidate


async def custody_log(
    custody: EvidenceCustodyRepository,
    *,
    evidence: Evidence,
    action: EvidenceCustodyAction,
    description: str,
    current_user: User | None,
    metadata: dict[str, Any] | None = None,
) -> None:
    await custody.create(
        EvidenceCustodyEvent(
            id=f"esc_{uuid4().hex}",
            organization_id=evidence.organization_id,
            evidence_id=evidence.id,
            actor_user_id=current_user.id if current_user is not None else None,
            actor_email=str(current_user.email) if current_user is not None else None,
            action=action,
            description=description,
            metadata=metadata or {},
        ),
    )


async def get_evidence_or_404(
    evidence_id: str,
    current_user: User,
    evidence_repo: EvidenceRepository,
) -> Evidence:
    evidence = await evidence_repo.find_by_id_for_organization(
        evidence_id=evidence_id,
        organization_id=current_user.organization_id,
    )
    if evidence is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Evidence not found")
    return evidence


async def validate_incident(
    incident_id: str,
    current_user: User,
    incidents: IncidentRepository,
) -> None:
    incident = await incidents.find_by_id_for_organization(
        incident_id=incident_id,
        organization_id=current_user.organization_id,
    )
    if incident is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Incident not found")


async def sha256_for_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(CHUNK_SIZE), b""):
            digest.update(chunk)
    return digest.hexdigest()


@router.post("", response_model=EvidenceRead, status_code=status.HTTP_201_CREATED)
async def upload_evidence(
    request: Request,
    current_user: Annotated[User, Depends(require_roles(*WRITE_ROLES))],
    evidence_repo: Annotated[EvidenceRepository, Depends(get_evidence_repository)],
    custody: Annotated[EvidenceCustodyRepository, Depends(get_evidence_custody_repository)],
    incidents: Annotated[IncidentRepository, Depends(get_incident_repository)],
    audit: Annotated[AuditService, Depends(get_audit_service)],
    file: Annotated[UploadFile, File()],
    incident_id: Annotated[str | None, Form()] = None,
    description: Annotated[str | None, Form()] = None,
    tags: Annotated[str | None, Form()] = None,
) -> EvidenceRead:
    incident_id = incident_id.strip() if incident_id else None
    if incident_id:
        await validate_incident(incident_id, current_user, incidents)

    original_filename = sanitize_filename(file.filename)
    suffix = Path(original_filename).suffix[:32]
    generated_filename = f"evf_{uuid4().hex}{suffix}"
    path = storage_root() / generated_filename
    max_bytes = get_settings().evidence_max_upload_mb * 1024 * 1024
    digest = hashlib.sha256()
    size_bytes = 0

    try:
        with path.open("wb") as handle:
            while chunk := await file.read(CHUNK_SIZE):
                size_bytes += len(chunk)
                if size_bytes > max_bytes:
                    raise HTTPException(
                        status_code=status.HTTP_413_CONTENT_TOO_LARGE,
                        detail="Evidence file exceeds upload size limit",
                    )
                digest.update(chunk)
                handle.write(chunk)
    except Exception:
        path.unlink(missing_ok=True)
        raise
    finally:
        await file.close()

    now = datetime.now(UTC)
    evidence = Evidence(
        id=f"evd_{uuid4().hex}",
        organization_id=current_user.organization_id,
        incident_id=incident_id,
        uploaded_by_user_id=current_user.id,
        uploaded_by_email=str(current_user.email),
        filename=generated_filename,
        original_filename=original_filename,
        content_type=file.content_type or "application/octet-stream",
        size_bytes=size_bytes,
        sha256=digest.hexdigest(),
        storage_path=generated_filename,
        description=description,
        tags=parse_tags(tags),
        created_at=now,
        updated_at=now,
    )
    evidence = await evidence_repo.create(evidence)
    await custody_log(
        custody,
        evidence=evidence,
        action=EvidenceCustodyAction.UPLOADED,
        description="Evidence uploaded",
        current_user=current_user,
        metadata={
            "original_filename": evidence.original_filename,
            "size_bytes": evidence.size_bytes,
            "sha256": evidence.sha256,
        },
    )
    if incident_id is not None:
        await custody_log(
            custody,
            evidence=evidence,
            action=EvidenceCustodyAction.LINKED_TO_INCIDENT,
            description="Evidence linked to incident during upload",
            current_user=current_user,
            metadata={"incident_id": incident_id},
        )
    await audit.log(
        action="evidence.upload",
        resource_type="evidence",
        resource_id=evidence.id,
        description="Evidence uploaded",
        request=request,
        current_user=current_user,
        metadata={
            "incident_id": evidence.incident_id,
            "original_filename": evidence.original_filename,
            "size_bytes": evidence.size_bytes,
            "sha256": evidence.sha256,
            "tags": evidence.tags,
        },
    )
    return to_evidence_read(evidence)


@router.get("", response_model=EvidenceListResponse)
async def list_evidence(
    current_user: Annotated[User, Depends(require_roles(*READ_ROLES))],
    evidence_repo: Annotated[EvidenceRepository, Depends(get_evidence_repository)],
    incident_id: str | None = None,
    status_filter: Annotated[EvidenceStatus | None, Query(alias="status")] = None,
    verification_status: EvidenceVerificationStatus | None = None,
    tag: str | None = None,
    limit: int = Query(default=100, ge=1, le=500),
    skip: int = Query(default=0, ge=0),
) -> EvidenceListResponse:
    rows = await evidence_repo.list_by_organization(
        organization_id=current_user.organization_id,
        incident_id=incident_id,
        status=status_filter,
        verification_status=verification_status,
        tag=tag,
        limit=limit,
        skip=skip,
    )
    count = await evidence_repo.count_by_organization(
        organization_id=current_user.organization_id,
        incident_id=incident_id,
        status=status_filter,
        verification_status=verification_status,
        tag=tag,
    )
    return EvidenceListResponse(
        evidence=[to_evidence_read(item) for item in rows],
        count=count,
        limit=limit,
        skip=skip,
    )


@router.get("/{evidence_id}", response_model=EvidenceRead)
async def get_evidence(
    evidence_id: str,
    current_user: Annotated[User, Depends(require_roles(*READ_ROLES))],
    evidence_repo: Annotated[EvidenceRepository, Depends(get_evidence_repository)],
    custody: Annotated[EvidenceCustodyRepository, Depends(get_evidence_custody_repository)],
) -> EvidenceRead:
    evidence = await get_evidence_or_404(evidence_id, current_user, evidence_repo)
    await custody_log(
        custody,
        evidence=evidence,
        action=EvidenceCustodyAction.VIEWED,
        description="Evidence metadata viewed",
        current_user=current_user,
    )
    return to_evidence_read(evidence)


@router.get("/{evidence_id}/download")
async def download_evidence(
    evidence_id: str,
    request: Request,
    current_user: Annotated[User, Depends(require_roles(*READ_ROLES))],
    evidence_repo: Annotated[EvidenceRepository, Depends(get_evidence_repository)],
    custody: Annotated[EvidenceCustodyRepository, Depends(get_evidence_custody_repository)],
    audit: Annotated[AuditService, Depends(get_audit_service)],
) -> FileResponse:
    evidence = await get_evidence_or_404(evidence_id, current_user, evidence_repo)
    path = resolve_storage_path(evidence.storage_path)
    if not path.is_file():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Evidence file not found")
    await custody_log(
        custody,
        evidence=evidence,
        action=EvidenceCustodyAction.DOWNLOADED,
        description="Evidence downloaded",
        current_user=current_user,
        metadata={"original_filename": evidence.original_filename},
    )
    await audit.log(
        action="evidence.download",
        resource_type="evidence",
        resource_id=evidence.id,
        description="Evidence downloaded",
        request=request,
        current_user=current_user,
        metadata={
            "original_filename": evidence.original_filename,
            "size_bytes": evidence.size_bytes,
        },
    )
    return FileResponse(
        path=path,
        media_type=evidence.content_type,
        filename=evidence.original_filename,
    )


@router.post("/{evidence_id}/verify", response_model=EvidenceVerifyResponse)
async def verify_evidence(
    evidence_id: str,
    request: Request,
    current_user: Annotated[User, Depends(require_roles(*READ_ROLES))],
    evidence_repo: Annotated[EvidenceRepository, Depends(get_evidence_repository)],
    custody: Annotated[EvidenceCustodyRepository, Depends(get_evidence_custody_repository)],
    audit: Annotated[AuditService, Depends(get_audit_service)],
) -> EvidenceVerifyResponse:
    evidence = await get_evidence_or_404(evidence_id, current_user, evidence_repo)
    path = resolve_storage_path(evidence.storage_path)
    actual_sha256: str | None = None
    matched = False
    if path.is_file():
        actual_sha256 = await sha256_for_file(path)
        matched = actual_sha256 == evidence.sha256

    verification_status = (
        EvidenceVerificationStatus.VERIFIED
        if matched
        else EvidenceVerificationStatus.FAILED
    )
    updated = await evidence_repo.set_verification(
        evidence_id=evidence.id,
        organization_id=current_user.organization_id,
        verification_status=verification_status,
        last_verified_at=datetime.now(UTC),
    )
    if updated is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Evidence not found")
    await custody_log(
        custody,
        evidence=updated,
        action=EvidenceCustodyAction.VERIFIED,
        description="Evidence hash verification completed",
        current_user=current_user,
        metadata={
            "matched": matched,
            "expected_sha256": evidence.sha256,
            "actual_sha256": actual_sha256,
        },
    )
    await audit.log(
        action="evidence.verify",
        resource_type="evidence",
        resource_id=evidence.id,
        description="Evidence hash verification completed",
        request=request,
        current_user=current_user,
        metadata={"matched": matched, "verification_status": verification_status.value},
    )
    return EvidenceVerifyResponse(
        evidence=to_evidence_read(updated),
        expected_sha256=evidence.sha256,
        actual_sha256=actual_sha256,
        matched=matched,
    )


@router.patch("/{evidence_id}/link", response_model=EvidenceRead)
async def link_evidence(
    evidence_id: str,
    payload: EvidenceLinkRequest,
    request: Request,
    current_user: Annotated[User, Depends(require_roles(*WRITE_ROLES))],
    evidence_repo: Annotated[EvidenceRepository, Depends(get_evidence_repository)],
    custody: Annotated[EvidenceCustodyRepository, Depends(get_evidence_custody_repository)],
    incidents: Annotated[IncidentRepository, Depends(get_incident_repository)],
    audit: Annotated[AuditService, Depends(get_audit_service)],
) -> EvidenceRead:
    evidence = await get_evidence_or_404(evidence_id, current_user, evidence_repo)
    await validate_incident(payload.incident_id, current_user, incidents)
    updated = await evidence_repo.set_incident(
        evidence_id=evidence.id,
        organization_id=current_user.organization_id,
        incident_id=payload.incident_id,
    )
    if updated is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Evidence not found")
    await custody_log(
        custody,
        evidence=updated,
        action=EvidenceCustodyAction.LINKED_TO_INCIDENT,
        description="Evidence linked to incident",
        current_user=current_user,
        metadata={"previous_incident_id": evidence.incident_id, "incident_id": payload.incident_id},
    )
    await audit.log(
        action="evidence.link",
        resource_type="evidence",
        resource_id=evidence.id,
        description="Evidence linked to incident",
        request=request,
        current_user=current_user,
        metadata={"incident_id": payload.incident_id},
    )
    return to_evidence_read(updated)


@router.patch("/{evidence_id}/unlink", response_model=EvidenceRead)
async def unlink_evidence(
    evidence_id: str,
    request: Request,
    current_user: Annotated[User, Depends(require_roles(*WRITE_ROLES))],
    evidence_repo: Annotated[EvidenceRepository, Depends(get_evidence_repository)],
    custody: Annotated[EvidenceCustodyRepository, Depends(get_evidence_custody_repository)],
    audit: Annotated[AuditService, Depends(get_audit_service)],
) -> EvidenceRead:
    evidence = await get_evidence_or_404(evidence_id, current_user, evidence_repo)
    updated = await evidence_repo.set_incident(
        evidence_id=evidence.id,
        organization_id=current_user.organization_id,
        incident_id=None,
    )
    if updated is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Evidence not found")
    await custody_log(
        custody,
        evidence=updated,
        action=EvidenceCustodyAction.UNLINKED_FROM_INCIDENT,
        description="Evidence unlinked from incident",
        current_user=current_user,
        metadata={"previous_incident_id": evidence.incident_id},
    )
    await audit.log(
        action="evidence.unlink",
        resource_type="evidence",
        resource_id=evidence.id,
        description="Evidence unlinked from incident",
        request=request,
        current_user=current_user,
        metadata={"previous_incident_id": evidence.incident_id},
    )
    return to_evidence_read(updated)


@router.post("/{evidence_id}/archive", response_model=EvidenceRead)
async def archive_evidence(
    evidence_id: str,
    request: Request,
    current_user: Annotated[User, Depends(require_roles(*ADMIN_ROLES))],
    evidence_repo: Annotated[EvidenceRepository, Depends(get_evidence_repository)],
    custody: Annotated[EvidenceCustodyRepository, Depends(get_evidence_custody_repository)],
    audit: Annotated[AuditService, Depends(get_audit_service)],
) -> EvidenceRead:
    return await set_evidence_status(
        evidence_id=evidence_id,
        next_status=EvidenceStatus.ARCHIVED,
        action=EvidenceCustodyAction.ARCHIVED,
        audit_action="evidence.archive",
        description="Evidence archived",
        request=request,
        current_user=current_user,
        evidence_repo=evidence_repo,
        custody=custody,
        audit=audit,
    )


@router.post("/{evidence_id}/restore", response_model=EvidenceRead)
async def restore_evidence(
    evidence_id: str,
    request: Request,
    current_user: Annotated[User, Depends(require_roles(*ADMIN_ROLES))],
    evidence_repo: Annotated[EvidenceRepository, Depends(get_evidence_repository)],
    custody: Annotated[EvidenceCustodyRepository, Depends(get_evidence_custody_repository)],
    audit: Annotated[AuditService, Depends(get_audit_service)],
) -> EvidenceRead:
    return await set_evidence_status(
        evidence_id=evidence_id,
        next_status=EvidenceStatus.ACTIVE,
        action=EvidenceCustodyAction.RESTORED,
        audit_action="evidence.restore",
        description="Evidence restored",
        request=request,
        current_user=current_user,
        evidence_repo=evidence_repo,
        custody=custody,
        audit=audit,
    )


async def set_evidence_status(
    *,
    evidence_id: str,
    next_status: EvidenceStatus,
    action: EvidenceCustodyAction,
    audit_action: str,
    description: str,
    request: Request,
    current_user: User,
    evidence_repo: EvidenceRepository,
    custody: EvidenceCustodyRepository,
    audit: AuditService,
) -> EvidenceRead:
    evidence = await get_evidence_or_404(evidence_id, current_user, evidence_repo)
    updated = await evidence_repo.set_status(
        evidence_id=evidence.id,
        organization_id=current_user.organization_id,
        status=next_status,
    )
    if updated is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Evidence not found")
    await custody_log(
        custody,
        evidence=updated,
        action=action,
        description=description,
        current_user=current_user,
        metadata={"previous_status": evidence.status.value, "status": next_status.value},
    )
    await audit.log(
        action=audit_action,
        resource_type="evidence",
        resource_id=evidence.id,
        description=description,
        request=request,
        current_user=current_user,
        metadata={"previous_status": evidence.status.value, "status": next_status.value},
    )
    return to_evidence_read(updated)


@router.get("/{evidence_id}/custody", response_model=EvidenceCustodyListResponse)
async def get_evidence_custody(
    evidence_id: str,
    current_user: Annotated[User, Depends(require_roles(*READ_ROLES))],
    evidence_repo: Annotated[EvidenceRepository, Depends(get_evidence_repository)],
    custody: Annotated[EvidenceCustodyRepository, Depends(get_evidence_custody_repository)],
    limit: int = Query(default=500, ge=1, le=1000),
    skip: int = Query(default=0, ge=0),
) -> EvidenceCustodyListResponse:
    evidence = await get_evidence_or_404(evidence_id, current_user, evidence_repo)
    events = await custody.list_for_evidence(
        organization_id=current_user.organization_id,
        evidence_id=evidence.id,
        limit=limit,
        skip=skip,
        newest_first=False,
    )
    return EvidenceCustodyListResponse(
        custody=[to_custody_read(event) for event in events],
        count=len(events),
    )
