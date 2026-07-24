import os

# Must run before any `app.*` import: Settings picks .env vs .env.test based
# on this variable at import time. Without it, running plain `pytest` loads
# the dev .env and the test_engine fixture below will create_all/drop_all
# against the real dev database instead of researchmind_test.
os.environ.setdefault("ENVIRONMENT", "test")

from collections.abc import AsyncGenerator, Generator  # noqa: E402

import pytest  # noqa: E402
import pytest_asyncio  # noqa: E402
from app.core.settings import settings  # noqa: E402
from app.db.base import Base  # noqa: E402
from app.main import app  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy.ext.asyncio import (  # noqa: E402
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.pool import NullPool  # noqa: E402


@pytest.fixture(scope="session")
def client() -> Generator[TestClient, None, None]:
    with TestClient(app) as client:
        yield client


@pytest_asyncio.fixture(scope="session")
async def test_engine() -> AsyncGenerator[AsyncEngine, None]:
    engine = create_async_engine(
        settings.database_url.replace("psycopg", "asyncpg"),
        future=True,
        poolclass=NullPool,
    )

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield engine

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

    await engine.dispose()


@pytest_asyncio.fixture(loop_scope="session")
async def db_session(test_engine: AsyncEngine) -> AsyncGenerator[AsyncSession, None]:
    """
    Yield a session scoped to a single outer transaction that is always
    rolled back at the end of the test.

    Application code under test may call `session.commit()` (e.g.
    UserService.create_user). Binding the session to a connection with
    `join_transaction_mode="create_savepoint"` turns those inner commits
    into SAVEPOINT releases instead of real commits, so the outer
    transaction rollback below still discards everything, keeping tests
    isolated from each other and from stale data left by interrupted runs.
    """

    session_factory = async_sessionmaker(
        class_=AsyncSession,
        autoflush=False,
        expire_on_commit=False,
        join_transaction_mode="create_savepoint",
    )

    async with test_engine.connect() as conn:
        await conn.begin()

        async with session_factory(bind=conn) as session:
            yield session

        await conn.rollback()
