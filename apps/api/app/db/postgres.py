from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine

from app.core.settings import settings


def create_postgres_engine() -> AsyncEngine:
    """
    Create the application's PostgreSQL engine.

    The engine is created during the FastAPI lifespan startup
    and disposed during shutdown.
    """

    return create_async_engine(
        settings.database_url.replace("psycopg", "asyncpg"),
        echo=settings.environment == "development",
        future=True,
        pool_pre_ping=True,
    )