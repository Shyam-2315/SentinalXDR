from collections.abc import Iterator
from datetime import UTC, datetime
from typing import Annotated
from uuid import uuid4

import pytest
from fastapi import Depends
from fastapi.testclient import TestClient

from app.api.dependencies import (
    get_organization_repository,
    get_user_repository,
    require_roles,
)
from app.core.config import get_settings
from app.main import app
from app.models.auth import Role, UserStatus
from app.models.organization import Organization
from app.models.user import User


class AuthStore:
    def __init__(self) -> None:
        self.users: dict[str, User] = {}
        self.organizations: dict[str, Organization] = {}


class FakeOrganizationRepository:
    def __init__(self, store: AuthStore) -> None:
        self.store = store

    async def create(self, name: str) -> Organization:
        now = datetime.now(UTC)
        organization = Organization(
            id=f"org_{uuid4().hex}",
            name=name,
            created_at=now,
            updated_at=now,
        )
        self.store.organizations[organization.id] = organization
        return organization

    async def find_by_id(self, organization_id: str) -> Organization | None:
        return self.store.organizations.get(organization_id)


class FakeUserRepository:
    def __init__(self, store: AuthStore) -> None:
        self.store = store

    async def count(self) -> int:
        return len(self.store.users)

    async def create(
        self,
        *,
        email: str,
        display_name: str,
        organization_id: str,
        role: Role,
        hashed_password: str,
        status: UserStatus = UserStatus.ACTIVE,
    ) -> User:
        now = datetime.now(UTC)
        user = User(
            id=f"usr_{uuid4().hex}",
            organization_id=organization_id,
            email=email.lower(),
            display_name=display_name,
            role=role,
            status=status,
            hashed_password=hashed_password,
            created_at=now,
            updated_at=now,
        )
        self.store.users[user.id] = user
        return user

    async def find_by_email(self, email: str) -> User | None:
        normalized_email = email.lower()
        return next(
            (user for user in self.store.users.values() if user.email == normalized_email),
            None,
        )

    async def find_by_id(self, user_id: str) -> User | None:
        return self.store.users.get(user_id)


@app.get("/tests/rbac/org-admin")
async def org_admin_only(
    current_user: Annotated[User, Depends(require_roles(Role.ORG_ADMIN))],
) -> dict[str, str]:
    return {"user_id": current_user.id}


@pytest.fixture(autouse=True)
def clear_settings_cache() -> Iterator[None]:
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


@pytest.fixture
def store() -> AuthStore:
    return AuthStore()


@pytest.fixture
def client(store: AuthStore) -> Iterator[TestClient]:
    app.dependency_overrides[get_user_repository] = lambda: FakeUserRepository(store)
    app.dependency_overrides[get_organization_repository] = (
        lambda: FakeOrganizationRepository(store)
    )
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


def register_user(
    client: TestClient,
    *,
    email: str = "alice@example.com",
    password: str = "password123",
    organization_id: str | None = None,
) -> dict:
    payload = {
        "email": email,
        "password": password,
        "display_name": "Alice Analyst",
    }
    if organization_id is None:
        payload["organization_name"] = "Acme Security"
    else:
        payload["organization_id"] = organization_id

    response = client.post("/api/auth/register", json=payload)
    assert response.status_code == 201
    return response.json()


def test_register_success(client: TestClient, store: AuthStore) -> None:
    body = register_user(client)

    assert body["token_type"] == "bearer"
    assert body["access_token"]
    assert body["refresh_token"]
    assert body["user"]["email"] == "alice@example.com"
    assert body["user"]["role"] == Role.ORG_ADMIN
    assert body["organization"]["name"] == "Acme Security"

    stored_user = next(iter(store.users.values()))
    assert stored_user.hashed_password != "password123"


def test_duplicate_email_rejected(client: TestClient) -> None:
    register_user(client)

    response = client.post(
        "/api/auth/register",
        json={
            "email": "alice@example.com",
            "password": "password123",
            "display_name": "Alice Duplicate",
            "organization_name": "Acme Security",
        },
    )

    assert response.status_code == 409


@pytest.mark.parametrize("prefix", ["/api", "/api/v1"])
def test_login_success_at_supported_api_prefixes(client: TestClient, prefix: str) -> None:
    registered = register_user(client)

    response = client.post(
        f"{prefix}/auth/login",
        json={"email": "alice@example.com", "password": "password123"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["access_token"]
    assert body["refresh_token"]
    assert body["user"]["id"] == registered["user"]["id"]
    assert "hashed_password" not in body["user"]


def test_versioned_auth_register_and_login(client: TestClient) -> None:
    register_response = client.post(
        "/api/v1/auth/register",
        json={
            "email": "versioned@example.com",
            "password": "password123",
            "display_name": "Versioned Analyst",
            "organization_name": "Versioned Security",
        },
    )
    assert register_response.status_code == 201

    login_response = client.post(
        "/api/v1/auth/login",
        json={"email": "versioned@example.com", "password": "password123"},
    )

    assert login_response.status_code == 200
    assert login_response.json()["access_token"]


def test_login_wrong_password_rejected(client: TestClient) -> None:
    register_user(client)

    response = client.post(
        "/api/auth/login",
        json={"email": "alice@example.com", "password": "wrong-password"},
    )

    assert response.status_code == 401


def test_me_requires_auth(client: TestClient) -> None:
    response = client.get("/api/auth/me")

    assert response.status_code == 401


def test_me_returns_user(client: TestClient) -> None:
    registered = register_user(client)

    response = client.get(
        "/api/auth/me",
        headers={"Authorization": f"Bearer {registered['access_token']}"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["user"]["email"] == "alice@example.com"
    assert body["user"]["organization_id"] == registered["organization"]["id"]
    assert body["organization"]["id"] == registered["organization"]["id"]


def test_refresh_returns_new_access_token(client: TestClient) -> None:
    registered = register_user(client)

    response = client.post(
        "/api/auth/refresh",
        json={"refresh_token": registered["refresh_token"]},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["access_token"]
    assert body["access_token"] != registered["access_token"]
    assert body["token_type"] == "bearer"


def test_disabled_user_blocked(client: TestClient, store: AuthStore) -> None:
    registered = register_user(client)
    user = store.users[registered["user"]["id"]]
    store.users[user.id] = user.model_copy(update={"status": UserStatus.DISABLED})

    login_response = client.post(
        "/api/auth/login",
        json={"email": "alice@example.com", "password": "password123"},
    )
    me_response = client.get(
        "/api/auth/me",
        headers={"Authorization": f"Bearer {registered['access_token']}"},
    )

    assert login_response.status_code == 403
    assert me_response.status_code == 403


def test_rbac_role_dependency_works(client: TestClient) -> None:
    org_admin = register_user(client)
    viewer = register_user(
        client,
        email="viewer@example.com",
        organization_id=org_admin["organization"]["id"],
    )

    admin_response = client.get(
        "/tests/rbac/org-admin",
        headers={"Authorization": f"Bearer {org_admin['access_token']}"},
    )
    viewer_response = client.get(
        "/tests/rbac/org-admin",
        headers={"Authorization": f"Bearer {viewer['access_token']}"},
    )

    assert admin_response.status_code == 200
    assert viewer_response.status_code == 403
