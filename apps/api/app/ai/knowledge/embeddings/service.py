"""
Embedding service.

The EmbeddingService orchestrates the embedding generation workflow.

It is responsible for:

- validating inputs
- resolving the requested embedding provider
- checking the embedding cache before generating new embeddings
- delegating embedding generation for cache misses
- returning the generated embeddings

The service contains no embedding algorithm itself.

Concrete embedding logic lives entirely inside provider implementations.
"""

from __future__ import annotations

from uuid import UUID

import structlog

from app.ai.knowledge.cache.embeddings.interfaces import EmbeddingCache
from app.ai.knowledge.cache.embeddings.key import build_embedding_cache_key
from app.ai.knowledge.cache.embeddings.null import NullEmbeddingCache
from app.ai.knowledge.chunking.artifacts.models import ChunkArtifact
from app.ai.knowledge.chunking.models import Chunk
from app.ai.knowledge.embeddings.enums import EmbeddingProvider
from app.ai.knowledge.embeddings.exceptions import (
    EmbeddingValidationError,
)
from app.ai.knowledge.embeddings.factory import EmbeddingFactory
from app.ai.knowledge.embeddings.models import Embedding
from app.ai.knowledge.embeddings.registry import EmbeddingRegistry

logger = structlog.get_logger()


class EmbeddingService:
    """
    Orchestrates embedding generation.

    The service depends only on the EmbeddingRegistry and an
    EmbeddingCache, keeping the orchestration layer independent from
    concrete embedding implementations and cache backends.
    """

    def __init__(
        self,
        registry: EmbeddingRegistry,
        cache: EmbeddingCache | None = None,
    ) -> None:
        self._registry = registry
        self._cache = cache or NullEmbeddingCache()

    async def embed(
        self,
        artifact: ChunkArtifact,
        provider: EmbeddingProvider,
    ) -> list[Embedding]:
        """
        Generate embeddings using the requested provider.

        Identical chunk text previously embedded with the same provider,
        model, and configuration is served from the embedding cache
        instead of being re-generated.

        Args:
            chunks:
                Canonical chunks produced by the Chunking Platform.

            provider:
                Embedding provider to use.

        Returns:
            Ordered list of canonical embeddings.
        """

        self._validate(artifact)

        embedding_provider = self._registry.get(provider)

        cache_keys = {
            chunk.id: build_embedding_cache_key(
                provider=embedding_provider.provider,
                model=embedding_provider.model,
                configuration_fingerprint=embedding_provider.configuration_fingerprint,
                text=chunk.content.text,
            )
            for chunk in artifact.chunks
        }

        cached_vectors = await self._cache.get_many(list(cache_keys.values()))

        embeddings_by_chunk_id: dict[UUID, Embedding] = {}
        chunks_to_embed: list[Chunk] = []

        for chunk in artifact.chunks:
            vector = cached_vectors.get(cache_keys[chunk.id])

            if vector is None:
                chunks_to_embed.append(chunk)
                continue

            embeddings_by_chunk_id[chunk.id] = EmbeddingFactory.from_vector(
                chunk=chunk,
                vector=vector,
                provider=embedding_provider.provider,
                model=embedding_provider.model,
                provider_version=embedding_provider.version,
                configuration_fingerprint=embedding_provider.configuration_fingerprint,
            )

        logger.info(
            "embedding.cache.lookup",
            provider=provider.value,
            total=len(artifact.chunks),
            hits=len(embeddings_by_chunk_id),
            misses=len(chunks_to_embed),
        )

        if chunks_to_embed:
            partial_artifact = artifact.model_copy(update={"chunks": chunks_to_embed})

            generated = await embedding_provider.embed(partial_artifact)

            await self._cache.set_many(
                {
                    cache_keys[embedding.provenance.chunk_id]: embedding.vector.values
                    for embedding in generated
                }
            )

            for embedding in generated:
                embeddings_by_chunk_id[embedding.provenance.chunk_id] = embedding

        return [embeddings_by_chunk_id[chunk.id] for chunk in artifact.chunks]

    @staticmethod
    def _validate(
        artifact: ChunkArtifact,
    ) -> None:
        """
        Validate the chunk artifact before embedding generation.
        """

        if not artifact.chunks:
            raise EmbeddingValidationError("Chunk artifact contains no chunks.")

        for chunk in artifact.chunks:
            if not chunk.content.text.strip():
                raise EmbeddingValidationError(f"Chunk '{chunk.id}' contains no text.")
