import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import hash_password
from app.models.user import User
from app.models.role import Role


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
async def superuser(db_session: AsyncSession) -> User:
    user = User(
        email="roles_admin@example.com",
        hashed_password=hash_password("admin1234"),
        is_active=True,
        is_superuser=True,
    )
    db_session.add(user)
    await db_session.flush()
    return user


@pytest.fixture
async def superuser_token(client: AsyncClient, superuser: User) -> str:
    response = await client.post(
        "/api/v1/auth/login",
        json={"email": "roles_admin@example.com", "password": "admin1234"},
    )
    assert response.status_code == 200
    return response.json()["access_token"]


@pytest.fixture
async def existing_role(db_session: AsyncSession) -> Role:
    role = Role(name="existing_role", description="Pre-existing role")
    db_session.add(role)
    await db_session.flush()
    await db_session.refresh(role)
    return role


# ---------------------------------------------------------------------------
# test_list_roles_requires_auth
# ---------------------------------------------------------------------------

async def test_list_roles_requires_auth(client: AsyncClient):
    """Unauthenticated request must be rejected with 401 or 403."""
    response = await client.get("/api/v1/roles/")
    assert response.status_code in (401, 403)


# ---------------------------------------------------------------------------
# test_create_role_as_superuser
# ---------------------------------------------------------------------------

async def test_create_role_as_superuser(client: AsyncClient, superuser_token: str):
    response = await client.post(
        "/api/v1/roles/",
        json={"name": "new_test_role", "description": "Created in test"},
        headers={"Authorization": f"Bearer {superuser_token}"},
    )
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "new_test_role"
    assert data["description"] == "Created in test"
    assert "id" in data


# ---------------------------------------------------------------------------
# test_delete_role
# ---------------------------------------------------------------------------

async def test_delete_role(client: AsyncClient, superuser_token: str, existing_role: Role):
    role_id = str(existing_role.id)

    response = await client.delete(
        f"/api/v1/roles/{role_id}",
        headers={"Authorization": f"Bearer {superuser_token}"},
    )
    assert response.status_code == 204

    # Verify it is gone
    get_response = await client.get(
        "/api/v1/roles/",
        headers={"Authorization": f"Bearer {superuser_token}"},
    )
    ids = [r["id"] for r in get_response.json()]
    assert role_id not in ids
