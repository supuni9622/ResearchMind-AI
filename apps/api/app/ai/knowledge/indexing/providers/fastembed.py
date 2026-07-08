"""
FastEmbed SPLADE sparse embedding provider.

Generates sparse neural retrieval vectors from chunk text using
FastEmbed's SPLADE implementation.

Per ADR-019 (Qdrant Native Hybrid Retrieval), sparse vectors are combined
with Voyage AI dense vectors and indexed into the same Qdrant collection,
enabling hybrid retrieval without a separate BM25 platform.

Unlike dense embedding providers, sparse vector generation is not a
swappable, user-facing business capability. It exists solely to feed
Qdrant's native hybrid search and is therefore owned by the Indexing
Platform rather than the Embedding Platform.

The FastEmbed SDK is intentionally encapsulated within this provider so
that the rest of the Indexing Platform remains framework-independent.
"""

from __future__ import annotations

import asyncio
import hashlib

import structlog
from fastembed import SparseTextEmbedding
from pydantic import BaseModel, ConfigDict, Field

from app.ai.knowledge.indexing.exceptions import SparseEmbeddingError
from app.ai.knowledge.vectorstores.models import SparseVector

logger = structlog.get_logger()


class FastEmbedSparseEmbeddingConfig(BaseModel):
    """
    Configuration for the FastEmbed SPLADE sparse embedding provider.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    model_name: str = Field(
        default="prithivida/Splade_PP_en_v1",
        description="FastEmbed SPLADE model identifier.",
    )

    batch_size: int = Field(
        default=32,
        ge=1,
        description="Maximum number of chunks embedded per local inference batch.",
    )


class FastEmbedSparseEmbeddingProvider:
    """
    Generates sparse SPLADE vectors for Qdrant native hybrid retrieval.
    """

    def __init__(
        self,
        config: FastEmbedSparseEmbeddingConfig,
        model: SparseTextEmbedding | None = None,
    ) -> None:
        self._config = config
        self._model = model or SparseTextEmbedding(model_name=config.model_name)

        self._configuration_fingerprint = hashlib.sha256(
            self._config.model_dump_json().encode("utf-8")
        ).hexdigest()

    @property
    def model(self) -> str:
        """
        Configured sparse embedding model.
        """

        return self._config.model_name

    @property
    def version(self) -> str:
        """
        Version of the provider implementation.
        """

        return "1.0"

    @property
    def config(self) -> FastEmbedSparseEmbeddingConfig:
        """
        Provider configuration.
        """

        return self._config

    @property
    def configuration_fingerprint(self) -> str:
        """
        Stable fingerprint uniquely identifying the provider configuration.
        """

        return self._configuration_fingerprint

    async def embed(
        self,
        texts: list[str],
    ) -> list[SparseVector]:
        """
        Generate sparse SPLADE vectors for the supplied texts.

        The resulting vectors are ordered identically to `texts`.

        FastEmbed inference is synchronous and CPU-bound, so it runs on
        a worker thread to avoid blocking the event loop.
        """

        if not texts:
            return []

        logger.info(
            "indexing.sparse_embedding.fastembed.started",
            model=self.model,
            text_count=len(texts),
        )

        try:
            embeddings = await asyncio.to_thread(
                lambda: list(
                    self._model.embed(
                        texts,
                        batch_size=self._config.batch_size,
                    )
                )
            )

        except Exception as exc:
            logger.exception(
                "indexing.sparse_embedding.fastembed.failed",
                model=self.model,
                text_count=len(texts),
            )

            raise SparseEmbeddingError(
                f"Failed to generate sparse embeddings using '{self.model}'."
            ) from exc

        logger.info(
            "indexing.sparse_embedding.fastembed.completed",
            model=self.model,
            text_count=len(texts),
        )

        return [
            SparseVector(
                indices=[int(index) for index in embedding.indices],
                values=[float(value) for value in embedding.values],
            )
            for embedding in embeddings
        ]
