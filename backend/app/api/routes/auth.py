from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, status

from app.api.dependencies import (
    get_audit_service,
    get_current_user,
    get_organization_repository,
    get_user_repository,
)
from app.core.security import create_token, decode_token, hash_password, verify_password
from app.models.audit_log import AuditStatus
from app.models.auth import Role, UserStatus
from app.models.organization import Organization
from app.models.user import User
from app.repositories.organizations import OrganizationRepository
from app.repositories.users import UserRepository
from app.schemas.auth import (
    AuthResponse,
    LoginRequest,
    MeResponse,
    MessageResponse,
    OrganizationRead,
    RefreshRequest,
    RefreshResponse,
    RegisterRequest,
    UserRead,
)
from app.services.audit_service import AuditService

router = APIRouter(prefix="/auth", tags=["auth"])


def to_user_read(user: User) -> UserRead:
    return UserRead(
        id=user.id,
        organization_id=user.organization_id,
        email=user.email,
        display_name=user.display_name,
        role=user.role,
        status=user.status,
    )


def to_organization_read(organization: Organization) -> OrganizationRead:
    return OrganizationRead(id=organization.id, name=organization.name)


def build_auth_response(user: User, organization: Organization) -> AuthResponse:
    return AuthResponse(
        access_token=create_token(user, "access"),
        refresh_token=create_token(user, "refresh"),
        user=to_user_read(user),
        organization=to_organization_read(organization),
    )


@router.post("/register", response_model=AuthResponse, status_code=status.HTTP_201_CREATED)
async def register(
    payload: RegisterRequest,
    request: Request,
    users: Annotated[UserRepository, Depends(get_user_repository)],
    organizations: Annotated[OrganizationRepository, Depends(get_organization_repository)],
    audit: Annotated[AuditService, Depends(get_audit_service)],
) -> AuthResponse:
    if payload.organization_name is not None and payload.organization_id is not None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Provide either organization_name or organization_id, not both.",
        )
    if payload.organization_name is None and payload.organization_id is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="organization_name or organization_id is required.",
        )

    existing_user = await users.find_by_email(payload.email)
    if existing_user is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email is already registered",
        )

    if payload.organization_name is not None:
        organization = await organizations.create(
            name=payload.organization_name,
        )
        role = Role.ORG_ADMIN
    else:
        organization = await organizations.find_by_id(payload.organization_id)
        if organization is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Organization not found",
            )
        role = Role.VIEWER

    user = await users.create(
        email=payload.email,
        display_name=payload.display_name,
        organization_id=organization.id,
        role=role,
        hashed_password=hash_password(payload.password),
    )
    await audit.log(
        action="user.register",
        resource_type="user",
        resource_id=user.id,
        description="User registered",
        request=request,
        current_user=user,
        metadata={
            "organization_id": organization.id,
            "organization_name": organization.name,
            "role": role.value,
        },
    )
    return build_auth_response(user, organization)


@router.post("/login", response_model=AuthResponse)
async def login(
    payload: LoginRequest,
    request: Request,
    users: Annotated[UserRepository, Depends(get_user_repository)],
    organizations: Annotated[OrganizationRepository, Depends(get_organization_repository)],
    audit: Annotated[AuditService, Depends(get_audit_service)],
) -> AuthResponse:
    user = await users.find_by_email(payload.email)
    if user is None or not verify_password(payload.password, user.hashed_password):
        await audit.log(
            action="user.login",
            resource_type="user",
            status=AuditStatus.FAILURE,
            description="User login failed",
            request=request,
            actor_email=str(payload.email),
            metadata={"reason": "invalid_credentials"},
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )
    if user.status == UserStatus.DISABLED:
        await audit.log(
            action="user.login",
            resource_type="user",
            resource_id=user.id,
            status=AuditStatus.FAILURE,
            description="Disabled user login rejected",
            request=request,
            current_user=user,
            metadata={"reason": "user_disabled"},
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is disabled",
        )

    organization = await organizations.find_by_id(user.organization_id)
    if organization is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="User organization is missing",
        )
    await audit.log(
        action="user.login",
        resource_type="user",
        resource_id=user.id,
        description="User logged in",
        request=request,
        current_user=user,
        metadata={"organization_id": organization.id},
    )
    return build_auth_response(user, organization)


@router.get("/me", response_model=MeResponse)
async def me(
    current_user: Annotated[User, Depends(get_current_user)],
    organizations: Annotated[OrganizationRepository, Depends(get_organization_repository)],
) -> MeResponse:
    organization = await organizations.find_by_id(current_user.organization_id)
    if organization is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="User organization is missing",
        )
    return MeResponse(
        user=to_user_read(current_user),
        organization=to_organization_read(organization),
    )


@router.post("/refresh", response_model=RefreshResponse)
async def refresh(
    payload: RefreshRequest,
    request: Request,
    users: Annotated[UserRepository, Depends(get_user_repository)],
    audit: Annotated[AuditService, Depends(get_audit_service)],
) -> RefreshResponse:
    try:
        token_payload = decode_token(payload.refresh_token, expected_type="refresh")
    except ValueError as exc:
        await audit.log(
            action="token.refresh",
            resource_type="token",
            status=AuditStatus.FAILURE,
            description="Refresh token rejected",
            request=request,
            metadata={"reason": "invalid_refresh_token"},
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token",
        ) from exc

    user = await users.find_by_id(token_payload["sub"])
    if user is None or user.organization_id != token_payload["organization_id"]:
        await audit.log(
            action="token.refresh",
            resource_type="token",
            status=AuditStatus.FAILURE,
            description="Refresh token subject rejected",
            request=request,
            organization_id=token_payload.get("organization_id"),
            actor_user_id=token_payload.get("sub"),
            metadata={"reason": "invalid_refresh_token_subject"},
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token",
        )
    if user.status == UserStatus.DISABLED:
        await audit.log(
            action="token.refresh",
            resource_type="token",
            status=AuditStatus.FAILURE,
            description="Disabled user refresh rejected",
            request=request,
            current_user=user,
            metadata={"reason": "user_disabled"},
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is disabled",
        )
    await audit.log(
        action="token.refresh",
        resource_type="token",
        description="Access token refreshed",
        request=request,
        current_user=user,
    )
    return RefreshResponse(access_token=create_token(user, "access"))


@router.post("/logout", response_model=MessageResponse)
async def logout(
    request: Request,
    current_user: Annotated[User, Depends(get_current_user)],
    audit: Annotated[AuditService, Depends(get_audit_service)],
) -> MessageResponse:
    await audit.log(
        action="user.logout",
        resource_type="user",
        resource_id=current_user.id,
        description="User logged out",
        request=request,
        current_user=current_user,
    )
    return MessageResponse(status="ok")
