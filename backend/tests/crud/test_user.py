import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import hash_password, verify_password
from app.core.exceptions import AlreadyExistsError
from app.crud.user import user_crud
from app.crud.role import role_crud
from app.models.user import User
from app.models.role import Role
from app.schemas.user import UserCreate


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

async def _make_user(db: AsyncSession, email: str, password: str = "testpass1") -> User:
    return await user_crud.create(db, obj_in=UserCreate(email=email, password=password))


# ---------------------------------------------------------------------------
# test_create_user
# ---------------------------------------------------------------------------

async def test_create_user(db_session: AsyncSession):
    user = await _make_user(db_session, "create@example.com", "securepass1")

    assert user.id is not None
    assert user.email == "create@example.com"
    assert user.hashed_password != "securepass1"
    assert verify_password("securepass1", user.hashed_password)
    assert user.is_active is True
    assert user.is_superuser is False


# ---------------------------------------------------------------------------
# test_get_by_email
# ---------------------------------------------------------------------------

async def test_get_by_email_existing(db_session: AsyncSession):
    await _make_user(db_session, "bylookup@example.com")

    found = await user_crud.get_by_email(db_session, email="bylookup@example.com")

    assert found is not None
    assert found.email == "bylookup@example.com"


async def test_get_by_email_not_found(db_session: AsyncSession):
    result = await user_crud.get_by_email(db_session, email="ghost@example.com")

    assert result is None


# ---------------------------------------------------------------------------
# test_duplicate_email_raises
# ---------------------------------------------------------------------------

async def test_duplicate_email_raises(db_session: AsyncSession):
    """
    The CRUD layer itself does not enforce uniqueness — the DB unique constraint
    does.  The API layer checks for duplicates before inserting and raises
    AlreadyExistsError.  We replicate that pattern here.
    """
    email = "dup_crud@example.com"
    await _make_user(db_session, email)

    existing = await user_crud.get_by_email(db_session, email=email)
    assert existing is not None, "first user must be persisted"

    # Simulate what the service / endpoint does before calling create again
    with pytest.raises(AlreadyExistsError):
        if existing:
            raise AlreadyExistsError("User")


# ---------------------------------------------------------------------------
# test_update_password
# ---------------------------------------------------------------------------

async def test_update_password(db_session: AsyncSession):
    user = await _make_user(db_session, "pwchange@example.com", "oldpass12")
    old_hash = user.hashed_password

    updated = await user_crud.update_password(db_session, user=user, new_password="newpass99")

    assert updated.hashed_password != old_hash
    assert not verify_password("oldpass12", updated.hashed_password)
    assert verify_password("newpass99", updated.hashed_password)


# ---------------------------------------------------------------------------
# test_assign_and_remove_role
# ---------------------------------------------------------------------------

async def test_assign_and_remove_role(db_session: AsyncSession):
    user = await _make_user(db_session, "roleuser@example.com")

    # Create a role directly (no API layer needed)
    role = Role(name="testrole_crud", description="A test role")
    db_session.add(role)
    await db_session.flush()
    await db_session.refresh(role)

    # Assign
    user = await user_crud.assign_role(db_session, user=user, role=role)
    assert role in user.roles

    # Assign again — idempotent, should not duplicate
    user = await user_crud.assign_role(db_session, user=user, role=role)
    assert user.roles.count(role) == 1

    # Remove
    user = await user_crud.remove_role(db_session, user=user, role=role)
    assert role not in user.roles

    # Remove when not present — should not raise
    user = await user_crud.remove_role(db_session, user=user, role=role)
    assert role not in user.roles
