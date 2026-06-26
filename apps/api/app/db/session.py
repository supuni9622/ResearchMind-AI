from collections.abc import AsyncGenerator

from fastapi import Request
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
)


def get_session_factory(
    engine: AsyncEngine,
) -> async_sessionmaker[AsyncSession]:
    return async_sessionmaker(
        bind=engine,
        autoflush=False,
        expire_on_commit=False,
    )


async def get_db(
    request: Request,
) -> AsyncGenerator[AsyncSession, None]:
    session_factory = get_session_factory(request.app.state.postgres_engine)

    async with session_factory() as session:
        yield session
