"""
Chunk artifact builder.

Builds the canonical ChunkArtifact from a collection of generated chunks.

The builder is intentionally pure and has no knowledge of storage,
serialization, or Amazon S3.
"""

from __future__ import annotations

from app.ai.knowledge.chunking.artifacts.models import (
    ChunkArtifact,
    ChunkArtifactDocument,
    ChunkArtifactEvaluation,
    ChunkArtifactStatistics,
    ChunkArtifactStrategy,
)
from app.ai.knowledge.chunking.models import Chunk


class ChunkArtifactBuilder:
    """
    Builds the canonical ChunkArtifact.
    """

    def build(
        self,
        chunks: list[Chunk],
    ) -> ChunkArtifact:
        """
        Build a ChunkArtifact from generated chunks.

        Args:
            chunks:
                Generated chunks for a single chunking execution.

        Returns:
            ChunkArtifact.
        """

        if not chunks:
            raise ValueError("Cannot build a ChunkArtifact from an empty chunk collection.")

        first_chunk = chunks[0]

        total_characters = sum(chunk.statistics.character_count for chunk in chunks)

        total_words = sum(chunk.statistics.word_count for chunk in chunks)

        total_tokens = sum(chunk.statistics.estimated_token_count for chunk in chunks)

        total_chunks = len(chunks)

        statistics = ChunkArtifactStatistics(
            total_chunks=total_chunks,
            total_characters=total_characters,
            total_words=total_words,
            total_estimated_tokens=total_tokens,
            average_chunk_size=(total_characters / total_chunks),
            average_word_count=(total_words / total_chunks),
            average_token_count=(total_tokens / total_chunks),
        )

        document = ChunkArtifactDocument(
            document_id=first_chunk.provenance.document_id,
            filename=first_chunk.provenance.filename or "",
            parser=first_chunk.provenance.parser,
            parser_version=first_chunk.provenance.parser_version,
        )

        strategy = ChunkArtifactStrategy(
            strategy=first_chunk.experiment.strategy,
            strategy_version=first_chunk.experiment.strategy_version,
            configuration_fingerprint=(first_chunk.experiment.configuration_fingerprint),
        )

        return ChunkArtifact(
            document=document,
            strategy=strategy,
            statistics=statistics,
            evaluation=ChunkArtifactEvaluation(),
            chunks=chunks,
        )
