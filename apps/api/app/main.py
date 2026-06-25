from fastapi import FastAPI

from app.api.v1.api import api_router
from app.core.lifespan import lifespan
from app.core.settings import settings

app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    lifespan=lifespan,
)

app.include_router(
    api_router,
    prefix="/api/v1",
)