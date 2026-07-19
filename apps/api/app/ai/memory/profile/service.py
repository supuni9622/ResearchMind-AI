"""
User Memory Service (PRD §9.3) -- preference management and profile
updates: favorite models, writing style, response preferences,
preferred providers, research interests. Persistent, low write
frequency, Postgres-only (PRD §6.2) -- no vector index, since
preferences are looked up by owner, not searched semantically.
"""

from __future__ import annotations

from typing import Any
from uuid import UUID

from app.ai.memory.enums import MemoryType
from app.ai.memory.models import MemoryRecord
from app.ai.memory.storage.postgres_store import PostgresMemoryStore


class UserMemoryService:
    def __init__(
        self,
        store: PostgresMemoryStore,
    ) -> None:
        self._store = store

    async def remember(
        self,
        *,
        owner_id: UUID,
        content: str,
        importance_score: float,
        metadata: dict[str, Any] | None = None,
    ) -> MemoryRecord:
        return await self._store.create(
            owner_id=owner_id,
            memory_type=MemoryType.USER,
            content=content,
            importance_score=importance_score,
            metadata=metadata,
        )

    async def recall(
        self,
        *,
        owner_id: UUID,
        memory_id: UUID,
    ) -> MemoryRecord | None:
        return await self._store.get(owner_id=owner_id, memory_id=memory_id)

    async def list_preferences(
        self,
        *,
        owner_id: UUID,
        limit: int = 100,
    ) -> list[MemoryRecord]:
        return await self._store.list_by_type(
            owner_id=owner_id,
            memory_type=MemoryType.USER,
            limit=limit,
        )

    async def find_exact_content(self, *, owner_id: UUID, content: str) -> MemoryRecord | None:
        return await self._store.find_exact_content(
            owner_id=owner_id, memory_type=MemoryType.USER, content=content
        )

    async def update(
        self,
        *,
        owner_id: UUID,
        memory_id: UUID,
        content: str | None = None,
        metadata: dict[str, Any] | None = None,
        importance_score: float | None = None,
    ) -> MemoryRecord | None:
        return await self._store.update(
            owner_id=owner_id,
            memory_id=memory_id,
            content=content,
            metadata=metadata,
            importance_score=importance_score,
        )

    async def forget(
        self,
        *,
        owner_id: UUID,
        memory_id: UUID,
    ) -> bool:
        return await self._store.delete(owner_id=owner_id, memory_id=memory_id)
