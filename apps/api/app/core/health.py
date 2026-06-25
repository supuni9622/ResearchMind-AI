from sqlalchemy import text
from app.db.postgres import engine
from app.db.qdrant import client as qdrant_client
from app.db.valkey import client as valkey_client


async def postgres_health() -> str:
    try:
        async with engine.begin() as conn:
            await conn.execute(text("SELECT 1"))
        return "healthy"
    except Exception:
        return "unhealthy"


async def valkey_health() -> str:
    try:
        await valkey_client.ping()
        return "healthy"
    except Exception:
        return "unhealthy"


async def qdrant_health() -> str:
    try:
        await qdrant_client.get_collections()
        return "healthy"
    except Exception:
        return "unhealthy"


async def get_health_status():
    return {
        "status": "healthy",
        "services": {
            "postgres": await postgres_health(),
            "valkey": await valkey_health(),
            "qdrant": await qdrant_health(),
        },
    }