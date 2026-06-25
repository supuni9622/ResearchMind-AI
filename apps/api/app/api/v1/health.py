from fastapi import APIRouter, Request

from app.core.health import get_health_status

router = APIRouter(tags=["Health"])


@router.get("/live")
async def live():
    return {"status": "alive"}


@router.get("/ready")
async def ready():
    return {"status": "ready"}


@router.get("/health")
async def health(request: Request):
    return await get_health_status(request)


# Why /live, /ready, /health?

# These are standard production patterns:

# Endpoint	Purpose
# /live	    - Is the application process running?
# /ready	- Can it receive requests?
# /health	- Are dependencies healthy?

# This will pay off later when we deploy with Docker, Kubernetes, or cloud platforms.