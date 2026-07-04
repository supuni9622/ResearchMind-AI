"""
Database session management.

This module owns the application's SQLAlchemy engine and session
factory. Both the FastAPI application and background workers reuse the
same configuration.
"""

from __future__ import annotations

from collections.abc import AsyncGenerator

from fastapi import Request
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.core.settings import settings

# ----------------------------------------------------------------------
# Shared Engine
# ----------------------------------------------------------------------

engine: AsyncEngine = create_async_engine(
    settings.database_url,
    pool_pre_ping=True,
)

# ----------------------------------------------------------------------
# Shared Session Factory
# ----------------------------------------------------------------------

SessionFactory = async_sessionmaker(
    bind=engine,
    autoflush=False,
    expire_on_commit=False,
)


def get_session_factory(
    engine: AsyncEngine,
) -> async_sessionmaker[AsyncSession]:
    """
    Create a session factory for the supplied engine.

    Primarily retained for testing where a custom engine may be injected.
    """

    return async_sessionmaker(
        bind=engine,
        autoflush=False,
        expire_on_commit=False,
    )


# async def get_db(
#     request: Request,
# ) -> AsyncGenerator[AsyncSession, None]:
#     """
#     FastAPI database dependency.

#     If the application has registered its own engine during startup,
#     use that. Otherwise fall back to the shared engine.
#     """

#     engine = getattr(
#         request.app.state,
#         "postgres_engine",
#         None,
#     )

#     session_factory = get_session_factory(engine) if engine is not None else SessionFactory

#     async with session_factory() as session:
#         yield session


async def get_db(
    _: Request,  # required by FastAPI, even if unused
) -> AsyncGenerator[AsyncSession, None]:
    """
    FastAPI database dependency.
    """

    async with SessionFactory() as session:
        yield session
