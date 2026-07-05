"""
Fixed-size chunking provider.

This provider implements the simplest chunking strategy by splitting
documents into fixed-size character windows with configurable overlap.

It serves as the experimental baseline for the Chunking Platform.
Future chunking strategies are evaluated relative to this implementation.
"""

from __future__ import annotations

from app.ai.knowledge.chunking.base import BaseChunkingProvider
from app.ai.knowledge.chunking.config import FixedChunkingConfig
from app.ai.knowledge.chunking.enums import ChunkingStrategy
from app.ai.knowledge.chunking.models import Chunk
from app.ai.knowledge.processing.models import ProcessedDocument


class FixedChunkingProvider(
    BaseChunkingProvider[FixedChunkingConfig],
):
    """
    Fixed-size chunking implementation.

    Splits a processed document into fixed-size overlapping
    character windows.
    """

    def __init__(
        self,
        config: FixedChunkingConfig,
    ) -> None:
        super().__init__(config)

    @property
    def strategy(self) -> ChunkingStrategy:
        """
        Chunking strategy implemented by this provider.
        """

        return ChunkingStrategy.FIXED

    async def chunk(
        self,
        document: ProcessedDocument,
    ) -> list[Chunk]:
        """
        Split a processed document into fixed-size overlapping chunks.

        Args:
            document:
                Canonical processed document.

        Returns:
            Ordered list of generated chunks.
        """

        text = document.raw_text.strip()

        if not text:
            return []

        chunk_size = self.config.chunk_size
        chunk_overlap = self.config.chunk_overlap
        step = chunk_size - chunk_overlap

        chunk_texts: list[str] = []

        start = 0

        while start < len(text):
            end = min(start + chunk_size, len(text))

            chunk_text = text[start:end]

            if chunk_text.strip():
                chunk_texts.append(chunk_text)

            if end == len(text):
                break

            start += step

        total_chunks = len(chunk_texts)

        return [
            self._build_chunk(
                document=document,
                text=chunk_text,
                index=index,
                total_chunks=total_chunks,
            )
            for index, chunk_text in enumerate(chunk_texts)
        ]
