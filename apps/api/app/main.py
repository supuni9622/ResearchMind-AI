from fastapi import FastAPI

from app.api.v1.api import api_router
from app.core.constants import (
    API_V1_PREFIX,
    APP_DESCRIPTION,
    APP_NAME,
    APP_VERSION,
)
from app.core.lifespan import lifespan
from app.core.setup import configure_application

app = FastAPI(
    title=APP_NAME,
    description=APP_DESCRIPTION,
    version=APP_VERSION,
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
)

configure_application(app)

app.include_router(
    api_router,
    prefix=API_V1_PREFIX,
)
