from qdrant_client import AsyncQdrantClient

from app.core.settings import settings


def create_qdrant_client() -> AsyncQdrantClient:
    """
    Create the application's Qdrant client.

    The client is created during FastAPI startup
    and closed during shutdown.
    """

    return AsyncQdrantClient(
        url=settings.qdrant_url,
    )
