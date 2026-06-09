from datetime import UTC, datetime, timedelta
from secrets import token_urlsafe
from typing import Any, Literal
from uuid import uuid4

import jwt
from jwt import InvalidTokenError
from passlib.context import CryptContext

from app.core.config import get_settings
from app.models.user import User

TokenType = Literal["access", "refresh"]

password_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    return password_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return password_context.verify(plain_password, hashed_password)


def generate_agent_api_key() -> str:
    settings = get_settings()
    return f"sxag_{token_urlsafe(settings.agent_api_key_bytes)}"


def hash_agent_api_key(api_key: str) -> str:
    return password_context.hash(api_key)


def verify_agent_api_key(api_key: str, api_key_hash: str) -> bool:
    return password_context.verify(api_key, api_key_hash)


def create_token(user: User, token_type: TokenType) -> str:
    settings = get_settings()
    now = datetime.now(UTC)
    expires_delta = (
        timedelta(minutes=settings.access_token_expire_minutes)
        if token_type == "access"
        else timedelta(days=settings.refresh_token_expire_days)
    )
    payload: dict[str, Any] = {
        "sub": user.id,
        "organization_id": user.organization_id,
        "role": user.role.value,
        "type": token_type,
        "jti": uuid4().hex,
        "iat": now,
        "exp": now + expires_delta,
    }
    return jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)


def decode_token(token: str, expected_type: TokenType) -> dict[str, Any]:
    settings = get_settings()
    try:
        payload = jwt.decode(token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm])
    except InvalidTokenError as exc:
        raise ValueError("Invalid token") from exc

    if payload.get("type") != expected_type:
        raise ValueError("Invalid token type")
    if not payload.get("sub") or not payload.get("organization_id"):
        raise ValueError("Invalid token claims")
    return payload
