"""
Memory artifact builders. Pure -- no knowledge of storage.
"""

from __future__ import annotations

from uuid import UUID

from app.ai.memory.artifacts.models import MemoryContextArtifact, MemorySearchArtifact
from app.ai.memory.enums import MemoryType
from app.ai.memory.models import MemoryContext, MemorySearchResult


class MemoryArtifactBuilder:
    def build_search(
        self,
        *,
        owner_id: UUID,
        query: str,
        memory_types: list[MemoryType],
        result: MemorySearchResult,
    ) -> MemorySearchArtifact:
        return MemorySearchArtifact(
            owner_id=owner_id,
            query=query,
            memory_types=memory_types,
            result=result,
        )

    def build_context(
        self,
        *,
        owner_id: UUID,
        session_id: UUID | None,
        context: MemoryContext,
    ) -> MemoryContextArtifact:
        return MemoryContextArtifact(
            owner_id=owner_id,
            session_id=session_id,
            context=context,
        )
