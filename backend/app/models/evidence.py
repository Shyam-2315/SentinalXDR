from datetime import UTC, datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field


class EvidenceStatus(StrEnum):
    ACTIVE = "active"
    ARCHIVED = "archived"


class EvidenceVerificationStatus(StrEnum):
    VERIFIED = "verified"
    FAILED = "failed"
    NOT_VERIFIED = "not_verified"


class EvidenceCustodyAction(StrEnum):
    UPLOADED = "uploaded"
    VIEWED = "viewed"
    DOWNLOADED = "downloaded"
    LINKED_TO_INCIDENT = "linked_to_incident"
    UNLINKED_FROM_INCIDENT = "unlinked_from_incident"
    VERIFIED = "verified"
    ARCHIVED = "archived"
    RESTORED = "restored"


class Evidence(BaseModel):
    id: str
    organization_id: str
    incident_id: str | None = None
    uploaded_by_user_id: str
    uploaded_by_email: str
    filename: str
    original_filename: str
    content_type: str
    size_bytes: int
    sha256: str
    storage_path: str
    description: str | None = None
    tags: list[str] = Field(default_factory=list)
    status: EvidenceStatus = EvidenceStatus.ACTIVE
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    last_verified_at: datetime | None = None
    verification_status: EvidenceVerificationStatus = EvidenceVerificationStatus.NOT_VERIFIED


class EvidenceCustodyEvent(BaseModel):
    id: str
    organization_id: str
    evidence_id: str
    actor_user_id: str | None = None
    actor_email: str | None = None
    action: EvidenceCustodyAction
    description: str
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
