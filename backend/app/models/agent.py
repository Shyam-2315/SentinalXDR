from datetime import UTC, datetime
from enum import StrEnum

from pydantic import BaseModel, Field


class OSType(StrEnum):
    WINDOWS = "windows"
    LINUX = "linux"
    MACOS = "macos"
    UNKNOWN = "unknown"


class AgentStatus(StrEnum):
    ONLINE = "online"
    OFFLINE = "offline"
    DISABLED = "disabled"


class Agent(BaseModel):
    id: str
    organization_id: str
    name: str
    hostname: str
    os_type: OSType = OSType.UNKNOWN
    agent_version: str | None = None
    status: AgentStatus = AgentStatus.OFFLINE
    api_key_hash: str
    last_seen_at: datetime | None = None
    ip_address: str | None = None
    tags: list[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
