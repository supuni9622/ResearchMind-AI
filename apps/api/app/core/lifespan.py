from contextlib import asynccontextmanager
import structlog
from fastapi import FastAPI
from app.core.logging import configure_logging
from app.db.postgres import create_postgres_engine
from app.db.qdrant import create_qdrant_client
from app.db.valkey import create_valkey_client

logger = structlog.get_logger()


@asynccontextmanager
async def lifespan(app: FastAPI):
    configure_logging()

    logger.info("Starting ResearchMind")

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