"""Best-effort transaction boundary for durable generation accounting."""

from __future__ import annotations

import structlog

from app.ai.runtime.generation.models import GenerationResult
from app.db.session import SessionFactory
from app.repositories.generation_usage import GenerationUsageRepository

logger = structlog.get_logger()


class GenerationUsageService:
    async def record(self, result: GenerationResult) -> None:
        """Persist user-owned usage without breaking an already-completed reply."""

        if result.request.owner_id is None:
            return
        try:
            async with SessionFactory() as session:
                await GenerationUsageRepository(session).record(result)
                await session.commit()
        except Exception:
            logger.exception(
                "generation_usage.record_failed",
                request_id=str(result.request.request_id),
                owner_id=str(result.request.owner_id),
            )
