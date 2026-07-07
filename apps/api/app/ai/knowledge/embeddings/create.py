"""
Embedding Platform composition root.

Assembles the Embedding Platform by registering all available embedding
providers and constructing the EmbeddingService.

This module is the single composition root for the Embedding Platform.

Adding a new embedding provider should require only registering the
provider here without modifying the rest of the application.
"""

from __future__ import annotations

from openai import OpenAI
from voyageai.client import Client as VoyageAIClient

from app.ai.knowledge.embeddings.config import (
    OpenAIEmbeddingConfig,
    SentenceTransformerEmbeddingConfig,
    VoyageAIEmbeddingConfig,
)
from app.ai.knowledge.embeddings.interfaces import EmbeddingProvider
from app.ai.knowledge.embeddings.providers.openai import (
    OpenAIEmbeddingProvider,
)
from app.ai.knowledge.embeddings.providers.sentence_transformers import (
    SentenceTransformerEmbeddingProvider,
)
from app.ai.knowledge.embeddings.providers.voyage import (
    VoyageAIEmbeddingProvider,
)
from app.ai.knowledge.embeddings.registry import EmbeddingRegistry
from app.ai.knowledge.embeddings.service import EmbeddingService
from app.core.settings import settings


def create_voyage_client() -> VoyageAIClient:
    """
    Create a configured Voyage AI client.

    This centralizes SDK client construction so that providers remain
    independent from application configuration.
    """

    return VoyageAIClient(
        api_key=settings.voyage_api_key,
    )


def create_openai_client() -> OpenAI:
    """
    Create a configured OpenAI client.

    This centralizes SDK client construction so that providers remain
    independent from application configuration.
    """

    return OpenAI(
        api_key=settings.openai_api_key,
    )


def create_embedding_registry() -> EmbeddingRegistry:
    """
    Create a fully configured EmbeddingRegistry.

    This is the single place where embedding providers are constructed
    and registered. Both create_embedding_service() and the Benchmark
    Platform depend on this function rather than duplicating provider
    construction.
    """

    registry = EmbeddingRegistry()

    voyage_client = create_voyage_client()
    openai_client = create_openai_client()

    providers: list[EmbeddingProvider] = [
        SentenceTransformerEmbeddingProvider(
            SentenceTransformerEmbeddingConfig(),
        ),
        VoyageAIEmbeddingProvider(
            config=VoyageAIEmbeddingConfig(),
            client=voyage_client,
        ),
        OpenAIEmbeddingProvider(
            config=OpenAIEmbeddingConfig(),
            client=openai_client,
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
