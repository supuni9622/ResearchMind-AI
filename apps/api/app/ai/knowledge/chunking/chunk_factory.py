"""
Canonical Chunk mapper.

Converts provider output into the canonical Chunk model.

All chunking providers should use this mapper instead of constructing
Chunk objects directly.

The mapper centralizes chunk creation so that future schema changes are
implemented in one place.
"""

from __future__ import annotations

from typing import Any
from uuid import UUID, uuid4

from app.ai.knowledge.chunking.enums import ChunkContentType, ChunkingStrategy
from app.ai.knowledge.chunking.models import (
    Chunk,
    ChunkContent,
    ChunkExperiment,
    ChunkProvenance,
    ChunkStatistics,
    ChunkStructure,
)
from app.ai.knowledge.processing.models import ProcessedDocument


class ChunkFactory:
    """
    Factory for canonical Chunk objects.
    """

    @staticmethod
    def from_text(
        *,
        document: ProcessedDocument,
        text: str,
        index: int,
        total_chunks: int,
        strategy: ChunkingStrategy,
        strategy_version: str,
        configuration_fingerprint: str,
        markdown: str | None = None,
        content_type: ChunkContentType = ChunkContentType.TEXT,
        heading: str | None = None,
        heading_path: list[str] | None = None,
        page_numbers: list[int] | None = None,
        hierarchy_level: int | None = None,
        parent_chunk_id: UUID | None = None,
        additional_metadata: dict[str, Any] | None = None,
    ) -> Chunk:
        """
        Build a canonical Chunk.
        """

        heading_path = heading_path or []
        page_numbers = page_numbers or []

        word_count = len(text.split())

        estimated_tokens = max(
            1,
            len(text) // 4,
        )

        return Chunk(
            id=uuid4(),
            index=index,
            total_chunks=total_chunks,
            content=ChunkContent(
                text=text,
                markdown=markdown,
                content_type=content_type,
            ),
            structure=ChunkStructure(
                heading=heading,
                heading_path=heading_path,
                page_numbers=page_numbers,
                hierarchy_level=hierarchy_level,
                parent_chunk_id=parent_chunk_id,
            ),
            statistics=ChunkStatistics(
                character_count=len(text),
                word_count=word_count,
                sentence_count=0,
                estimated_token_count=estimated_tokens,
                average_token_length=((len(text) / estimated_tokens) if estimated_tokens else 0.0),
            ),
            provenance=ChunkProvenance(
                document_id=document.document_id,
                filename=document.filename,
                parser=document.parser.value,
                parser_version=None,
            ),
            experiment=ChunkExperiment(
                strategy=strategy,
                strategy_version=strategy_version,
                configuration_fingerprint=configuration_fingerprint,
                additional_metadata=additional_metadata or {},
            ),
        )
