import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import hash_password
from app.models.user import User


@pytest.fixture
async def superuser(db_session: AsyncSession) -> User:
    user = User(
        email="admin@example.com",
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
        json={"email": "admin@example.com", "password": "admin1234"},
    )
    return response.json()["access_token"]


async def test_create_user(client: AsyncClient, superuser_token: str):
    response = await client.post(
        "/api/v1/users/",
        json={"email": "new@example.com", "password": "newpass99", "full_name": "New User"},
        headers={"Authorization": f"Bearer {superuser_token}"},
    )
    assert response.status_code == 201
    assert response.json()["email"] == "new@example.com"


async def test_duplicate_user_fails(client: AsyncClient, superuser_token: str):
    payload = {"email": "dup@example.com", "password": "pass1234"}
    await client.post(
        "/api/v1/users/",
        json=payload,
        headers={"Authorization": f"Bearer {superuser_token}"},
    )
    response = await client.post(
        "/api/v1/users/",
        json=payload,
        headers={"Authorization": f"Bearer {superuser_token}"},
    )
    assert response.status_code == 409
