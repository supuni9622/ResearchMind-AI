"""
Hierarchical (Parent/Child) chunking provider.

Pipeline:

    Parent Documents
        ↓
    Child Chunks
        ↓
    Retrieve Child
        ↓
    Expand Parent

Documents are first split into large "parent" sections using LangChain's
RecursiveCharacterTextSplitter, then each parent section is split again
into small "child" chunks with the same splitter. This mirrors the
two-pass splitting `langchain_classic.retrievers.ParentDocumentRetriever`
performs internally; a bespoke retriever object is unnecessary here
since this provider only needs the splitting behavior, not the
vectorstore/docstore wiring LangChain's retriever couples it to.

Only child chunks are marked embeddable (`is_parent=False`); parent
chunks are tagged `is_parent=True` in `experiment.additional_metadata`
so `EmbeddingService` excludes them from the vector index while they
remain in the persisted ChunkArtifact for
`ParentExpansionService` (app/ai/knowledge/context/builders/parent_expansion.py)
to expand a retrieved child chunk back into its full parent section.

LangChain is intentionally encapsulated within this provider so that the
rest of the application remains framework-independent.
"""

from __future__ import annotations

from app.ai.knowledge.chunking.base import BaseChunkingProvider
from app.ai.knowledge.chunking.chunk_factory import ChunkFactory
from app.ai.knowledge.chunking.config import HierarchicalChunkingConfig
from app.ai.knowledge.chunking.enums import ChunkingStrategy
from app.ai.knowledge.chunking.models import Chunk
from app.ai.knowledge.processing.models import ProcessedDocument
from langchain_text_splitters import RecursiveCharacterTextSplitter


class HierarchicalChunkingProvider(
    BaseChunkingProvider[HierarchicalChunkingConfig],
):
    """
    Parent/Child hierarchical chunking implementation.
    """

    def __init__(
        self,
        config: HierarchicalChunkingConfig,
    ) -> None:
        super().__init__(config)

        self._parent_splitter = RecursiveCharacterTextSplitter(
            chunk_size=config.parent_chunk_size,
            chunk_overlap=config.parent_chunk_overlap,
        )

        self._child_splitter = RecursiveCharacterTextSplitter(
            chunk_size=config.child_chunk_size,
            chunk_overlap=config.child_chunk_overlap,
        )

    @property
    def strategy(self) -> ChunkingStrategy:
        """
        Chunking strategy implemented by this provider.
        """

        return ChunkingStrategy.HIERARCHICAL

    async def chunk(
        self,
        document: ProcessedDocument,
    ) -> list[Chunk]:
        """
        Split a processed document into parent sections and child chunks.

        Args:
            document:
                Canonical processed document.

        Returns:
            Ordered list of chunks containing both parent sections
            (`hierarchy_level=0`, `is_parent=True`) and child chunks
            (`hierarchy_level=1`, referencing their parent via
            `structure.parent_chunk_id`).
        """

        text = document.raw_text.strip()

        if not text:
            return []

        parent_texts = [
            parent_text.strip()
            for parent_text in self._parent_splitter.split_text(text)
            if parent_text.strip()
        ]

        parent_sections = [
            (
                parent_text,
                [
                    child_text.strip()
                    for child_text in self._child_splitter.split_text(parent_text)
                    if child_text.strip()
                ],
            )
            for parent_text in parent_texts
        ]

        total_parents = len(parent_sections)

        total_children = sum(len(child_texts) for _, child_texts in parent_sections)

        chunks: list[Chunk] = []

        child_index = 0

        for parent_position, (parent_text, child_texts) in enumerate(parent_sections):
            parent_chunk = ChunkFactory.from_text(
                document=document,
                text=parent_text,
                index=parent_position,
                total_chunks=total_parents,
                strategy=self.strategy,
                strategy_version=self.version,
                configuration_fingerprint=self.configuration_fingerprint,
                hierarchy_level=0,
                additional_metadata={"is_parent": True},
            )

            chunks.append(parent_chunk)

            for child_text in child_texts:
                chunks.append(
                    ChunkFactory.from_text(
                        document=document,
                        text=child_text,
                        index=child_index,
                        total_chunks=total_children,
                        strategy=self.strategy,
                        strategy_version=self.version,
                        configuration_fingerprint=self.configuration_fingerprint,
                        hierarchy_level=1,
                        parent_chunk_id=parent_chunk.id,
                        additional_metadata={"is_parent": False},
                    )
                )

                child_index += 1

        return chunks
