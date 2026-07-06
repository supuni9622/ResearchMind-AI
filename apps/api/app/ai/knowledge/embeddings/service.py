"""
Embedding service.

The EmbeddingService orchestrates the embedding generation workflow.

It is responsible for:

- validating inputs
- resolving the requested embedding provider
- delegating embedding generation
- returning the generated embeddings

The service contains no embedding algorithm itself.

Concrete embedding logic lives entirely inside provider implementations.
"""

from __future__ import annotations

from app.ai.knowledge.chunking.artifacts.models import ChunkArtifact
from app.ai.knowledge.embeddings.enums import EmbeddingProvider
from app.ai.knowledge.embeddings.exceptions import (
    EmbeddingValidationError,
)
from app.ai.knowledge.embeddings.models import Embedding
from app.ai.knowledge.embeddings.registry import EmbeddingRegistry


class EmbeddingService:
    """
    Orchestrates embedding generation.

    The service is intentionally lightweight and depends only on the
    EmbeddingRegistry. This keeps the orchestration layer independent
    from concrete embedding implementations.
    """

    def __init__(
        self,
        registry: EmbeddingRegistry,
    ) -> None:
        self._registry = registry

    async def embed(
        self,
        artifact: ChunkArtifact,
        provider: EmbeddingProvider,
    ) -> list[Embedding]:
        """
        Generate embeddings using the requested provider.

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

        return await embedding_provider.embed(artifact)

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
