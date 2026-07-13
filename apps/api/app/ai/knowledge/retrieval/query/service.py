"""
Query Embedding Service.

Responsible for generating embeddings for retrieval queries.

Query embeddings are intentionally separated from the document
Embedding Platform because search queries may use:

- different models
- different provider APIs
- different input types
- query-specific caching strategies

Future responsibilities:

- query embedding cache
- query rewriting
- HyDE
- multi-query generation
- provider-specific search embeddings
"""

from __future__ import annotations

import structlog
from app.ai.knowledge.cache.query_embeddings.interfaces import (
    QueryEmbeddingCache,
)
from app.ai.knowledge.cache.query_embeddings.key import (
    build_query_embedding_cache_key,
)
from app.ai.knowledge.embeddings.enums import (
    EmbeddingProvider,
)
from app.ai.knowledge.embeddings.providers.openai import (
    OpenAIEmbeddingProvider,
)
from app.ai.knowledge.embeddings.providers.voyage import (
    VoyageAIEmbeddingProvider,
)
from app.ai.knowledge.embeddings.registry import (
    EmbeddingRegistry,
)

logger = structlog.get_logger()


class QueryEmbeddingService:
    """
    Generates embeddings for retrieval queries.
    """

    def __init__(
        self,
        registry: EmbeddingRegistry,
        cache: QueryEmbeddingCache,
    ) -> None:
        self._registry = registry
        self._cache = cache

    async def embed(
        self,
        query: str,
        provider: EmbeddingProvider = (EmbeddingProvider.VOYAGE_AI),
    ) -> list[float]:
        """
        Generate query embedding.
        """

        embedding_provider = self._registry.get(
            provider,
        )

        cache_key = build_query_embedding_cache_key(
            provider=embedding_provider.provider,
            model=embedding_provider.model,
            configuration_fingerprint=(embedding_provider.configuration_fingerprint),
            query=query,
        )

        cached = await self._cache.get(
            cache_key,
        )

        if cached is not None:
            logger.info(
                "retrieval.query_embedding.cache.hit",
                provider=provider.value,
            )

            return cached

        logger.info(
            "retrieval.query_embedding.started",
            provider=provider.value,
        )

        #
        # Temporary implementation.
        #
        # Eventually providers should expose:
        #
        #     embed_query()
        #
        #

        if provider == EmbeddingProvider.VOYAGE_AI and isinstance(
            embedding_provider,
            VoyageAIEmbeddingProvider,
        ):
            voyage_response = embedding_provider._client.embed(
                texts=[query],
                model=embedding_provider.model,
                input_type="query",
            )

            vector = [float(value) for value in voyage_response.embeddings[0]]

        elif provider == EmbeddingProvider.OPENAI and isinstance(
            embedding_provider,
            OpenAIEmbeddingProvider,
        ):
            openai_response = embedding_provider._client.embeddings.create(
                model=embedding_provider.model,
                input=[query],
            )

            vector = [float(value) for value in openai_response.data[0].embedding]

        else:
            raise NotImplementedError(
                f"Provider '{provider}' does not yet support query embeddings."
            )

        await self._cache.set(
            cache_key,
            vector,
        )

        logger.info(
            "retrieval.query_embedding.completed",
            provider=provider.value,
            dimensions=len(vector),
        )

        return vector
