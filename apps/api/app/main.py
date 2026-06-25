from fastapi import FastAPI
from app.core.settings import settings

app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
)


@app.get("/")
async def root():
    return {
        "application": settings.app_name,
        "version": settings.app_version,
    }


@app.get("/health")
async def health():
    return {
        "status": "healthy",
        "environment": settings.environment,
    }