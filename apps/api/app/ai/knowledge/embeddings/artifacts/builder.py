"""
Embedding artifact builder.

Builds the canonical EmbeddingArtifact from a ChunkArtifact and the
generated embeddings.

The builder is intentionally pure and has no knowledge of storage,
serialization, or Amazon S3.
"""

from __future__ import annotations

from app.ai.knowledge.chunking.artifacts.models import ChunkArtifact
from app.ai.knowledge.embeddings.artifacts.models import (
    EmbeddingArtifact,
    EmbeddingArtifactChunking,
    EmbeddingArtifactDocument,
    EmbeddingArtifactEvaluation,
    EmbeddingArtifactExecution,
    EmbeddingArtifactStatistics,
)
from app.ai.knowledge.embeddings.models import Embedding
from app.ai.knowledge.vectorstores.enums import VectorDistanceMetric


class EmbeddingArtifactBuilder:
    """
    Builds the canonical EmbeddingArtifact.
    """

    def build(
        self,
        *,
        chunk_artifact: ChunkArtifact,
        embeddings: list[Embedding],
    ) -> EmbeddingArtifact:
        """
        Build an EmbeddingArtifact.

        Args:
            chunk_artifact:
                Source chunk artifact.

            embeddings:
                Generated embeddings.

        Returns:
            EmbeddingArtifact.
        """

        if not embeddings:
            raise ValueError(
                "Cannot build an EmbeddingArtifact from an empty embedding collection."
            )

        first_embedding = embeddings[0]

        total_embeddings = len(embeddings)

        total_characters = sum(embedding.statistics.character_count for embedding in embeddings)

        total_words = sum(embedding.statistics.word_count for embedding in embeddings)

        total_tokens = sum(embedding.statistics.estimated_token_count for embedding in embeddings)

        dimensions = first_embedding.vector.dimensions

        statistics = EmbeddingArtifactStatistics(
            total_embeddings=total_embeddings,
            dimensions=dimensions,
            total_characters=total_characters,
            total_words=total_words,
            total_estimated_tokens=total_tokens,
            average_dimensions=float(dimensions),
        )

        document = EmbeddingArtifactDocument(
            document_id=chunk_artifact.document.document_id,
            filename=chunk_artifact.document.filename,
            parser=chunk_artifact.document.parser,
            parser_version=chunk_artifact.document.parser_version,
        )

        chunking = EmbeddingArtifactChunking(
            strategy=chunk_artifact.strategy.strategy,
            strategy_version=chunk_artifact.strategy.strategy_version,
            configuration_fingerprint=(chunk_artifact.strategy.configuration_fingerprint),
        )

        execution = EmbeddingArtifactExecution(
            provider=first_embedding.experiment.provider,
            provider_version=first_embedding.experiment.provider_version,
            model=first_embedding.provider.model,
            model_version=first_embedding.provider.model_version,
            recommended_distance_metric=VectorDistanceMetric.DOT,
            configuration_fingerprint=(first_embedding.experiment.configuration_fingerprint),
        )

        return EmbeddingArtifact(
            document=document,
            chunking=chunking,
            execution=execution,
            statistics=statistics,
            evaluation=EmbeddingArtifactEvaluation(),
            embeddings=embeddings,
        )
