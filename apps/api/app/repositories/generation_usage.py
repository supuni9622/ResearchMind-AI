"""Persistence queries for the append-only generation usage ledger."""

from __future__ import annotations

from datetime import date, datetime
from typing import TypedDict
from uuid import UUID

from sqlalchemy import cast, func, or_, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.types import Date

from app.ai.runtime.generation.models import GenerationResult
from app.models.generation_usage import GenerationUsage
from app.models.research_run import ResearchRun


class ConversationUsageRollup(TypedDict):
    conversation_id: UUID
    total_cost_usd: float
    total_requests: int
    total_tokens: int


class GenerationUsageRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def record(self, result: GenerationResult) -> None:
        """Insert a usage row once; repeated completion handling is a no-op."""

        owner_id = result.request.owner_id
        if owner_id is None:
            return

        statistics = result.statistics
        await self._session.execute(
            insert(GenerationUsage)
            .values(
                request_id=result.request.request_id,
                generation_id=result.generation_id,
                langsmith_run_id=result.langsmith_run_id,
                owner_id=owner_id,
                conversation_id=result.request.conversation_id,
                session_id=result.request.session_id,
                provider=statistics.provider.value,
                model=statistics.model,
                runtime=(
                    result.request.metadata.get("usage_category")
                    or (result.request.runtime.value if result.request.runtime else None)
                ),
                prompt_tokens=statistics.prompt_tokens,
                completion_tokens=statistics.completion_tokens,
                total_tokens=statistics.total_tokens,
                estimated_cost_usd=statistics.estimated_cost_usd,
                cache_hit=statistics.cache_hit,
                streamed=statistics.streamed,
                surface=result.request.surface,
                prompt_version=result.request.prompt_version,
                chunking_strategy=result.request.chunking_strategy,
                embedding_model=result.request.embedding_model,
                reranker=result.request.reranker,
                routing_strategy=(
                    statistics.routing_strategy.value if statistics.routing_strategy else None
                ),
            )
            .on_conflict_do_nothing(index_elements=[GenerationUsage.request_id])
        )

    async def get_langsmith_run_id(self, generation_id: UUID) -> UUID | None:
        """
        For `FeedbackService`'s LangSmith-feedback follow-up (E21): looks
        up the run a user's feedback should attach to in LangSmith's own
        UI. Returns `None` for a `generation_id` this table has no row
        for, or whose row predates this column / has no configured trace
        -- callers must treat that as "skip the LangSmith call," not an
        error.
        """

        statement = select(GenerationUsage.langsmith_run_id).where(
            GenerationUsage.generation_id == generation_id
        )
        return (await self._session.execute(statement)).scalars().first()

    async def daily_cost_totals(self, *, since: datetime) -> list[tuple[date, float]]:
        """System-wide (not owner-scoped) cost per calendar day since `since`.

        Feeds the cost-forecast rolling average (`app/services/cost_forecast.py`,
        EVALUATION_IMPLEMENTATION_TRACKER.md E18) -- deliberately system-wide,
        distinct from `summary_for_owner`'s per-user totals, since a burn-rate
        projection is a product-level question, not a per-user one.
        """

        day_column = cast(GenerationUsage.completed_at, Date)
        statement = (
            select(day_column, func.sum(GenerationUsage.estimated_cost_usd))
            .where(GenerationUsage.completed_at >= since)
            .group_by(day_column)
            .order_by(day_column)
        )
        rows = (await self._session.execute(statement)).all()
        return [(row[0], float(row[1])) for row in rows]

    async def sum_cost_for_session(self, session_id: UUID) -> float:
        """Sum estimated cost recorded so far for one runtime session (e.g. a research run).

        Used for soft, best-effort budget checks; usage recording is itself
        best-effort/fail-open, so this is an estimate, not an exact ceiling.
        """

        statement = select(func.coalesce(func.sum(GenerationUsage.estimated_cost_usd), 0)).where(
            GenerationUsage.session_id == session_id,
        )
        return float((await self._session.execute(statement)).scalar_one())

    async def sum_for_conversation(
        self,
        conversation_id: UUID,
        owner_id: UUID,
    ) -> ConversationUsageRollup:
        """Roll up cost/requests/tokens for every generation call tagged with
        this conversation: Linear Research turns (tagged `conversation_id`
        directly) plus Deep Research runs belonging to it (tagged
        `session_id = research_run.id` instead, since Deep Research bills
        per-run -- see `ResearchPlanner.plan` et al.). `owner_id` is a
        defense-in-depth scope, not the only check -- callers must still
        verify the caller owns `conversation_id` before invoking this.
        """

        run_ids = select(ResearchRun.id).where(
            ResearchRun.conversation_id == conversation_id,
            ResearchRun.owner_id == owner_id,
        )
        statement = select(
            func.coalesce(func.sum(GenerationUsage.estimated_cost_usd), 0),
            func.count(GenerationUsage.id),
            func.coalesce(func.sum(GenerationUsage.total_tokens), 0),
        ).where(
            GenerationUsage.owner_id == owner_id,
            or_(
                GenerationUsage.conversation_id == conversation_id,
                GenerationUsage.session_id.in_(run_ids),
            ),
        )
        cost, requests, tokens = (await self._session.execute(statement)).one()
        return {
            "conversation_id": conversation_id,
            "total_cost_usd": float(cost),
            "total_requests": int(requests),
            "total_tokens": int(tokens),
        }

    async def summary_for_owner(
        self,
        owner_id: UUID,
        month_start: datetime,
    ) -> dict[str, float | int]:
        total = await self._aggregate(owner_id)
        month = await self._aggregate(owner_id, month_start=month_start)
        memory_extraction_cost, memory_extraction_requests = await self._runtime_aggregate(
            owner_id,
            runtime="memory_extraction",
        )
        answer_turns = await self._answer_turn_count(owner_id)
        return {
            "total_cost_usd": total[0],
            "total_requests": total[1],
            "total_tokens": total[2],
            "month_cost_usd": month[0],
            "month_requests": month[1],
            "month_tokens": month[2],
            "memory_extraction_cost_usd": memory_extraction_cost,
            "memory_extraction_requests": memory_extraction_requests,
            "answer_turns": answer_turns,
            "memory_extraction_cost_per_100_turns": (
                memory_extraction_cost / answer_turns * 100 if answer_turns else 0.0
            ),
        }

    async def _runtime_aggregate(self, owner_id: UUID, *, runtime: str) -> tuple[float, int]:
        statement = select(
            func.coalesce(func.sum(GenerationUsage.estimated_cost_usd), 0),
            func.count(GenerationUsage.id),
        ).where(
            GenerationUsage.owner_id == owner_id,
            GenerationUsage.runtime == runtime,
        )
        cost, requests = (await self._session.execute(statement)).one()
        return float(cost), int(requests)

    async def _answer_turn_count(self, owner_id: UUID) -> int:
        statement = select(func.count(GenerationUsage.id)).where(
            GenerationUsage.owner_id == owner_id,
            GenerationUsage.runtime.in_(("chat", "research")),
        )
        return int((await self._session.execute(statement)).scalar_one())

    async def _aggregate(
        self,
        owner_id: UUID,
        month_start: datetime | None = None,
    ) -> tuple[float, int, int]:
        statement = select(
            func.coalesce(func.sum(GenerationUsage.estimated_cost_usd), 0),
            func.count(GenerationUsage.id),
            func.coalesce(func.sum(GenerationUsage.total_tokens), 0),
        ).where(GenerationUsage.owner_id == owner_id)
        if month_start is not None:
            statement = statement.where(GenerationUsage.completed_at >= month_start)
        cost, requests, tokens = (await self._session.execute(statement)).one()
        return float(cost), int(requests), int(tokens)
