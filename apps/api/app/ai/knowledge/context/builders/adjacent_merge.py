"""
Adjacent chunk merge.

Combines neighbouring chunks from the same
document to build richer context blocks.
"""

from __future__ import annotations

from app.ai.knowledge.context.models import (
    ContextChunk,
)


class AdjacentMergeService:
    """
    Merge adjacent chunks.
    """

    def merge(
        self,
        chunks: list[ContextChunk],
    ) -> list[ContextChunk]:

        if not chunks:
            return chunks

        ordered = sorted(
            chunks,
            key=lambda c: (
                c.document_id,
                c.chunk_index,
            ),
        )

        merged: list[ContextChunk] = []

        current = ordered[0]

        current.merged_chunk_ids = [current.chunk_id]

        # Tracks the last original chunk_index absorbed into `current`,
        # since current.chunk_index itself is pinned to the block's
        # minimum (its starting index) below -- checking adjacency
        # against that minimum instead of the last-seen index would
        # break chains longer than two consecutive chunks.
        last_index = current.chunk_index

        for chunk in ordered[1:]:
            same_document = chunk.document_id == current.document_id

            adjacent = chunk.chunk_index == last_index + 1

            if same_document and adjacent:
                current.content += "\n\n" + chunk.content

                current.chunk_index = min(
                    current.chunk_index,
                    chunk.chunk_index,
                )

                current.score = max(
                    current.score,
                    chunk.score,
                )

                current.merged_chunk_ids.append(chunk.chunk_id)

                last_index = chunk.chunk_index

                continue

            merged.append(current)

            current = chunk

            current.merged_chunk_ids = [current.chunk_id]

            last_index = current.chunk_index

        merged.append(current)

        return merged
