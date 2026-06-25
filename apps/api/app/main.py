from fastapi import FastAPI

from app.core.health import get_health_status
from app.core.lifespan import lifespan
from app.core.settings import settings

app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    lifespan=lifespan,
)


@app.get("/")
async def root():
    return {
        "application": settings.app_name,
        "version": settings.app_version,
    }


@app.get("/live")
async def live():
    return {
        "status": "alive",
    }


@app.get("/ready")
async def ready():
    return {
        "status": "ready",
    }


@app.get("/health")
async def health():
    return await get_health_status()




# Why /live, /ready, /health?

# These are standard production patterns:

# Endpoint	Purpose
# /live	    - Is the application process running?
# /ready	- Can it receive requests?
# /health	- Are dependencies healthy?

# This will pay off later when we deploy with Docker, Kubernetes, or cloud platforms.