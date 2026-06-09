from datetime import UTC, datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.models.auth import Role, UserStatus


class User(BaseModel):
    model_config = ConfigDict(use_enum_values=False)

    id: str
    organization_id: str
    email: EmailStr
    display_name: str
    role: Role
    status: UserStatus = UserStatus.ACTIVE
    hashed_password: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
