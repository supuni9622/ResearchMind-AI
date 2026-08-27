"""Transaction boundary for explicit feedback about injected memory."""

from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.enums import EvalScoreSource, FeedbackSurface, MemoryFeedbackSignal
from app.models.memory_feedback import MemoryFeedback
from app.repositories.eval_score import EvalScoreRepository
from app.repositories.generation_usage import GenerationUsageRepository
from app.repositories.memory_feedback import MemoryFeedbackRepository

MEMORY_USER_SIGNAL_METRIC = "memory_user_signal"


class MemoryFeedbackService:
    def __init__(
        self,
        *,
        session: AsyncSession,
        repository: MemoryFeedbackRepository,
        generation_usage_repository: GenerationUsageRepository,
        eval_score_repository: EvalScoreRepository,
    ) -> None:
        self._session = session
        self._repository = repository
        self._generation_usage_repository = generation_usage_repository
        self._eval_score_repository = eval_score_repository

    async def submit(
        self,
        *,
        owner_id: UUID,
        generation_id: UUID,
        surface: FeedbackSurface,
        signal: MemoryFeedbackSignal,
    ) -> MemoryFeedback:
        generation = await self._generation_usage_repository.get_owned_generation(
            owner_id=owner_id, generation_id=generation_id
        )
        if generation is None or not generation.injected_memory_ids:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No memory-backed generation was found",
            )
        feedback = await self._repository.upsert(
            owner_id=owner_id,
            generation_id=generation_id,
            surface=surface,
            signal=signal,
        )
        helped = signal == MemoryFeedbackSignal.HELPED
        await self._eval_score_repository.upsert(
            owner_id=owner_id,
            generation_id=generation_id,
            metric_name=MEMORY_USER_SIGNAL_METRIC,
            score=1.0 if helped else 0.0,
            passed=helped,
            reason=f"user reported memory {signal.value}",
            source=EvalScoreSource.HUMAN_FEEDBACK.value,
        )
        await self._session.commit()
        return feedback
