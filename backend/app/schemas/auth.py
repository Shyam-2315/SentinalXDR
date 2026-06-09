from pydantic import BaseModel, EmailStr, Field

from app.models.auth import Role, UserStatus


class OrganizationRead(BaseModel):
    id: str
    name: str


class UserRead(BaseModel):
    id: str
    organization_id: str
    email: EmailStr
    display_name: str
    role: Role
    status: UserStatus


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    display_name: str = Field(min_length=1, max_length=120)
    organization_name: str | None = Field(default=None, min_length=1, max_length=120)
    organization_id: str | None = None


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class RefreshRequest(BaseModel):
    refresh_token: str


class AuthResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    user: UserRead
    organization: OrganizationRead


class MeResponse(BaseModel):
    user: UserRead
    organization: OrganizationRead


class RefreshResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class MessageResponse(BaseModel):
    status: str
