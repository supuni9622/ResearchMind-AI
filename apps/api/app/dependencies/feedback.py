"""Request-scoped dependencies for feedback."""

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.runtime.generation.comment_classification.create import (
    create_comment_classification_service,
)
from app.ai.runtime.generation.comment_classification.service import (
    CommentClassificationService,
)
from app.db.session import SessionFactory, get_db
from app.dependencies.eval_score import get_eval_score_repository
from app.dependencies.generation_usage import get_generation_usage_repository
from app.repositories.eval_score import EvalScoreRepository
from app.repositories.feedback import FeedbackRepository
from app.repositories.generation_usage import GenerationUsageRepository
from app.repositories.memory_feedback import MemoryFeedbackRepository
from app.services.feedback import FeedbackService
from app.services.memory_feedback import MemoryFeedbackService
from app.services.preference_memory import PreferenceMemoryWriter


def get_comment_classification_service() -> CommentClassificationService:
    return create_comment_classification_service()


def get_feedback_repository(
    session: AsyncSession = Depends(get_db),
) -> FeedbackRepository:
    return FeedbackRepository(session)


def get_preference_memory_writer() -> PreferenceMemoryWriter:
    """Return a writer that owns a session separate from the request."""

    return PreferenceMemoryWriter(session_factory=SessionFactory)


def get_feedback_service(
    session: AsyncSession = Depends(get_db),
    repository: FeedbackRepository = Depends(get_feedback_repository),
    generation_usage_repository: GenerationUsageRepository = Depends(
        get_generation_usage_repository
    ),
    eval_score_repository: EvalScoreRepository = Depends(get_eval_score_repository),
    comment_classification_service: CommentClassificationService = Depends(
        get_comment_classification_service
    ),
    preference_memory_writer: PreferenceMemoryWriter = Depends(get_preference_memory_writer),
) -> FeedbackService:
    return FeedbackService(
        session=session,
        repository=repository,
        generation_usage_repository=generation_usage_repository,
        eval_score_repository=eval_score_repository,
        comment_classification_service=comment_classification_service,
        preference_memory_writer=preference_memory_writer,
    )


def get_memory_feedback_service(
    session: AsyncSession = Depends(get_db),
    generation_usage_repository: GenerationUsageRepository = Depends(
        get_generation_usage_repository
    ),
    eval_score_repository: EvalScoreRepository = Depends(get_eval_score_repository),
) -> MemoryFeedbackService:
    return MemoryFeedbackService(
        session=session,
        repository=MemoryFeedbackRepository(session),
        generation_usage_repository=generation_usage_repository,
        eval_score_repository=eval_score_repository,
    )
