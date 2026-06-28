from __future__ import annotations

import structlog
from fastapi import Request
from sqlalchemy import text

logger = structlog.get_logger()


async def postgres_health(request: Request) -> str:
    try:
        async with request.app.state.postgres_engine.begin() as conn:
            await conn.execute(text("SELECT 1"))
        return "healthy"
    except Exception as exc:
        logger.warning("health.postgres_unhealthy", reason=str(exc))
        return "unhealthy"


async def valkey_health(request: Request) -> str:
    try:
        await request.app.state.valkey.ping()
        return "healthy"
    except Exception as exc:
        logger.warning("health.valkey_unhealthy", reason=str(exc))
        return "unhealthy"


async def qdrant_health(request: Request) -> str:
    try:
        await request.app.state.qdrant.get_collections()
        return "healthy"
    except Exception as exc:
        logger.warning("health.qdrant_unhealthy", reason=str(exc))
        return "unhealthy"


async def get_health_status(request: Request) -> dict:
    postgres = await postgres_health(request)
    valkey = await valkey_health(request)
    qdrant = await qdrant_health(request)

    overall = "healthy" if all(s == "healthy" for s in (postgres, valkey, qdrant)) else "unhealthy"

    if overall == "unhealthy":
        logger.warning(
            "health.degraded",
            postgres=postgres,
            valkey=valkey,
            qdrant=qdrant,
        )

    return {
        "status": overall,
        "services": {
            "postgres": postgres,
            "valkey": valkey,
            "qdrant": qdrant,
        },
    }
