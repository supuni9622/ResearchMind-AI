from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.core.logging import configure_logging
from app.db.postgres import create_postgres_engine
from app.db.qdrant import create_qdrant_client
from app.db.valkey import create_valkey_client


@asynccontextmanager
async def lifespan(app: FastAPI):
    configure_logging()

    print("🚀 Starting ResearchMind...")

    # PostgreSQL
    app.state.postgres_engine = create_postgres_engine()

    # Valkey
    app.state.valkey = create_valkey_client()

    # Qdrant
    app.state.qdrant = create_qdrant_client()

    print("✅ Infrastructure initialized.")

    yield

    print("🛑 Shutting down ResearchMind...")

    await app.state.postgres_engine.dispose()
    await app.state.valkey.aclose()
    await app.state.qdrant.close()

    print("✅ Infrastructure shutdown complete.")