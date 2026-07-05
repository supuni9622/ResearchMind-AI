"""
Markdown chunking provider.

This provider preserves Markdown document structure by first splitting
the document using Markdown headings and then recursively splitting
oversized sections.

LangChain is intentionally encapsulated within this provider so that the
rest of the application remains framework-independent.
"""

from __future__ import annotations

from app.ai.knowledge.chunking.base import BaseChunkingProvider
from app.ai.knowledge.chunking.chunk_factory import ChunkFactory
from app.ai.knowledge.chunking.config import MarkdownChunkingConfig
from app.ai.knowledge.chunking.enums import (
    ChunkContentType,
    ChunkingStrategy,
)
from app.ai.knowledge.chunking.models import Chunk
from app.ai.knowledge.processing.models import ProcessedDocument
from langchain_text_splitters import (
    MarkdownHeaderTextSplitter,
    RecursiveCharacterTextSplitter,
)


class MarkdownChunkingProvider(
    BaseChunkingProvider[MarkdownChunkingConfig],
):
    """
    Markdown-aware chunking provider.

    Preserves Markdown document hierarchy before recursively splitting
    oversized sections.
    """

    def __init__(
        self,
        config: MarkdownChunkingConfig,
    ) -> None:
        super().__init__(config)

        self._markdown_splitter = MarkdownHeaderTextSplitter(
            headers_to_split_on=list(config.headers_to_split_on),
            strip_headers=config.strip_headers,
            return_each_line=config.return_each_line,
        )

        self._recursive_splitter = RecursiveCharacterTextSplitter(
            chunk_size=config.chunk_size,
            chunk_overlap=config.chunk_overlap,
        )

    @property
    def strategy(self) -> ChunkingStrategy:
        """
        Chunking strategy implemented by this provider.
        """

        return ChunkingStrategy.MARKDOWN

    async def chunk(
        self,
        document: ProcessedDocument,
    ) -> list[Chunk]:
        """
        Split a processed Markdown document while preserving heading
        hierarchy.

        Args:
            document:
                Canonical processed document.

        Returns:
            Ordered list of canonical chunks.
        """

        markdown = document.markdown.strip()

        if not markdown:
            return []

        markdown_documents = self._markdown_splitter.split_text(
            markdown,
        )

        recursive_documents = []

        for markdown_document in markdown_documents:
            recursive_documents.extend(
                self._recursive_splitter.create_documents(
                    texts=[markdown_document.page_content],
                    metadatas=[markdown_document.metadata],
                )
            )

        total_chunks = len(recursive_documents)

        chunks: list[Chunk] = []

        for index, langchain_document in enumerate(recursive_documents):
            text = langchain_document.page_content.strip()

            if not text:
                continue

            metadata = langchain_document.metadata

            heading_path = [
                metadata[level]
                for level in ("h1", "h2", "h3", "h4", "h5", "h6")
                if metadata.get(level)
            ]

            heading = heading_path[-1] if heading_path else None

            chunks.append(
                ChunkFactory.from_text(
                    document=document,
                    text=text,
                    markdown=text,
                    index=index,
                    total_chunks=total_chunks,
                    strategy=self.strategy,
                    strategy_version=self.version,
                    configuration_fingerprint=self.configuration_fingerprint,
                    content_type=ChunkContentType.MARKDOWN,
                    heading=heading,
                    heading_path=heading_path,
                )
            )

        return chunks
