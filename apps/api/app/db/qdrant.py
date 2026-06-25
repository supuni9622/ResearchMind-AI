#Qdrant client
from qdrant_client import AsyncQdrantClient
from app.core.settings import settings

client = AsyncQdrantClient(
    url=settings.qdrant_url,
)