from __future__ import annotations

import uuid

from sqlalchemy import exists, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User


class UserRepository:
    """
    Repository responsible for User persistence.

    This class contains only database operations.

    It must never:
        - contain business logic
        - call external services
        - perform authentication
        - commit or rollback transactions
    """

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(self, user: User) -> User:
        """
        Persist a new user.

        The transaction is not committed here.
        """

        self.session.add(user)

        await self.session.flush()
        await self.session.refresh(user)

        return user

    async def get_by_id(
        self,
        user_id: uuid.UUID,
    ) -> User | None:
        """
        Retrieve a user by primary key.
        """

        statement = select(User).where(User.id == user_id)

        result = await self.session.execute(statement)

        return result.scalar_one_or_none()

    async def get_by_email(
        self,
        email: str,
    ) -> User | None:
        """
        Retrieve a user by email.
        """

        statement = select(User).where(User.email == email)

        result = await self.session.execute(statement)

        return result.scalar_one_or_none()

    async def get_by_provider_user_id(
        self,
        provider_user_id: str,
    ) -> User | None:
        """
        Retrieve a user by identity provider user ID.
        """

        statement = select(User).where(
            User.provider_user_id == provider_user_id,
        )

        result = await self.session.execute(statement)

        return result.scalar_one_or_none()

    async def exists_by_email(
        self,
        email: str,
    ) -> bool:
        """
        Check whether a user exists by email.
        """

        statement = select(
            exists().where(User.email == email),
        )

        result = await self.session.scalar(statement)

        return bool(result)

    async def update(
        self,
        user: User,
    ) -> User:
        """
        Flush pending changes.

        The transaction is not committed here.
        """

        await self.session.flush()
        await self.session.refresh(user)

        return user

    async def delete(
        self,
        user: User,
    ) -> None:
        """
        Delete a user.

        The transaction is not committed here.
        """

        await self.session.delete(user)

        await self.session.flush()
