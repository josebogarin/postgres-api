import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import hash_password
from app.models.user import User
from app.models.application import Application


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
async def superuser(db_session: AsyncSession) -> User:
    user = User(
        email="apps_admin@example.com",
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
        json={"email": "apps_admin@example.com", "password": "admin1234"},
    )
    assert response.status_code == 200
    return response.json()["access_token"]


@pytest.fixture
async def existing_application(db_session: AsyncSession) -> Application:
    app = Application(
        slug="existing-app",
        name="Existing Application",
        description="Pre-existing app for tests",
        is_active=True,
    )
    db_session.add(app)
    await db_session.flush()
    await db_session.refresh(app)
    return app


# ---------------------------------------------------------------------------
# test_create_application
# ---------------------------------------------------------------------------

async def test_create_application(client: AsyncClient, superuser_token: str):
    response = await client.post(
        "/api/v1/applications/",
        json={
            "slug": "my-new-app",
            "name": "My New Application",
            "description": "Test app",
            "is_active": True,
        },
        headers={"Authorization": f"Bearer {superuser_token}"},
    )
    assert response.status_code == 201
    data = response.json()
    assert data["slug"] == "my-new-app"
    assert data["name"] == "My New Application"
    assert data["is_active"] is True
    assert "id" in data


# ---------------------------------------------------------------------------
# test_slug_unique
# ---------------------------------------------------------------------------

async def test_slug_unique(
    client: AsyncClient, superuser_token: str, existing_application: Application
):
    """Posting with a duplicate slug must return 409 Conflict."""
    response = await client.post(
        "/api/v1/applications/",
        json={
            "slug": "existing-app",
            "name": "Duplicate Slug App",
            "is_active": True,
        },
        headers={"Authorization": f"Bearer {superuser_token}"},
    )
    assert response.status_code == 409


# ---------------------------------------------------------------------------
# test_list_applications
# ---------------------------------------------------------------------------

async def test_list_applications(
    client: AsyncClient, superuser_token: str, existing_application: Application
):
    response = await client.get(
        "/api/v1/applications/",
        headers={"Authorization": f"Bearer {superuser_token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    slugs = [item["slug"] for item in data]
    assert "existing-app" in slugs
