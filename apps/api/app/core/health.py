from fastapi import Request
from sqlalchemy import text


async def postgres_health(request: Request) -> str:
    try:
        async with request.app.state.postgres_engine.begin() as conn:
            await conn.execute(text("SELECT 1"))
        return "healthy"
    except Exception:
        return "unhealthy"


async def valkey_health(request: Request) -> str:
    try:
        await request.app.state.valkey.ping()
        return "healthy"
    except Exception:
        return "unhealthy"


async def qdrant_health(request: Request) -> str:
    try:
        await request.app.state.qdrant.get_collections()
        return "healthy"
    except Exception:
        return "unhealthy"


async def get_health_status(request: Request):
    postgres = await postgres_health(request)
    valkey = await valkey_health(request)
    qdrant = await qdrant_health(request)

    overall = (
        "healthy"
        if all(
            service == "healthy"
            for service in (postgres, valkey, qdrant)
        )
        else "unhealthy"
    )

    return {
        "status": overall,
        "services": {
            "postgres": postgres,
            "valkey": valkey,
            "qdrant": qdrant,
        },
    }