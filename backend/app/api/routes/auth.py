from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status

from app.api.dependencies import (
    get_current_user,
    get_organization_repository,
    get_user_repository,
)
from app.core.security import create_token, decode_token, hash_password, verify_password
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

router = APIRouter(prefix="/api/auth", tags=["auth"])


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
    users: Annotated[UserRepository, Depends(get_user_repository)],
    organizations: Annotated[OrganizationRepository, Depends(get_organization_repository)],
) -> AuthResponse:
    existing_user = await users.find_by_email(payload.email)
    if existing_user is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email is already registered",
        )

    is_first_user = await users.count() == 0
    if is_first_user:
        organization = await organizations.create(
            name=payload.organization_name or "SentinelXDR Organization",
        )
        role = Role.ORG_ADMIN
    else:
        if payload.organization_id is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="organization_id is required after the first user is registered",
            )
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
    return build_auth_response(user, organization)


@router.post("/login", response_model=AuthResponse)
async def login(
    payload: LoginRequest,
    users: Annotated[UserRepository, Depends(get_user_repository)],
    organizations: Annotated[OrganizationRepository, Depends(get_organization_repository)],
) -> AuthResponse:
    user = await users.find_by_email(payload.email)
    if user is None or not verify_password(payload.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )
    if user.status == UserStatus.DISABLED:
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
    users: Annotated[UserRepository, Depends(get_user_repository)],
) -> RefreshResponse:
    try:
        token_payload = decode_token(payload.refresh_token, expected_type="refresh")
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token",
        ) from exc

    user = await users.find_by_id(token_payload["sub"])
    if user is None or user.organization_id != token_payload["organization_id"]:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token",
        )
    if user.status == UserStatus.DISABLED:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is disabled",
        )
    return RefreshResponse(access_token=create_token(user, "access"))


@router.post("/logout", response_model=MessageResponse)
async def logout(current_user: Annotated[User, Depends(get_current_user)]) -> MessageResponse:
    return MessageResponse(status="ok")
