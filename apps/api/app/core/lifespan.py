from contextlib import asynccontextmanager
from fastapi import FastAPI
from app.core.logging import configure_logging


@asynccontextmanager
async def lifespan(app: FastAPI):
    configure_logging()

    print("🚀 ResearchMind API starting...")

    yield

    print("🛑 ResearchMind API shutting down...")


# Later this file will initialize:

# PostgreSQL
# Valkey
# Qdrant
# LangSmith
# OpenTelemetry