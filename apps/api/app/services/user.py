from __future__ import annotations

import uuid
from datetime import UTC, datetime

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from app.exceptions.base import ConflictException, NotFoundException
from app.models.user import User
from app.repositories import UserRepository

logger = structlog.get_logger()


class UserService:
    """
    Service responsible for User business logic.

    Services coordinate repositories,
    enforce business rules,
    and manage database transactions.
    """

    def __init__(
        self,
        session: AsyncSession,
    ) -> None:
        self.session = session
        self.repository = UserRepository(session)

    async def create_user(
        self,
        *,
        auth_provider: str,
        provider_user_id: str,
        email: str,
        username: str | None = None,
        full_name: str | None = None,
        avatar_url: str | None = None,
        is_verified: bool = False,
    ) -> User:
        """
        Create a new ResearchMind user.
        """

        if await self.repository.exists_by_email(email):
            raise ConflictException(
                message=f"User with email '{email}' already exists.",
            )

        user = User(
            auth_provider=auth_provider,
            provider_user_id=provider_user_id,
            email=email,
            username=username,
            full_name=full_name,
            avatar_url=avatar_url,
            is_verified=is_verified,
        )

        user = await self.repository.create(user)

        await self.session.commit()

        logger.info("user.created", user_id=str(user.id), provider=auth_provider)

        return user

    async def get_user_by_id(
        self,
        user_id: uuid.UUID,
    ) -> User:
        """
        Retrieve a user by ID.
        """

        user = await self.repository.get_by_id(user_id)

        if user is None:
            logger.warning("user.not_found", lookup="id", user_id=str(user_id))
            raise NotFoundException(message="User not found.")

        return user

    async def get_user_by_email(
        self,
        email: str,
    ) -> User:
        """
        Retrieve a user by email.
        """

        user = await self.repository.get_by_email(email)

        if user is None:
            logger.warning("user.not_found", lookup="email", email=email)
            raise NotFoundException(message="User not found.")

        return user

    async def sync_user(
        self,
        *,
        auth_provider: str,
        provider_user_id: str,
        email: str,
        username: str | None = None,
        full_name: str | None = None,
        avatar_url: str | None = None,
        is_verified: bool = False,
    ) -> User:
        """
        Synchronize a user from an external identity provider.

        If the user already exists,
        return it.

        Otherwise create a new user.
        """

        user = await self.repository.get_by_provider_user_id(
            provider_user_id,
        )

        if user is not None:
            logger.debug("user.synced", user_id=str(user.id), provider=auth_provider)
            return user

        logger.info("user.first_login", provider=auth_provider, email=email)
        return await self.create_user(
            auth_provider=auth_provider,
            provider_user_id=provider_user_id,
            email=email,
            username=username,
            full_name=full_name,
            avatar_url=avatar_url,
            is_verified=is_verified,
        )

    async def update_last_login(
        self,
        user: User,
    ) -> User:
        """
        Update the user's last login timestamp.
        """

        user.last_login_at = datetime.now(UTC)

        user = await self.repository.update(user)

        await self.session.commit()

        logger.debug("user.last_login_updated", user_id=str(user.id))

        return user

    async def deactivate_user(
        self,
        user: User,
    ) -> User:
        """
        Soft delete (deactivate) a user.
        """

        user.is_active = False

        user = await self.repository.update(user)

        await self.session.commit()

        logger.info("user.deactivated", user_id=str(user.id))

        return user
