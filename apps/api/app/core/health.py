from typing import Any


async def get_health_status() -> dict[str, Any]:
    return {
        "status": "healthy",
        "services": {
            "postgres": "unknown",
            "valkey": "unknown",
            "qdrant": "unknown",
        },
    }

#Later these will perform actual connection checks.