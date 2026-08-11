"""Persistence for per-metric evaluation scores (EVALUATION_PLAN.md §14/§16 phase 6)."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import ColumnElement, and_, case, func, or_, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.enums import EvalScoreSource
from app.models.eval_score import EvalScore
from app.models.generation_usage import GenerationUsage
from app.models.user import User

ONLINE_FINGERPRINT_FIELDS = (
    "surface",
    "prompt_version",
    "chunking_strategy",
    "embedding_model",
    "reranker",
    "routing_strategy",
)
"""
The `GenerationUsage` columns E9's online segment analysis can group by
-- mirrors `config_fingerprint.py`'s fingerprint fields exactly (plus
`routing_strategy`, populated separately by `RoutingService`). A closed
list, not an arbitrary caller-supplied column name, since
`aggregate_online_by_fingerprint` uses `getattr(GenerationUsage, ...)` --
validating against this tuple first is what keeps that safe.
"""


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
    ) -> EvalScore | None:
        """
        Insert one score row. `on_conflict_do_nothing` on
        `(generation_id, metric_name, source)`: this is a defensive
        backstop against a race between two concurrent job ticks, not the
        primary exactly-once mechanism -- `GenerationUsageRepository.
        list_unscored_since()`'s anti-join is what normally prevents a
        generation from being picked up twice.

        Returns the inserted row, or `None` when the insert conflicted
        (`RETURNING` produces nothing for a no-op'd insert) -- callers
        that need the new row's id (e.g. `OnlineScoringJob`'s LangSmith
        sync, keyed on `EvalScore.id`) treat `None` as "nothing new to
        sync," not an error.
        """

        result = await self._session.execute(
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
            .returning(EvalScore)
        )
        return result.scalar_one_or_none()

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

    async def list_for_owner_page(
        self,
        owner_id: UUID,
        *,
        metric_name: str | None = None,
        source: str | None = None,
        since: datetime | None = None,
        limit: int,
        offset: int,
    ) -> tuple[list[EvalScore], int]:
        """
        One page of an owner's `eval_scores` rows, newest first (E7's
        drill-down view). `metric_name`/`source`/`since` are optional
        narrowing filters -- e.g. `source="human_feedback"` alone to see
        just that user's thumbs up/down history.
        """

        conditions: list[ColumnElement[bool]] = [EvalScore.owner_id == owner_id]

        if metric_name:
            conditions.append(EvalScore.metric_name == metric_name)

        if source:
            conditions.append(EvalScore.source == source)

        if since is not None:
            conditions.append(EvalScore.created_at >= since)

        filters = and_(*conditions)

        count_statement = select(func.count()).select_from(EvalScore).where(filters)
        total = await self._session.scalar(count_statement) or 0

        statement = (
            select(EvalScore)
            .where(filters)
            .order_by(EvalScore.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        rows = (await self._session.execute(statement)).scalars().all()

        return list(rows), total

    async def search_owners_with_scores(
        self,
        *,
        search: str | None = None,
        limit: int,
        offset: int,
    ) -> tuple[list[tuple[User, int]], int]:
        """
        Owners who have at least one `eval_scores` row, with their row
        count, ordered by most rows first -- the "pick a user" step
        before E7's drill-down view. `search` matches email/username
        (case-insensitive substring). Excludes offline-benchmark rows'
        `NULL` owner_id implicitly (the join only matches real users).
        """

        conditions: list[ColumnElement[bool]] = []
        if search:
            pattern = f"%{search.lower()}%"
            conditions.append(
                or_(
                    func.lower(User.email).like(pattern),
                    func.lower(func.coalesce(User.username, "")).like(pattern),
                )
            )
        filters = and_(*conditions) if conditions else None

        base = select(User.id).join(EvalScore, EvalScore.owner_id == User.id)
        if filters is not None:
            base = base.where(filters)
        base = base.group_by(User.id)

        count_statement = select(func.count()).select_from(base.subquery())
        total = await self._session.scalar(count_statement) or 0

        score_count = func.count(EvalScore.id).label("score_count")
        statement = (
            select(User, score_count)
            .join(EvalScore, EvalScore.owner_id == User.id)
            .group_by(User.id)
            .order_by(score_count.desc())
            .limit(limit)
            .offset(offset)
        )
        if filters is not None:
            statement = statement.where(filters)

        rows = (await self._session.execute(statement)).all()

        return [(row[0], row[1]) for row in rows], total

    async def list_offline_page(
        self,
        *,
        dataset_example_id: str | None = None,
        metric_name: str | None = None,
        limit: int,
        offset: int,
    ) -> tuple[list[EvalScore], int]:
        """
        One page of `source=offline_benchmark` rows, newest first --
        deliberately **not** owner-scoped, unlike `list_for_owner_page()`:
        offline rows have no `owner_id` (they score a fixed golden-set
        example, not a live production generation), so an owner-scoped
        endpoint can never surface them. This is the read path the E7
        dashboard's "Offline" filter needs but didn't have -- filtering
        `list_for_owner_page()` by `source="offline_benchmark"` always
        returns zero rows regardless of which owner is selected.
        """

        conditions: list[ColumnElement[bool]] = [
            EvalScore.source == EvalScoreSource.OFFLINE_BENCHMARK.value
        ]

        if dataset_example_id:
            conditions.append(EvalScore.dataset_example_id == dataset_example_id)

        if metric_name:
            conditions.append(EvalScore.metric_name == metric_name)

        filters = and_(*conditions)

        count_statement = select(func.count()).select_from(EvalScore).where(filters)
        total = await self._session.scalar(count_statement) or 0

        statement = (
            select(EvalScore)
            .where(filters)
            .order_by(EvalScore.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        rows = (await self._session.execute(statement)).scalars().all()

        return list(rows), total

    async def search_offline_examples(
        self,
        *,
        search: str | None = None,
        limit: int,
        offset: int,
    ) -> tuple[list[tuple[str, int, datetime]], int]:
        """
        Distinct `dataset_example_id`s with at least one offline-benchmark
        score, each with its row count and most recent run timestamp,
        ordered by most-recently-run first -- the "pick an example" step
        before drilling into its `list_offline_page()` history. `search`
        matches `dataset_example_id` (case-insensitive substring).
        """

        conditions: list[ColumnElement[bool]] = [
            EvalScore.source == EvalScoreSource.OFFLINE_BENCHMARK.value
        ]
        if search:
            conditions.append(func.lower(EvalScore.dataset_example_id).like(f"%{search.lower()}%"))
        filters = and_(*conditions)

        base = (
            select(EvalScore.dataset_example_id)
            .where(filters)
            .group_by(EvalScore.dataset_example_id)
        )
        count_statement = select(func.count()).select_from(base.subquery())
        total = await self._session.scalar(count_statement) or 0

        score_count = func.count(EvalScore.id).label("score_count")
        latest_run_at = func.max(EvalScore.created_at).label("latest_run_at")
        statement = (
            select(EvalScore.dataset_example_id, score_count, latest_run_at)
            .where(filters)
            .group_by(EvalScore.dataset_example_id)
            .order_by(latest_run_at.desc())
            .limit(limit)
            .offset(offset)
        )
        rows = (await self._session.execute(statement)).all()

        return [(row[0], row[1], row[2]) for row in rows], total

    async def aggregate_online_by_fingerprint(
        self,
        *,
        metric_name: str,
        fingerprint_field: str,
    ) -> list[tuple[str | None, int, float | None, float | None]]:
        """
        Online-sampled `eval_scores` rows for `metric_name`, joined to
        `generation_usage` on `generation_id` and grouped by one config-
        fingerprint field (E9, EVALUATION_IMPLEMENTATION_TRACKER.md) --
        e.g. "did average `faithfulness` differ between `prompt_version`
        'chat-v1' and 'chat-v2'." `fingerprint_field` must be one of
        `ONLINE_FINGERPRINT_FIELDS`; the caller (the API route) is
        responsible for that validation before calling this, matching
        this repository's existing convention of trusting its own
        service-layer callers.

        Offline-benchmark rows have no `generation_usage` row to join
        against (no live production request produced them) -- this only
        ever sees online-sampled traffic. See
        `list_offline_scores_for_metric` for the offline/content-segment
        side of E9, which needs a different join entirely (the golden
        dataset's `query_type` lives in a JSON file, not Postgres).
        """

        column = getattr(GenerationUsage, fingerprint_field)

        count = func.count(EvalScore.id)
        avg_score = func.avg(EvalScore.score)
        pass_rate = func.avg(
            case((EvalScore.passed.is_(True), 1.0), (EvalScore.passed.is_(False), 0.0))
        )

        statement = (
            select(column, count, avg_score, pass_rate)
            .join(GenerationUsage, GenerationUsage.generation_id == EvalScore.generation_id)
            .where(
                EvalScore.metric_name == metric_name,
                EvalScore.source == EvalScoreSource.ONLINE_SAMPLED.value,
            )
            .group_by(column)
            .order_by(column)
        )

        rows = (await self._session.execute(statement)).all()

        return [(row[0], row[1], row[2], row[3]) for row in rows]

    async def list_offline_scores_for_metric(
        self,
        *,
        metric_name: str,
        limit: int = 5000,
    ) -> list[EvalScore]:
        """
        Every `offline_benchmark` row for one metric, unpaginated (up to
        `limit`) -- feeds E9's content-segment aggregation, which groups
        by the golden dataset's `query_type`/`difficulty`/`workflow`
        fields. Those fields live in `datasets/golden/rag_answer_gold.json`,
        not Postgres, so the grouping itself has to happen in Python
        (`app/services/segment_analysis.py`) after this fetch, not in
        SQL like `aggregate_online_by_fingerprint` above. `limit` is a
        safety cap, not a real pagination control -- the golden set is
        ~100 examples, so even a few dozen re-runs stays well under it.
        """

        statement = (
            select(EvalScore)
            .where(
                EvalScore.metric_name == metric_name,
                EvalScore.source == EvalScoreSource.OFFLINE_BENCHMARK.value,
            )
            .order_by(EvalScore.created_at.desc())
            .limit(limit)
        )

        rows = (await self._session.execute(statement)).scalars().all()

        return list(rows)
