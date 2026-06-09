from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.api.dependencies import (
    get_detection_result_repository,
    get_detection_rule_repository,
    require_roles,
)
from app.models.auth import Role
from app.models.detection import DetectionResult, DetectionRule
from app.models.user import User
from app.repositories.detections import DetectionResultRepository, DetectionRuleRepository
from app.schemas.detections import (
    DetectionResultListResponse,
    DetectionResultRead,
    DetectionRuleCreate,
    DetectionRuleListResponse,
    DetectionRuleRead,
    DetectionRuleUpdate,
)

router = APIRouter(prefix="/api/detections", tags=["detections"])

READ_ROLES = (Role.SUPER_ADMIN, Role.ORG_ADMIN, Role.ANALYST, Role.VIEWER)
CREATE_ROLES = (Role.SUPER_ADMIN, Role.ORG_ADMIN, Role.ANALYST)
ADMIN_ROLES = (Role.SUPER_ADMIN, Role.ORG_ADMIN)


def to_rule_read(rule: DetectionRule) -> DetectionRuleRead:
    return DetectionRuleRead(**rule.model_dump())


def to_result_read(result: DetectionResult) -> DetectionResultRead:
    return DetectionResultRead(**result.model_dump())


@router.get("/rules", response_model=DetectionRuleListResponse)
async def list_rules(
    current_user: Annotated[User, Depends(require_roles(*READ_ROLES))],
    rules: Annotated[DetectionRuleRepository, Depends(get_detection_rule_repository)],
) -> DetectionRuleListResponse:
    organization_rules = await rules.list_for_organization(current_user.organization_id)
    return DetectionRuleListResponse(rules=[to_rule_read(rule) for rule in organization_rules])


@router.get("/rules/{rule_id}", response_model=DetectionRuleRead)
async def get_rule(
    rule_id: str,
    current_user: Annotated[User, Depends(require_roles(*READ_ROLES))],
    rules: Annotated[DetectionRuleRepository, Depends(get_detection_rule_repository)],
) -> DetectionRuleRead:
    rule = await rules.find_by_id_for_organization(
        rule_id=rule_id,
        organization_id=current_user.organization_id,
    )
    if rule is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Rule not found")
    return to_rule_read(rule)


@router.post("/rules", response_model=DetectionRuleRead, status_code=status.HTTP_201_CREATED)
async def create_rule(
    payload: DetectionRuleCreate,
    current_user: Annotated[User, Depends(require_roles(*CREATE_ROLES))],
    rules: Annotated[DetectionRuleRepository, Depends(get_detection_rule_repository)],
) -> DetectionRuleRead:
    rule = await rules.create(organization_id=current_user.organization_id, rule=payload)
    return to_rule_read(rule)


@router.patch("/rules/{rule_id}", response_model=DetectionRuleRead)
async def update_rule(
    rule_id: str,
    payload: DetectionRuleUpdate,
    current_user: Annotated[User, Depends(require_roles(*ADMIN_ROLES))],
    rules: Annotated[DetectionRuleRepository, Depends(get_detection_rule_repository)],
) -> DetectionRuleRead:
    existing = await rules.find_by_id_for_organization(
        rule_id=rule_id,
        organization_id=current_user.organization_id,
    )
    if existing is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Rule not found")
    if existing.organization_id is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Built-in rules are read-only",
        )
    rule = await rules.update(
        rule_id=rule_id,
        organization_id=current_user.organization_id,
        updates=payload.model_dump(exclude_unset=True),
    )
    if rule is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Rule not found")
    return to_rule_read(rule)


@router.post("/rules/{rule_id}/disable", response_model=DetectionRuleRead)
async def disable_rule(
    rule_id: str,
    current_user: Annotated[User, Depends(require_roles(*ADMIN_ROLES))],
    rules: Annotated[DetectionRuleRepository, Depends(get_detection_rule_repository)],
) -> DetectionRuleRead:
    return await set_rule_enabled(rule_id, current_user, rules, enabled=False)


@router.post("/rules/{rule_id}/enable", response_model=DetectionRuleRead)
async def enable_rule(
    rule_id: str,
    current_user: Annotated[User, Depends(require_roles(*ADMIN_ROLES))],
    rules: Annotated[DetectionRuleRepository, Depends(get_detection_rule_repository)],
) -> DetectionRuleRead:
    return await set_rule_enabled(rule_id, current_user, rules, enabled=True)


async def set_rule_enabled(
    rule_id: str,
    current_user: User,
    rules: DetectionRuleRepository,
    *,
    enabled: bool,
) -> DetectionRuleRead:
    existing = await rules.find_by_id_for_organization(
        rule_id=rule_id,
        organization_id=current_user.organization_id,
    )
    if existing is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Rule not found")
    if existing.organization_id is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Built-in rules are read-only",
        )
    rule = await rules.set_enabled(
        rule_id=rule_id,
        organization_id=current_user.organization_id,
        enabled=enabled,
    )
    if rule is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Rule not found")
    return to_rule_read(rule)


@router.get("/results", response_model=DetectionResultListResponse)
async def list_results(
    current_user: Annotated[User, Depends(require_roles(*READ_ROLES))],
    results: Annotated[DetectionResultRepository, Depends(get_detection_result_repository)],
    limit: int = Query(default=100, ge=1, le=500),
    skip: int = Query(default=0, ge=0),
) -> DetectionResultListResponse:
    organization_results = await results.list_by_organization(
        organization_id=current_user.organization_id,
        limit=limit,
        skip=skip,
    )
    return DetectionResultListResponse(
        results=[to_result_read(result) for result in organization_results],
        count=len(organization_results),
        limit=limit,
        skip=skip,
    )


@router.get("/results/{result_id}", response_model=DetectionResultRead)
async def get_result(
    result_id: str,
    current_user: Annotated[User, Depends(require_roles(*READ_ROLES))],
    results: Annotated[DetectionResultRepository, Depends(get_detection_result_repository)],
) -> DetectionResultRead:
    result = await results.find_by_id_for_organization(
        result_id=result_id,
        organization_id=current_user.organization_id,
    )
    if result is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Result not found")
    return to_result_read(result)
