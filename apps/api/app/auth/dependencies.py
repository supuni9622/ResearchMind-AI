# FastAPI Dependencies
from __future__ import annotations

from functools import lru_cache

import structlog
from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.jwt import JWTVerifier
from app.auth.providers.cognito import CognitoAuthenticationProvider
from app.db.session import get_db
from app.exceptions.base import UnauthorizedException
from app.models.user import User
from app.services.user import UserService

security = HTTPBearer(auto_error=False)


@lru_cache
def get_jwt_verifier() -> JWTVerifier:
    return JWTVerifier(CognitoAuthenticationProvider())


async def authenticate_token(
    token: str,
    session: AsyncSession,
) -> User:
    """
    Verifies a bearer token and returns the synced ResearchMind user.

    Shared by `get_current_user` (HTTP, token from the `Authorization`
    header) and the chat WebSocket route (`?token=` query param, since a
    browser's WebSocket handshake can't set a custom header) so both
    authenticate identically instead of duplicating this flow.
    """

    claims = await get_jwt_verifier().verify(
        token,
    )

    service = UserService(session)

    user = await service.sync_user(
        auth_provider=claims["provider"],
        provider_user_id=claims["provider_user_id"],
        email=claims["email"],
        username=claims.get("username"),
        full_name=claims.get("full_name"),
        avatar_url=claims.get("avatar_url"),
        is_verified=claims.get("email_verified", False),
    )

    await service.update_last_login(user)

    # Bind user_id to the request context so all downstream logs carry it.
    structlog.contextvars.bind_contextvars(user_id=str(user.id))

    return user


async def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(security),
    session: AsyncSession = Depends(get_db),
) -> User:
    """
    Authenticate the current request and return
    the authenticated ResearchMind user.
    """

    if credentials is None:
        raise UnauthorizedException(
            message="Authentication credentials were not provided.",
        )

    return await authenticate_token(
        credentials.credentials,
        session,
    )
