from datetime import datetime
from typing import Any

from pydantic import BaseModel

from app.models.evidence import (
    EvidenceCustodyAction,
    EvidenceStatus,
    EvidenceVerificationStatus,
)


class EvidenceRead(BaseModel):
    id: str
    organization_id: str
    incident_id: str | None
    uploaded_by_user_id: str
    uploaded_by_email: str
    filename: str
    original_filename: str
    content_type: str
    size_bytes: int
    sha256: str
    description: str | None
    tags: list[str]
    status: EvidenceStatus
    created_at: datetime
    updated_at: datetime
    last_verified_at: datetime | None
    verification_status: EvidenceVerificationStatus


class EvidenceListResponse(BaseModel):
    evidence: list[EvidenceRead]
    count: int
    limit: int
    skip: int


class EvidenceVerifyResponse(BaseModel):
    evidence: EvidenceRead
    expected_sha256: str
    actual_sha256: str | None
    matched: bool


class EvidenceLinkRequest(BaseModel):
    incident_id: str


class EvidenceCustodyRead(BaseModel):
    id: str
    organization_id: str
    evidence_id: str
    actor_user_id: str | None
    actor_email: str | None
    action: EvidenceCustodyAction
    description: str
    metadata: dict[str, Any]
    created_at: datetime


class EvidenceCustodyListResponse(BaseModel):
    custody: list[EvidenceCustodyRead]
    count: int
