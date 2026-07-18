"""
Memory Lifecycle Pipeline (PRD §15/§26 -- created -> hot -> warm ->
cold -> archive -> delete).

SESSION memory already has a full lifecycle: Valkey's TTL is the hot
-> delete transition (PRD §6.1, 7 days), and there is nothing colder
than "expired" for a conversation turn, so it needs no code here.

USER/SEMANTIC/RESEARCH memory has no automatic lifecycle otherwise --
this module is the "cold -> delete" tail end of it: a callable sweep
that removes low-importance rows nobody has touched in a long time,
so Postgres/Qdrant don't grow unbounded (PRD §16 "avoid remembering
everything" applies over time, not just at write time).

This is intentionally *not* the full hot/warm/cold staging the PRD
describes (no status field, no archival tier) -- that requires real
usage data to tune retention thresholds against, which doesn't exist
yet (mirrors the PRD's own §26 guidance to postpone decay/
consolidation until Research Runtime has real workloads). `sweep_stale()`
is deliberately callable-but-unscheduled: nothing in this codebase
currently runs recurring jobs, so wiring a scheduler is a decision for
whoever operates this, not something to invent here.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import UUID

import structlog

from app.ai.memory.enums import MemoryType
from app.ai.memory.storage.vector_index import MemoryVectorIndex
from app.repositories.memory import MemoryRepository

logger = structlog.get_logger()

_STALE_TYPES = (MemoryType.USER, MemoryType.SEMANTIC, MemoryType.RESEARCH)

_DEFAULT_STALE_AFTER_DAYS = 90
_DEFAULT_MAX_IMPORTANCE = 0.3


class MemoryLifecycleService:
    def __init__(
        self,
        repository: MemoryRepository,
        vector_index: MemoryVectorIndex,
    ) -> None:
        self._repository = repository
        self._vector_index = vector_index

    async def sweep_stale(
        self,
        *,
        owner_id: UUID | None = None,
        stale_after_days: int = _DEFAULT_STALE_AFTER_DAYS,
        max_importance: float = _DEFAULT_MAX_IMPORTANCE,
    ) -> int:
        """
        Delete USER/SEMANTIC/RESEARCH rows last updated more than
        `stale_after_days` ago with `importance_score <= max_importance`.
        Also removes the corresponding Qdrant point for SEMANTIC/
        RESEARCH rows. Returns the number of memories deleted.

        Caller owns the transaction boundary (mirrors every other
        method on `MemoryRepository`): commits after each delete.
        """

        cutoff = datetime.now(UTC) - timedelta(days=stale_after_days)

        stale_rows = await self._repository.list_stale(
            older_than=cutoff,
            max_importance=max_importance,
            types=[t.value for t in _STALE_TYPES],
            owner_id=owner_id,
        )

        for row in stale_rows:
            await self._repository.delete(row)

            if row.type in (MemoryType.SEMANTIC.value, MemoryType.RESEARCH.value):
                await self._vector_index.delete(row.id)

        await self._repository.session.commit()

        logger.info(
            "memory.lifecycle.sweep_completed",
            owner_id=str(owner_id) if owner_id else None,
            stale_after_days=stale_after_days,
            max_importance=max_importance,
            deleted=len(stale_rows),
        )

        return len(stale_rows)
