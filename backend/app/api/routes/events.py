from typing import Annotated

from fastapi import APIRouter, Depends, Header, HTTPException, Query, status

from app.api.dependencies import get_agent_repository, get_event_repository, require_roles
from app.core.config import get_settings
from app.models.agent import AgentStatus
from app.models.auth import Role
from app.models.event import Event, EventSeverity, EventSource
from app.models.user import User
from app.repositories.agents import AgentRepository
from app.repositories.events import EventRepository
from app.schemas.events import (
    EventIngestRequest,
    EventIngestResponse,
    EventListResponse,
    EventRead,
)

router = APIRouter(prefix="/api/events", tags=["events"])

READ_ROLES = (Role.SUPER_ADMIN, Role.ORG_ADMIN, Role.ANALYST, Role.VIEWER)


def to_event_read(event: Event) -> EventRead:
    return EventRead(
        id=event.id,
        organization_id=event.organization_id,
        agent_id=event.agent_id,
        event_type=event.event_type,
        severity=event.severity,
        source=event.source,
        title=event.title,
        description=event.description,
        raw_event=event.raw_event,
        normalized_fields=event.normalized_fields,
        tags=event.tags,
        timestamp=event.timestamp,
        received_at=event.received_at,
    )


@router.post("/ingest", response_model=EventIngestResponse, status_code=status.HTTP_201_CREATED)
async def ingest_events(
    payload: EventIngestRequest,
    agents: Annotated[AgentRepository, Depends(get_agent_repository)],
    events: Annotated[EventRepository, Depends(get_event_repository)],
    agent_key: Annotated[str | None, Header(alias="X-Agent-Key")] = None,
) -> EventIngestResponse:
    settings = get_settings()
    if len(payload.events) > settings.event_ingest_batch_size_limit:
        raise HTTPException(
            status_code=status.HTTP_413_CONTENT_TOO_LARGE,
            detail=f"Batch size limit exceeded: {settings.event_ingest_batch_size_limit}",
        )

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

    stored_events = await events.create_many(
        organization_id=agent.organization_id,
        agent_id=agent.id,
        event_items=payload.events,
    )
    await agents.update_heartbeat(
        agent_id=agent.id,
        ip_address=None,
        agent_version=None,
    )
    return EventIngestResponse(
        accepted=len(stored_events),
        events=[to_event_read(event) for event in stored_events],
    )


@router.get("", response_model=EventListResponse)
async def list_events(
    current_user: Annotated[User, Depends(require_roles(*READ_ROLES))],
    events: Annotated[EventRepository, Depends(get_event_repository)],
    severity: EventSeverity | None = None,
    source: EventSource | None = None,
    event_type: str | None = None,
    agent_id: str | None = None,
    limit: int = Query(default=100, ge=1, le=500),
    skip: int = Query(default=0, ge=0),
) -> EventListResponse:
    organization_events = await events.list_by_organization(
        organization_id=current_user.organization_id,
        severity=severity,
        source=source,
        event_type=event_type,
        agent_id=agent_id,
        limit=limit,
        skip=skip,
    )
    return EventListResponse(
        events=[to_event_read(event) for event in organization_events],
        count=len(organization_events),
        limit=limit,
        skip=skip,
    )


@router.get("/{event_id}", response_model=EventRead)
async def get_event(
    event_id: str,
    current_user: Annotated[User, Depends(require_roles(*READ_ROLES))],
    events: Annotated[EventRepository, Depends(get_event_repository)],
) -> EventRead:
    event = await events.find_by_id_for_organization(
        event_id=event_id,
        organization_id=current_user.organization_id,
    )
    if event is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Event not found",
        )
    return to_event_read(event)
