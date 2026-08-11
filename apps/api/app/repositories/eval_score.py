"""Persistence for per-metric evaluation scores (EVALUATION_PLAN.md §14/§16 phase 6)."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.enums import EvalScoreSource
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

    async def upsert(
        self,
        *,
        owner_id: UUID,
        generation_id: UUID,
        metric_name: str,
        score: float | None,
        passed: bool | None,
        reason: str | None,
        source: str,
        sample_category: str | None = None,
    ) -> EvalScore:
        """
        Insert or update the score for this `(generation_id, metric_name,
        source)` triple. Unlike `record()`'s insert-only "first score
        wins" semantics (right for the online scoring job, where a
        generation should never be re-scored once it has a row), a
        mirrored human-feedback score must reflect the user's *latest*
        rating -- matches `FeedbackRepository.upsert()`'s "changing your
        mind updates the same record" semantics exactly, including the
        `populate_existing` fix that repository's own tests caught
        (SQLAlchemy's ORM-enabled `RETURNING` doesn't refresh an
        already identity-mapped object by default).
        """

        statement = (
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
            )
            .on_conflict_do_update(
                constraint="uq_eval_scores_generation_metric_source",
                set_={
                    "score": score,
                    "passed": passed,
                    "reason": reason,
                    "sample_category": sample_category,
                },
            )
            .returning(EvalScore)
        )
        result = await self._session.execute(
            statement,
            execution_options={"populate_existing": True},
        )
        return result.scalar_one()

    async def record_offline_example(
        self,
        *,
        dataset_example_id: str,
        metric_name: str,
        score: float | None,
        passed: bool | None,
        reason: str | None,
    ) -> None:
        """
        Insert one offline-benchmark score row (E6, EVALUATION_PLAN.md §16
        phase 6/7) -- no `owner_id`/`generation_id`, since this scores a
        fixed golden-dataset example, not a live production generation.
        `source` is always `EvalScoreSource.OFFLINE_BENCHMARK`; passed as
        a literal here rather than a parameter since every caller of this
        specific method needs exactly that value (unlike `record()`,
        which is shared across every online free-check/judge metric).

        Deliberately plain `insert()`, no conflict handling: offline rows
        are append-only by design (see `EvalScore`'s own docstring) --
        every benchmark run is a new trend data point, not a replacement
        of the last one.
        """

        await self._session.execute(
            insert(EvalScore).values(
                owner_id=None,
                generation_id=None,
                dataset_example_id=dataset_example_id,
                metric_name=metric_name,
                score=score,
                passed=passed,
                reason=reason,
                source=EvalScoreSource.OFFLINE_BENCHMARK.value,
                sample_category=None,
            )
        )
