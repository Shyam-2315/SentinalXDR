from datetime import datetime

from pydantic import BaseModel, Field

from app.models.agent import AgentStatus, OSType


class AgentRead(BaseModel):
    id: str
    organization_id: str
    name: str
    hostname: str
    os_type: OSType
    agent_version: str | None
    status: AgentStatus
    last_seen_at: datetime | None
    ip_address: str | None
    tags: list[str]
    created_at: datetime
    updated_at: datetime


class AgentRegisterRequest(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    hostname: str = Field(min_length=1, max_length=255)
    os_type: OSType = OSType.UNKNOWN
    agent_version: str | None = Field(default=None, max_length=64)
    ip_address: str | None = Field(default=None, max_length=64)
    tags: list[str] = Field(default_factory=list)


class AgentRegisterResponse(BaseModel):
    agent: AgentRead
    api_key: str


class AgentListResponse(BaseModel):
    agents: list[AgentRead]


class AgentHeartbeatRequest(BaseModel):
    agent_version: str | None = Field(default=None, max_length=64)
    ip_address: str | None = Field(default=None, max_length=64)


class AgentHeartbeatResponse(BaseModel):
    status: str = "ok"


class AgentDisableResponse(BaseModel):
    agent: AgentRead
