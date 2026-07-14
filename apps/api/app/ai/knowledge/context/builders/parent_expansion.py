"""
Parent context expansion.

Transforms retrieved child chunks into richer context
by loading parent chunks from persisted chunk artifacts.
"""

from __future__ import annotations

from collections import defaultdict
from uuid import UUID

from app.ai.knowledge.context.artifacts.reader import (
    ChunkArtifactReader,
)
from app.ai.knowledge.context.models import (
    ContextChunk,
)


class ParentExpansionService:
    """
    Expands retrieved chunks using parent chunks.
    """

    def __init__(
        self,
        artifact_reader: ChunkArtifactReader,
    ) -> None:
        self._artifact_reader = artifact_reader

    async def expand(
        self,
        chunks: list[ContextChunk],
    ) -> list[ContextChunk]:

        if not chunks:
            return chunks

        grouped = defaultdict(list)

        #
        # Group by artifact.
        #

        for chunk in chunks:
            metadata = chunk.metadata

            artifact_id = metadata.get("chunk_artifact_id")

            strategy = metadata.get("chunking_strategy")

            if not isinstance(artifact_id, str) or not isinstance(strategy, str):
                continue

            grouped[
                (
                    chunk.owner_id,
                    chunk.document_id,
                    strategy,
                    artifact_id,
                )
            ].append(chunk)

        #
        # Load artifacts once.
        #

        for (
            owner_id,
            document_id,
            strategy,
            artifact_id,
        ), group in grouped.items():
            artifact = await self._artifact_reader.load(
                owner_id=owner_id,
                document_id=document_id,
                strategy=strategy,
                artifact_id=UUID(
                    artifact_id,
                ),
            )

            lookup = {chunk.id: chunk for chunk in artifact.chunks}

            for chunk in group:
                if not chunk.parent_chunk_id:
                    continue

                parent = lookup.get(
                    chunk.parent_chunk_id,
                )

                if not parent:
                    continue

                chunk.parent_content = parent.content.text

                chunk.page_numbers = parent.structure.page_numbers

                chunk.heading = parent.structure.heading

                chunk.heading_path = parent.structure.heading_path

        return chunks
