"""Persistence queries for the append-only generation usage ledger."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.runtime.generation.models import GenerationResult
from app.models.generation_usage import GenerationUsage


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
            )
            .on_conflict_do_nothing(index_elements=[GenerationUsage.request_id])
        )

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
