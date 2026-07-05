"""
Recursive chunking provider.

This provider delegates recursive text splitting to LangChain's
RecursiveCharacterTextSplitter while converting the results into the
canonical Chunk model used throughout the Knowledge Platform.

LangChain is intentionally encapsulated within this provider so that the
rest of the application remains framework-independent.
"""

from __future__ import annotations

from app.ai.knowledge.chunking.base import BaseChunkingProvider
from app.ai.knowledge.chunking.chunk_factory import ChunkFactory
from app.ai.knowledge.chunking.config import RecursiveChunkingConfig
from app.ai.knowledge.chunking.enums import ChunkingStrategy
from app.ai.knowledge.chunking.models import Chunk
from app.ai.knowledge.processing.models import ProcessedDocument
from langchain_text_splitters import RecursiveCharacterTextSplitter


class RecursiveChunkingProvider(
    BaseChunkingProvider[RecursiveChunkingConfig],
):
    """
    Recursive chunking implementation.

    Uses LangChain's RecursiveCharacterTextSplitter internally while
    exposing only canonical Chunk models to the rest of the application.
    """

    def __init__(
        self,
        config: RecursiveChunkingConfig,
    ) -> None:
        super().__init__(config)

    @property
    def strategy(self) -> ChunkingStrategy:
        """
        Chunking strategy implemented by this provider.
        """

        return ChunkingStrategy.RECURSIVE

    async def chunk(
        self,
        document: ProcessedDocument,
    ) -> list[Chunk]:
        """
        Split a processed document using recursive chunking.

        Args:
            document:
                Canonical processed document.

        Returns:
            Ordered list of canonical chunks.
        """

        text = document.raw_text.strip()

        if not text:
            return []

        splitter = RecursiveCharacterTextSplitter(
            chunk_size=self.config.chunk_size,
            chunk_overlap=self.config.chunk_overlap,
            separators=self.config.separators,
            keep_separator=self.config.keep_separator,
        )

        chunk_texts = splitter.split_text(text)

        total_chunks = len(chunk_texts)

        return [
            ChunkFactory.from_text(
                document=document,
                text=chunk_text,
                index=index,
                total_chunks=total_chunks,
                strategy=self.strategy,
                strategy_version=self.version,
                configuration_fingerprint=self.configuration_fingerprint,
            )
            for index, chunk_text in enumerate(chunk_texts)
        ]
