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
is invoked by the dedicated recurring lifecycle worker in `apps/worker`.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import UUID

import structlog

from app.ai.memory.enums import MemoryType
from app.ai.memory.observability import metrics as memory_metrics
from app.ai.memory.storage.vector_index import MemoryVectorIndex
from app.infrastructure.metrics.interfaces import MetricsRecorder
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
        metrics: MetricsRecorder | None = None,
    ) -> None:
        self._repository = repository
        self._vector_index = vector_index
        self._metrics = metrics

    async def sweep_stale(
        self,
        *,
        owner_id: UUID | None = None,
        stale_after_days: int = _DEFAULT_STALE_AFTER_DAYS,
        max_importance: float = _DEFAULT_MAX_IMPORTANCE,
        memory_types: tuple[MemoryType, ...] = _STALE_TYPES,
        batch_size: int = 500,
        dry_run: bool = False,
    ) -> int:
        """
        Delete USER/SEMANTIC/RESEARCH rows last updated more than
        `stale_after_days` ago with `importance_score <= max_importance`.
        Qdrant is deleted before its canonical row. A vector failure leaves
        PostgreSQL intact so a later sweep can retry instead of creating an
        untracked orphan. Each row commits independently so one failure does
        not poison the rest of the bounded batch. Returns rows deleted (or
        candidates examined in dry-run mode).
        """

        cutoff = datetime.now(UTC) - timedelta(days=stale_after_days)

        stale_rows = await self._repository.list_stale(
            older_than=cutoff,
            max_importance=max_importance,
            types=[t.value for t in memory_types],
            owner_id=owner_id,
            limit=batch_size,
        )

        examined = len(stale_rows)
        deleted = 0
        failed = 0
        if self._metrics:
            self._metrics.increment(metric=memory_metrics.LIFECYCLE_EXAMINED, value=examined)
            if stale_rows:
                oldest_age = (datetime.now(UTC) - stale_rows[0].updated_at).total_seconds()
                self._metrics.set_gauge(
                    metric=memory_metrics.LIFECYCLE_OLDEST_CANDIDATE_AGE,
                    value=max(0.0, oldest_age),
                )

        if dry_run:
            logger.info(
                "memory.lifecycle.dry_run_completed",
                types=[t.value for t in memory_types],
                examined=examined,
            )
            return examined

        for row in stale_rows:
            try:
                if row.type in (
                    MemoryType.SEMANTIC.value,
                    MemoryType.RESEARCH.value,
                ) and not await self._vector_index.delete(row.id):
                    raise RuntimeError("vector deletion failed")
                await self._repository.delete(row)
                await self._repository.session.commit()
                deleted += 1
            except Exception:
                failed += 1
                await self._repository.session.rollback()
                logger.exception("memory.lifecycle.row_failed", memory_id=str(row.id))

        if self._metrics:
            self._metrics.increment(metric=memory_metrics.LIFECYCLE_DELETED, value=deleted)
            self._metrics.increment(metric=memory_metrics.LIFECYCLE_FAILED, value=failed)

        logger.info(
            "memory.lifecycle.sweep_completed",
            owner_id=str(owner_id) if owner_id else None,
            stale_after_days=stale_after_days,
            max_importance=max_importance,
            types=[t.value for t in memory_types],
            examined=examined,
            deleted=deleted,
            failed=failed,
        )

        return deleted
