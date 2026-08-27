from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

import structlog

from app.ai.knowledge.embeddings.enums import EmbeddingProvider
from app.ai.knowledge.retrieval.query.dense_service import QueryEmbeddingService
from app.ai.memory.consolidation.decision import MemoryConsolidationDecisionService
from app.ai.memory.consolidation.models import (
    ConsolidationAction,
    ConsolidationRunResult,
)
from app.ai.memory.enums import MemoryScopeType, MemoryType
from app.ai.memory.models import MemoryRecord
from app.ai.memory.observability import metrics as memory_metrics
from app.ai.memory.storage.vector_index import MemoryVectorIndex
from app.infrastructure.metrics.interfaces import MetricsRecorder
from app.models.memory import Memory
from app.repositories.memory import MemoryRepository

logger = structlog.get_logger()


class MemoryConsolidationService:
    """Bounded two-stage consolidation: vector nomination, then typed judgment."""

    def __init__(
        self,
        repository: MemoryRepository,
        vector_index: MemoryVectorIndex,
        embeddings: QueryEmbeddingService,
        decision_service: MemoryConsolidationDecisionService,
        *,
        metrics: MetricsRecorder | None = None,
        embedding_provider: EmbeddingProvider = EmbeddingProvider.VOYAGE_AI,
    ) -> None:
        self._repository = repository
        self._vector_index = vector_index
        self._embeddings = embeddings
        self._decisions = decision_service
        self._metrics = metrics
        self._embedding_provider = embedding_provider

    async def run_batch(
        self,
        *,
        batch_size: int = 50,
        candidate_limit: int = 5,
        similarity_threshold: float = 0.88,
        dry_run: bool = True,
    ) -> ConsolidationRunResult:
        seeds = await self._repository.list_consolidation_seeds(
            types=[MemoryType.SEMANTIC.value, MemoryType.RESEARCH.value],
            limit=batch_size,
        )
        result = ConsolidationRunResult(examined=len(seeds))
        for seed in seeds:
            try:
                candidate = await self._nominate(
                    seed,
                    limit=candidate_limit,
                    threshold=similarity_threshold,
                )
                if candidate is None:
                    if not dry_run:
                        await self._mark_checked(seed, "no_candidate")
                    continue
                result.candidates += 1
                decision = await self._decisions.decide(
                    owner_id=seed.owner_id,
                    first=self._record(seed),
                    second=self._record(candidate),
                )
                if decision is None:
                    result.failed += 1
                    continue
                if decision.action == ConsolidationAction.DUPLICATE:
                    result.duplicates += 1
                elif decision.action == ConsolidationAction.MERGEABLE:
                    result.merged += 1
                elif decision.action == ConsolidationAction.CONTRADICTION:
                    result.contradictions += 1
                else:
                    result.unrelated += 1

                if dry_run:
                    logger.info(
                        "memory.consolidation.dry_run_decision",
                        first_id=str(seed.id),
                        second_id=str(candidate.id),
                        action=decision.action.value,
                    )
                elif decision.action in (
                    ConsolidationAction.DUPLICATE,
                    ConsolidationAction.MERGEABLE,
                ):
                    await self._merge(seed, candidate, decision.action, decision.merged_content)
                else:
                    await self._mark_checked(seed, decision.action.value)
            except Exception:
                result.failed += 1
                await self._repository.session.rollback()
                logger.exception("memory.consolidation.row_failed", memory_id=str(seed.id))

        if self._metrics:
            self._metrics.increment(
                metric=memory_metrics.CONSOLIDATION_EXAMINED, value=result.examined
            )
            self._metrics.increment(
                metric=memory_metrics.CONSOLIDATION_CANDIDATES, value=result.candidates
            )
            for action, value in (
                ("duplicate", result.duplicates),
                ("mergeable", result.merged),
                ("contradiction", result.contradictions),
                ("unrelated", result.unrelated),
                ("failed", result.failed),
            ):
                self._metrics.increment(
                    metric=memory_metrics.CONSOLIDATION_OUTCOMES,
                    value=value,
                    labels={"action": action},
                )
        logger.info("memory.consolidation.batch_completed", **result.model_dump(), dry_run=dry_run)
        return result

    async def _nominate(self, seed: Memory, *, limit: int, threshold: float) -> Memory | None:
        vector = await self._embeddings.embed(seed.content, self._embedding_provider)
        ids = await self._vector_index.search(
            owner_id=seed.owner_id,
            scope_type=MemoryScopeType(seed.scope_type),
            project_id=seed.project_id,
            vector=vector,
            memory_types=[MemoryType(seed.type)],
            top_k=limit + 1,
            score_threshold=threshold,
        )
        for memory_id in ids:
            if memory_id == seed.id:
                continue
            row = await self._repository.get_by_id_for_owner(
                memory_id=memory_id,
                owner_id=seed.owner_id,
                scope_type=seed.scope_type,
                project_id=seed.project_id,
            )
            if row is not None and row.type == seed.type:
                return row
        return None

    async def _merge(
        self,
        first: Memory,
        second: Memory,
        action: ConsolidationAction,
        merged_content: str,
    ) -> None:
        canonical, source = sorted((first, second), key=lambda row: (row.created_at, row.id))
        content = canonical.content
        if action == ConsolidationAction.MERGEABLE:
            content = merged_content.strip()
            if not content:
                raise ValueError("mergeable decision omitted merged_content")

        canonical_original = {
            "id": canonical.id,
            "owner_id": canonical.owner_id,
            "type": MemoryType(canonical.type),
            "scope_type": MemoryScopeType(canonical.scope_type),
            "project_id": canonical.project_id,
            "content": canonical.content,
        }
        source_original = {
            "id": source.id,
            "owner_id": source.owner_id,
            "type": MemoryType(source.type),
            "scope_type": MemoryScopeType(source.scope_type),
            "project_id": source.project_id,
            "content": source.content,
        }
        vector = await self._embeddings.embed(content, self._embedding_provider)
        canonical_original_vector = await self._embeddings.embed(
            canonical.content, self._embedding_provider
        )
        source_original_vector = await self._embeddings.embed(
            source.content, self._embedding_provider
        )
        indexed = await self._vector_index.upsert(
            memory_id=canonical.id,
            owner_id=canonical.owner_id,
            memory_type=MemoryType(canonical.type),
            scope_type=MemoryScopeType(canonical.scope_type),
            project_id=canonical.project_id,
            vector=vector,
        )
        deleted = indexed and await self._vector_index.delete(source.id)
        if not indexed or not deleted:
            await self._restore_vectors(
                canonical_original,
                canonical_original_vector,
                source_original,
                source_original_vector,
            )
            raise RuntimeError("consolidation vector update failed")

        now = datetime.now(UTC)
        canonical_lineage = list(canonical.memory_metadata.get("_merged_from", []))
        canonical.memory_metadata = {
            **canonical.memory_metadata,
            "_merged_from": [*canonical_lineage, str(source.id)],
            "_consolidation_action": action.value,
            "_consolidated_at": now.isoformat(),
        }
        canonical.content = content
        canonical.importance_score = max(canonical.importance_score, source.importance_score)
        canonical.updated_at = now
        source.memory_metadata = {
            **source.memory_metadata,
            "_consolidated_into": str(canonical.id),
            "_consolidation_action": action.value,
            "_consolidated_at": now.isoformat(),
        }
        source.updated_at = now
        try:
            await self._repository.session.commit()
        except Exception:
            await self._repository.session.rollback()
            await self._restore_vectors(
                canonical_original,
                canonical_original_vector,
                source_original,
                source_original_vector,
            )
            raise

    async def _restore_vectors(
        self,
        canonical: dict[str, Any],
        canonical_vector: list[float],
        source: dict[str, Any],
        source_vector: list[float],
    ) -> None:
        """Best-effort compensation keeps Postgres truth searchable after failure."""

        for snapshot, vector in (
            (canonical, canonical_vector),
            (source, source_vector),
        ):
            await self._vector_index.upsert(
                memory_id=snapshot["id"],
                owner_id=snapshot["owner_id"],
                memory_type=snapshot["type"],
                scope_type=snapshot["scope_type"],
                project_id=snapshot["project_id"],
                vector=vector,
            )

    async def _mark_checked(self, row: Memory, outcome: str) -> None:
        row.memory_metadata = {
            **row.memory_metadata,
            "_consolidation_checked_at": datetime.now(UTC).isoformat(),
            "_consolidation_last_outcome": outcome,
        }
        await self._repository.session.commit()

    @staticmethod
    def _record(row: Memory) -> MemoryRecord:
        return MemoryRecord(
            id=row.id,
            owner_id=row.owner_id,
            scope_type=MemoryScopeType(row.scope_type),
            project_id=row.project_id,
            type=MemoryType(row.type),
            content=row.content,
            metadata=row.memory_metadata,
            importance_score=row.importance_score,
            created_at=row.created_at,
            updated_at=row.updated_at,
        )
