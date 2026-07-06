"""
Embedding Platform composition root.

Assembles the Embedding Platform by registering all available embedding
providers and constructing the EmbeddingService.

This module is the single composition root for the Embedding Platform.

Adding a new embedding provider should require only registering the
provider here without modifying the rest of the application.
"""

from __future__ import annotations

from app.ai.knowledge.embeddings.config import (
    SentenceTransformerEmbeddingConfig,
)
from app.ai.knowledge.embeddings.interfaces import EmbeddingProvider
from app.ai.knowledge.embeddings.providers.sentence_transformers import (
    SentenceTransformerEmbeddingProvider,
)
from app.ai.knowledge.embeddings.registry import EmbeddingRegistry
from app.ai.knowledge.embeddings.service import EmbeddingService


def create_embedding_registry() -> EmbeddingRegistry:
    """
    Create a fully configured EmbeddingRegistry.

    This is the single place where embedding providers are constructed
    and registered. Both create_embedding_service() and the Benchmark
    Platform depend on this function rather than duplicating provider
    construction.
    """

    registry = EmbeddingRegistry()

    providers: list[EmbeddingProvider] = [
        SentenceTransformerEmbeddingProvider(
            SentenceTransformerEmbeddingConfig(),
        ),
    ]

    for provider in providers:
        registry.register(provider)

    return registry


def create_embedding_service() -> EmbeddingService:
    """
    Create a fully configured EmbeddingService.
    """

    return EmbeddingService(
        registry=create_embedding_registry(),
    )
