from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.api.dependencies import get_attack_chain_repository, require_roles
from app.models.attack_chain import AttackChain, AttackChainStatus
from app.models.auth import Role
from app.models.event import EventSeverity
from app.models.user import User
from app.repositories.attack_chains import AttackChainRepository
from app.schemas.attack_chains import (
    AttackChainListResponse,
    AttackChainRead,
    AttackChainStatusUpdate,
)

router = APIRouter(prefix="/api/attack-chains", tags=["attack-chains"])
incident_router = APIRouter(prefix="/api/incidents", tags=["attack-chains"])

READ_ROLES = (Role.SUPER_ADMIN, Role.ORG_ADMIN, Role.ANALYST, Role.VIEWER)
UPDATE_ROLES = (Role.SUPER_ADMIN, Role.ORG_ADMIN, Role.ANALYST)


def to_attack_chain_read(chain: AttackChain) -> AttackChainRead:
    return AttackChainRead(**chain.model_dump())


@router.get("", response_model=AttackChainListResponse)
async def list_attack_chains(
    current_user: Annotated[User, Depends(require_roles(*READ_ROLES))],
    chains: Annotated[AttackChainRepository, Depends(get_attack_chain_repository)],
    status_filter: Annotated[AttackChainStatus | None, Query(alias="status")] = None,
    severity: EventSeverity | None = None,
    agent_id: str | None = None,
    mitre_technique: str | None = None,
    min_risk_score: float | None = Query(default=None, ge=0, le=100),
    limit: int = Query(default=100, ge=1, le=500),
    skip: int = Query(default=0, ge=0),
) -> AttackChainListResponse:
    organization_chains = await chains.list_by_organization(
        organization_id=current_user.organization_id,
        status=status_filter,
        severity=severity,
        agent_id=agent_id,
        mitre_technique=mitre_technique,
        min_risk_score=min_risk_score,
        limit=limit,
        skip=skip,
    )
    return AttackChainListResponse(
        attack_chains=[to_attack_chain_read(chain) for chain in organization_chains],
        count=len(organization_chains),
        limit=limit,
        skip=skip,
    )


@router.get("/{chain_id}", response_model=AttackChainRead)
async def get_attack_chain(
    chain_id: str,
    current_user: Annotated[User, Depends(require_roles(*READ_ROLES))],
    chains: Annotated[AttackChainRepository, Depends(get_attack_chain_repository)],
) -> AttackChainRead:
    chain = await chains.find_by_id_for_organization(
        chain_id=chain_id,
        organization_id=current_user.organization_id,
    )
    if chain is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Attack chain not found")
    return to_attack_chain_read(chain)


@router.patch("/{chain_id}/status", response_model=AttackChainRead)
async def update_attack_chain_status(
    chain_id: str,
    payload: AttackChainStatusUpdate,
    current_user: Annotated[User, Depends(require_roles(*UPDATE_ROLES))],
    chains: Annotated[AttackChainRepository, Depends(get_attack_chain_repository)],
) -> AttackChainRead:
    chain = await chains.update_status(
        chain_id=chain_id,
        organization_id=current_user.organization_id,
        status=payload.status,
    )
    if chain is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Attack chain not found")
    return to_attack_chain_read(chain)


@incident_router.get("/{incident_id}/attack-chain", response_model=AttackChainRead)
async def get_attack_chain_by_incident(
    incident_id: str,
    current_user: Annotated[User, Depends(require_roles(*READ_ROLES))],
    chains: Annotated[AttackChainRepository, Depends(get_attack_chain_repository)],
) -> AttackChainRead:
    chain = await chains.find_by_incident_for_organization(
        incident_id=incident_id,
        organization_id=current_user.organization_id,
    )
    if chain is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Attack chain not found")
    return to_attack_chain_read(chain)
