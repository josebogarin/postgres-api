"""Run: python -m scripts.create_superuser"""

import asyncio
import getpass

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import AsyncSessionLocal
from app.services.user import create_user
from app.schemas.user import UserCreate


async def main() -> None:
    email = input("Email: ").strip()
    password = getpass.getpass("Password: ")
    full_name = input("Full name: ").strip()

    async with AsyncSessionLocal() as session:
        user = await create_user(
            session,
            user_in=UserCreate(
                email=email,
                password=password,
                full_name=full_name,
                is_superuser=True,
            ),
        )
        await session.commit()
        print(f"Superuser created: {user.email} (id={user.id})")


if __name__ == "__main__":
    asyncio.run(main())
