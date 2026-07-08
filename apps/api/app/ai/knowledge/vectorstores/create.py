"""
Vector Store Platform composition root.

Assembles the Vector Store Platform by registering all available vector
store providers and constructing the VectorStoreService.

This module is the single composition root for the Vector Store Platform.

Adding a new vector store provider should require only registering the
provider here without modifying the rest of the application.
"""

from __future__ import annotations

from qdrant_client import AsyncQdrantClient

from app.ai.knowledge.vectorstores.config import (
    QdrantVectorStoreConfig,
)
from app.ai.knowledge.vectorstores.interfaces import (
    VectorStoreProviderInterface,
)
from app.ai.knowledge.vectorstores.providers.qdrant import (
    QdrantVectorStoreProvider,
)
from app.ai.knowledge.vectorstores.registry import (
    VectorStoreRegistry,
)
from app.ai.knowledge.vectorstores.service import (
    VectorStoreService,
)
from app.core.settings import settings


def create_qdrant_client() -> AsyncQdrantClient:
    """
    Create a configured Qdrant client.

    This centralizes SDK client construction so that providers remain
    independent from application configuration.
    """

    return AsyncQdrantClient(
        url=settings.qdrant_url,
    )


def create_vectorstore_registry() -> VectorStoreRegistry:
    """
    Create a fully configured VectorStoreRegistry.

    This is the single place where vector store providers are
    constructed and registered.
    """

    registry = VectorStoreRegistry()

    qdrant_client = create_qdrant_client()

    providers: list[VectorStoreProviderInterface] = [
        QdrantVectorStoreProvider(
            config=QdrantVectorStoreConfig(
                collection_name=settings.qdrant_collection_name,
            ),
            client=qdrant_client,
        ),
    ]

    for provider in providers:
        registry.register(provider)

    return registry


def create_vectorstore_service() -> VectorStoreService:
    """
    Create a fully configured VectorStoreService.
    """

    return VectorStoreService(
        registry=create_vectorstore_registry(),
    )
