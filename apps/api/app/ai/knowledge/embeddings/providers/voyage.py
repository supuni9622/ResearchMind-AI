"""
Voyage AI embedding provider.

This provider generates dense vector embeddings using the Voyage AI API
while exposing only canonical Embedding models to the rest of the
Knowledge Platform.

Voyage AI is intentionally encapsulated within this provider so that the
remainder of the application remains framework-independent.
"""

from __future__ import annotations

import structlog
from app.ai.knowledge.chunking.artifacts.models import ChunkArtifact
from app.ai.knowledge.embeddings.base import BaseEmbeddingProvider
from app.ai.knowledge.embeddings.batching import EmbeddingBatcher
from app.ai.knowledge.embeddings.config import VoyageAIEmbeddingConfig
from app.ai.knowledge.embeddings.enums import EmbeddingProvider
from app.ai.knowledge.embeddings.factory import EmbeddingFactory
from app.ai.knowledge.embeddings.models import Embedding
from voyageai.client import Client as VoyageAIClient

logger = structlog.get_logger()


class VoyageAIEmbeddingProvider(
    BaseEmbeddingProvider[VoyageAIEmbeddingConfig],
):
    """
    Voyage AI embedding provider.

    Generates dense vector embeddings for canonical chunks.
    """

    def __init__(
        self,
        config: VoyageAIEmbeddingConfig,
        client: VoyageAIClient,
    ) -> None:
        super().__init__(config)

        self._client = client

    @property
    def provider(self) -> EmbeddingProvider:
        """
        Provider identifier.
        """

        return EmbeddingProvider.VOYAGE_AI

    @property
    def model(self) -> str:
        """
        Configured embedding model.
        """

        return self.config.model_name

    async def embed(
        self,
        artifact: ChunkArtifact,
    ) -> list[Embedding]:
        """
        Generate embeddings for every chunk in the supplied chunk artifact.

        Args:
            artifact:
                Canonical chunk artifact.

        Returns:
            Canonical embeddings.
        """

        chunks = artifact.chunks

        logger.info(
            "embedding.voyage.started",
            provider=self.provider.value,
            model=self.model,
            chunk_count=len(chunks),
            batch_size=self.config.batch_size,
        )

        batcher = EmbeddingBatcher(
            batch_size=self.config.batch_size,
        )

        embeddings: list[Embedding] = []

        for batch_chunks in batcher.batch(chunks):
            batch_texts = [chunk.content.text for chunk in batch_chunks]

            response = self._client.embed(
                texts=batch_texts,
                model=self.model,
                input_type=self.config.input_type,
            )

            logger.debug(
                "embedding.voyage.batch",
                provider=self.provider.value,
                batch_size=len(batch_chunks),
            )

            batch_vectors: list[list[float]] = [
                [float(value) for value in vector] for vector in response.embeddings
            ]

            embeddings.extend(
                [
                    EmbeddingFactory.from_vector(
                        chunk=chunk,
                        vector=vector,
                        provider=self.provider,
                        model=self.model,
                        provider_version=self.version,
                        configuration_fingerprint=self.configuration_fingerprint,
                    )
                    for chunk, vector in zip(
                        batch_chunks,
                        batch_vectors,
                        strict=True,
                    )
                ]
            )

        logger.info(
            "embedding.voyage.completed",
            provider=self.provider.value,
            model=self.model,
            embedding_count=len(embeddings),
            dimensions=embeddings[0].vector.dimensions if embeddings else 0,
        )

        return embeddings
