"""Request-scoped dependencies for feedback."""

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.dependencies.generation_usage import get_generation_usage_repository
from app.repositories.feedback import FeedbackRepository
from app.repositories.generation_usage import GenerationUsageRepository
from app.services.feedback import FeedbackService


def get_feedback_repository(
    session: AsyncSession = Depends(get_db),
) -> FeedbackRepository:
    return FeedbackRepository(session)


def get_feedback_service(
    session: AsyncSession = Depends(get_db),
    repository: FeedbackRepository = Depends(get_feedback_repository),
    generation_usage_repository: GenerationUsageRepository = Depends(
        get_generation_usage_repository
    ),
) -> FeedbackService:
    return FeedbackService(
        session=session,
        repository=repository,
        generation_usage_repository=generation_usage_repository,
    )
