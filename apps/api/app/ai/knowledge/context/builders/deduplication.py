from __future__ import annotations

from app.ai.knowledge.context.models import (
    ContextChunk,
)


class DeduplicationService:
    def deduplicate(
        self,
        chunks: list[ContextChunk],
    ) -> list[ContextChunk]:

        seen = set()

        result = []

        for chunk in chunks:
            if chunk.chunk_id in seen:
                continue

            seen.add(chunk.chunk_id)

            result.append(chunk)

        return result
