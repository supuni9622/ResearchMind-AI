"""
OpenAI embedding provider.

This provider generates dense vector embeddings using the OpenAI API
while exposing only canonical Embedding models to the rest of the
Knowledge Platform.

OpenAI is intentionally encapsulated within this provider so that the
remainder of the application remains framework-independent.
"""

from __future__ import annotations

import structlog
from app.ai.knowledge.chunking.artifacts.models import ChunkArtifact
from app.ai.knowledge.embeddings.base import BaseEmbeddingProvider
from app.ai.knowledge.embeddings.batching import EmbeddingBatcher
from app.ai.knowledge.embeddings.config import OpenAIEmbeddingConfig
from app.ai.knowledge.embeddings.enums import EmbeddingProvider
from app.ai.knowledge.embeddings.factory import EmbeddingFactory
from app.ai.knowledge.embeddings.models import Embedding
from openai import OpenAI

logger = structlog.get_logger()


class OpenAIEmbeddingProvider(
    BaseEmbeddingProvider[OpenAIEmbeddingConfig],
):
    """
    OpenAI embedding provider.

    Generates dense vector embeddings for canonical chunks.
    """

    def __init__(
        self,
        config: OpenAIEmbeddingConfig,
        client: OpenAI,
    ) -> None:
        super().__init__(config)

        self._client = client

    @property
    def provider(self) -> EmbeddingProvider:
        """
        Provider identifier.
        """

        return EmbeddingProvider.OPENAI

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
            "embedding.openai.started",
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

            logger.debug(
                "embedding.openai.batch",
                provider=self.provider.value,
                batch_size=len(batch_chunks),
            )

            response = self._client.embeddings.create(
                model=self.model,
                input=batch_texts,
            )

            embeddings.extend(
                [
                    EmbeddingFactory.from_vector(
                        chunk=chunk,
                        vector=result.embedding,
                        provider=self.provider,
                        model=self.model,
                        provider_version=self.version,
                        configuration_fingerprint=self.configuration_fingerprint,
                    )
                    for chunk, result in zip(
                        batch_chunks,
                        response.data,
                        strict=True,
                    )
                ]
            )

        logger.info(
            "embedding.openai.completed",
            provider=self.provider.value,
            model=self.model,
            embedding_count=len(embeddings),
            dimensions=embeddings[0].vector.dimensions if embeddings else 0,
        )

        return embeddings
