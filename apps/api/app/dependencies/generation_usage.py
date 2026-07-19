"""Request-scoped dependencies for generation usage reporting."""

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.repositories.generation_usage import GenerationUsageRepository


def get_generation_usage_repository(
    session: AsyncSession = Depends(get_db),
) -> GenerationUsageRepository:
    return GenerationUsageRepository(session)
