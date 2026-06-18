from typing import Annotated

from fastapi import APIRouter, Depends, Header, HTTPException, Request, status

from app.api.dependencies import get_agent_repository, get_audit_service, require_roles
from app.core.security import generate_agent_api_key, hash_agent_api_key
from app.models.agent import Agent, AgentStatus
from app.models.auth import Role
from app.models.user import User
from app.repositories.agents import AgentRepository
from app.schemas.agents import (
    AgentDisableResponse,
    AgentHeartbeatRequest,
    AgentHeartbeatResponse,
    AgentListResponse,
    AgentRead,
    AgentRegisterRequest,
    AgentRegisterResponse,
)
from app.services.audit_service import AuditService

router = APIRouter(prefix="/agents", tags=["agents"])

READ_ROLES = (Role.SUPER_ADMIN, Role.ORG_ADMIN, Role.ANALYST, Role.VIEWER)
WRITE_ROLES = (Role.SUPER_ADMIN, Role.ORG_ADMIN, Role.ANALYST)
ADMIN_ROLES = (Role.SUPER_ADMIN, Role.ORG_ADMIN)


def to_agent_read(agent: Agent) -> AgentRead:
    return AgentRead(
        id=agent.id,
        organization_id=agent.organization_id,
        name=agent.name,
        hostname=agent.hostname,
        os_type=agent.os_type,
        agent_version=agent.agent_version,
        status=agent.status,
        last_seen_at=agent.last_seen_at,
        ip_address=agent.ip_address,
        tags=agent.tags,
        created_at=agent.created_at,
        updated_at=agent.updated_at,
    )


@router.post(
    "/register",
    response_model=AgentRegisterResponse,
    status_code=status.HTTP_201_CREATED,
)
async def register_agent(
    payload: AgentRegisterRequest,
    request: Request,
    current_user: Annotated[User, Depends(require_roles(*WRITE_ROLES))],
    agents: Annotated[AgentRepository, Depends(get_agent_repository)],
    audit: Annotated[AuditService, Depends(get_audit_service)],
) -> AgentRegisterResponse:
    api_key = generate_agent_api_key()
    agent = await agents.create(
        organization_id=current_user.organization_id,
        name=payload.name,
        hostname=payload.hostname,
        os_type=payload.os_type,
        agent_version=payload.agent_version,
        ip_address=payload.ip_address,
        tags=payload.tags,
        api_key_hash=hash_agent_api_key(api_key),
    )
    await audit.log(
        action="agent.register",
        resource_type="agent",
        resource_id=agent.id,
        description="Agent registered",
        request=request,
        current_user=current_user,
        metadata={
            "name": agent.name,
            "hostname": agent.hostname,
            "os_type": agent.os_type.value,
            "agent_version": agent.agent_version,
            "tags": agent.tags,
        },
    )
    return AgentRegisterResponse(agent=to_agent_read(agent), api_key=api_key)


@router.post("/heartbeat", response_model=AgentHeartbeatResponse)
async def heartbeat(
    payload: AgentHeartbeatRequest,
    request: Request,
    agents: Annotated[AgentRepository, Depends(get_agent_repository)],
    agent_key: Annotated[str | None, Header(alias="X-Agent-Key")] = None,
) -> AgentHeartbeatResponse:
    if agent_key is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing agent key",
        )

    agent = await agents.find_by_api_key(agent_key)
    if agent is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid agent key",
        )
    if agent.status == AgentStatus.DISABLED:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Agent is disabled",
        )

    request_ip_address = request.client.host if request.client is not None else None
    await agents.update_heartbeat(
        agent_id=agent.id,
        ip_address=payload.ip_address or request_ip_address,
        agent_version=payload.agent_version,
    )
    return AgentHeartbeatResponse()


@router.get("", response_model=AgentListResponse)
async def list_agents(
    current_user: Annotated[User, Depends(require_roles(*READ_ROLES))],
    agents: Annotated[AgentRepository, Depends(get_agent_repository)],
) -> AgentListResponse:
    organization_agents = await agents.list_by_organization(current_user.organization_id)
    return AgentListResponse(agents=[to_agent_read(agent) for agent in organization_agents])


@router.get("/{agent_id}", response_model=AgentRead)
async def get_agent(
    agent_id: str,
    current_user: Annotated[User, Depends(require_roles(*READ_ROLES))],
    agents: Annotated[AgentRepository, Depends(get_agent_repository)],
) -> AgentRead:
    agent = await agents.find_by_id_for_organization(
        agent_id=agent_id,
        organization_id=current_user.organization_id,
    )
    if agent is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Agent not found",
        )
    return to_agent_read(agent)


@router.post("/{agent_id}/disable", response_model=AgentDisableResponse)
async def disable_agent(
    agent_id: str,
    request: Request,
    current_user: Annotated[User, Depends(require_roles(*ADMIN_ROLES))],
    agents: Annotated[AgentRepository, Depends(get_agent_repository)],
    audit: Annotated[AuditService, Depends(get_audit_service)],
) -> AgentDisableResponse:
    agent = await agents.disable(
        agent_id=agent_id,
        organization_id=current_user.organization_id,
    )
    if agent is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Agent not found",
        )
    await audit.log(
        action="agent.disable",
        resource_type="agent",
        resource_id=agent.id,
        description="Agent disabled",
        request=request,
        current_user=current_user,
        metadata={"hostname": agent.hostname, "name": agent.name},
    )
    return AgentDisableResponse(agent=to_agent_read(agent))
