"""
Sentence Transformers embedding provider.

This provider generates dense vector embeddings using the
SentenceTransformers library while exposing only canonical Embedding
models to the rest of the Knowledge Platform.

SentenceTransformers is intentionally encapsulated within this provider
so that the remainder of the application remains framework-independent.
"""

from __future__ import annotations

import structlog
from app.ai.knowledge.chunking.artifacts.models import ChunkArtifact
from app.ai.knowledge.embeddings.base import BaseEmbeddingProvider
from app.ai.knowledge.embeddings.config import (
    SentenceTransformerEmbeddingConfig,
)
from app.ai.knowledge.embeddings.enums import EmbeddingProvider
from app.ai.knowledge.embeddings.factory import EmbeddingFactory
from app.ai.knowledge.embeddings.models import Embedding
from sentence_transformers import SentenceTransformer

logger = structlog.get_logger()


class SentenceTransformerEmbeddingProvider(
    BaseEmbeddingProvider[SentenceTransformerEmbeddingConfig],
):
    """
    Sentence Transformers embedding provider.

    Generates dense vector embeddings for canonical chunks.
    """

    def __init__(
        self,
        config: SentenceTransformerEmbeddingConfig,
    ) -> None:
        super().__init__(config)

        self._model: SentenceTransformer | None = None

    @property
    def provider(self) -> EmbeddingProvider:
        """
        Provider identifier.
        """

        return EmbeddingProvider.SENTENCE_TRANSFORMERS

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

        model = self._get_model()

        chunks = artifact.chunks

        texts = [chunk.content.text for chunk in chunks]

        logger.info(
            "embedding.sentence_transformers.started",
            provider=self.provider.value,
            model=self.model,
            chunk_count=len(texts),
        )

        vectors = model.encode(
            texts,
            batch_size=self.config.batch_size,
            normalize_embeddings=self.config.normalize_embeddings,
            show_progress_bar=self.config.show_progress_bar,
            convert_to_numpy=self.config.convert_to_numpy,
        )

        embeddings = [
            EmbeddingFactory.from_vector(
                chunk=chunk,
                vector=vector.tolist(),
                provider=self.provider,
                model=self.model,
                provider_version=self.version,
                configuration_fingerprint=self.configuration_fingerprint,
            )
            for chunk, vector in zip(
                chunks,
                vectors,
                strict=True,
            )
        ]

        logger.info(
            "embedding.sentence_transformers.completed",
            provider=self.provider.value,
            model=self.model,
            embedding_count=len(embeddings),
            dimensions=embeddings[0].vector.dimensions if embeddings else 0,
        )

        return embeddings

    def _get_model(
        self,
    ) -> SentenceTransformer:
        """
        Lazily construct and cache the SentenceTransformer model.
        """

        if self._model is None:
            logger.info(
                "embedding.sentence_transformers.loading_model",
                model=self.config.model_name,
                device=self.config.device,
            )

            self._model = SentenceTransformer(
                model_name_or_path=self.config.model_name,
                device=self.config.device,
                trust_remote_code=self.config.trust_remote_code,
            )

        return self._model
