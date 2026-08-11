"""Persistence for per-metric evaluation scores (EVALUATION_PLAN.md §14/§16 phase 6)."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.eval_score import EvalScore


class EvalScoreRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def record(
        self,
        *,
        owner_id: UUID,
        generation_id: UUID,
        metric_name: str,
        score: float | None,
        passed: bool | None,
        reason: str | None,
        source: str,
        sample_category: str | None,
        dataset_example_id: str | None = None,
    ) -> None:
        """
        Insert one score row. `on_conflict_do_nothing` on
        `(generation_id, metric_name, source)`: this is a defensive
        backstop against a race between two concurrent job ticks, not the
        primary exactly-once mechanism -- `GenerationUsageRepository.
        list_unscored_since()`'s anti-join is what normally prevents a
        generation from being picked up twice.
        """

        await self._session.execute(
            insert(EvalScore)
            .values(
                owner_id=owner_id,
                generation_id=generation_id,
                metric_name=metric_name,
                score=score,
                passed=passed,
                reason=reason,
                source=source,
                sample_category=sample_category,
                dataset_example_id=dataset_example_id,
            )
            .on_conflict_do_nothing(constraint="uq_eval_scores_generation_metric_source")
        )
