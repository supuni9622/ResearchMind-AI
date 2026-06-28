import asyncio
from contextlib import asynccontextmanager

import structlog
from alembic.config import Config
from fastapi import FastAPI

from alembic import command
from app.core.logging import configure_logging
from app.core.settings import settings
from app.db.postgres import create_postgres_engine
from app.db.qdrant import create_qdrant_client
from app.db.valkey import create_valkey_client

logger = structlog.get_logger()


def _run_migrations() -> None:
    cfg = Config("alembic.ini")
    command.upgrade(cfg, "head")


@asynccontextmanager
async def lifespan(app: FastAPI):
    configure_logging()

    logger.info("Starting ResearchMind")

    if settings.auto_migrate:
        logger.info("db.migrations_starting")
        await asyncio.to_thread(_run_migrations)
        logger.info("db.migrations_complete")

    app.state.postgres_engine = create_postgres_engine()
    app.state.valkey = create_valkey_client()
    app.state.qdrant = create_qdrant_client()

    logger.info("Infrastructure initialized")

    yield

    logger.info("Shutting down ResearchMind")

    await app.state.postgres_engine.dispose()
    await app.state.valkey.aclose()
    await app.state.qdrant.close()

    logger.info("Infrastructure shutdown complete")
