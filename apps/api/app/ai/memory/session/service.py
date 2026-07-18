"""
Session Memory Service (PRD §9.2) -- active-conversation recall:
previous messages, generated answers, retrieved context, intermediate
state. Backed entirely by `ValkeySessionStore` (7-day TTL, PRD §6.1).
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from uuid import UUID, uuid4

from app.ai.memory.enums import MemoryType
from app.ai.memory.models import MemoryRecord
from app.ai.memory.storage.valkey_store import ValkeySessionStore

_SESSION_ID_KEY = "session_id"


class SessionMemoryService:
    def __init__(
        self,
        store: ValkeySessionStore,
    ) -> None:
        self._store = store

    async def remember(
        self,
        *,
        owner_id: UUID,
        session_id: UUID,
        content: str,
        importance_score: float,
        metadata: dict[str, Any] | None = None,
    ) -> MemoryRecord:
        now = datetime.now(UTC)

        record = MemoryRecord(
            id=uuid4(),
            owner_id=owner_id,
            type=MemoryType.SESSION,
            content=content,
            metadata={**(metadata or {}), _SESSION_ID_KEY: str(session_id)},
            importance_score=importance_score,
            created_at=now,
            updated_at=now,
        )

        await self._store.put(record, session_id=session_id)

        return record

    async def recall(
        self,
        *,
        owner_id: UUID,
        memory_id: UUID,
    ) -> MemoryRecord | None:
        return await self._store.get(owner_id=owner_id, memory_id=memory_id)

    async def get_context(
        self,
        *,
        owner_id: UUID,
        session_id: UUID,
        limit: int = 20,
    ) -> list[MemoryRecord]:
        """Most recent messages/state for `session_id`, oldest first."""

        return await self._store.get_recent(
            owner_id=owner_id,
            session_id=session_id,
            limit=limit,
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
        existing = await self.recall(owner_id=owner_id, memory_id=memory_id)

        if existing is None:
            return None

        updated = existing.model_copy(
            update={
                "content": content if content is not None else existing.content,
                "metadata": {**existing.metadata, **(metadata or {})},
                "importance_score": (
                    importance_score if importance_score is not None else existing.importance_score
                ),
                "updated_at": datetime.now(UTC),
            }
        )

        if not await self._store.replace(updated):
            return None

        return updated

    async def forget(
        self,
        *,
        owner_id: UUID,
        memory_id: UUID,
    ) -> bool:
        return await self._store.delete(owner_id=owner_id, memory_id=memory_id)
