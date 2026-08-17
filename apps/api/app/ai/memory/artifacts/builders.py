"""
Memory artifact builders. Pure -- no knowledge of storage.
"""

from __future__ import annotations

from uuid import UUID

from app.ai.memory.artifacts.models import MemoryContextArtifact, MemorySearchArtifact
from app.ai.memory.enums import MemoryScopeType, MemoryType
from app.ai.memory.models import MemoryContext, MemorySearchResult


class MemoryArtifactBuilder:
    def build_search(
        self,
        *,
        owner_id: UUID,
        scope_type: MemoryScopeType = MemoryScopeType.PERSONAL,
        project_id: UUID | None = None,
        query: str,
        memory_types: list[MemoryType],
        result: MemorySearchResult,
    ) -> MemorySearchArtifact:
        return MemorySearchArtifact(
            owner_id=owner_id,
            scope_type=scope_type,
            project_id=project_id,
            query=query,
            memory_types=memory_types,
            result=result,
        )

    def build_context(
        self,
        *,
        owner_id: UUID,
        session_id: UUID | None,
        scope_type: MemoryScopeType = MemoryScopeType.PERSONAL,
        project_id: UUID | None = None,
        context: MemoryContext,
    ) -> MemoryContextArtifact:
        return MemoryContextArtifact(
            owner_id=owner_id,
            scope_type=scope_type,
            project_id=project_id,
            session_id=session_id,
            context=context,
        )
