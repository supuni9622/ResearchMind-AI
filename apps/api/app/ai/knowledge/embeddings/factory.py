"""
Canonical Embedding factory.

Converts provider output into the canonical Embedding model.

All embedding providers should use this factory instead of constructing
Embedding objects directly.

The factory centralizes embedding creation so that future schema changes
are implemented in one place.
"""

from __future__ import annotations

from uuid import uuid4

from app.ai.knowledge.chunking.models import Chunk
from app.ai.knowledge.embeddings.enums import EmbeddingProvider
from app.ai.knowledge.embeddings.models import (
    Embedding,
    EmbeddingExperiment,
    EmbeddingProvenance,
    EmbeddingProviderMetadata,
    EmbeddingStatistics,
    EmbeddingVector,
)


class EmbeddingFactory:
    """
    Factory for canonical Embedding objects.
    """

    @staticmethod
    def from_vector(
        *,
        chunk: Chunk,
        vector: list[float],
        provider: EmbeddingProvider,
        model: str,
        provider_version: str,
        configuration_fingerprint: str,
        model_version: str | None = None,
    ) -> Embedding:
        """
        Build a canonical Embedding.

        Args:
            chunk:
                Canonical source chunk.

            vector:
                Generated embedding vector.

            provider:
                Embedding provider name.

            model:
                Embedding model name.

            provider_version:
                Provider implementation version.

            configuration_fingerprint:
                Stable provider configuration fingerprint.

            model_version:
                Optional provider model version.

        Returns:
            Canonical Embedding.
        """

        return Embedding(
            id=uuid4(),
            provenance=EmbeddingProvenance(
                document_id=chunk.provenance.document_id,
                chunk_id=chunk.id,
                filename=chunk.provenance.filename,
            ),
            provider=EmbeddingProviderMetadata(
                provider=provider,
                model=model,
                model_version=model_version,
            ),
            statistics=EmbeddingStatistics(
                character_count=chunk.statistics.character_count,
                word_count=chunk.statistics.word_count,
                estimated_token_count=chunk.statistics.estimated_token_count,
            ),
            experiment=EmbeddingExperiment(
                provider=provider,
                provider_version=provider_version,
                configuration_fingerprint=configuration_fingerprint,
            ),
            vector=EmbeddingVector(
                values=vector,
                dimensions=len(vector),
            ),
        )
