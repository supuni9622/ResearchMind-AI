"""Authenticated generation-usage reporting endpoints."""

from datetime import UTC, datetime

from fastapi import APIRouter, Depends

from app.auth.dependencies import get_current_user
from app.dependencies.generation_usage import get_generation_usage_repository
from app.models.user import User
from app.repositories.generation_usage import GenerationUsageRepository
from app.schemas.generation_usage import GenerationUsageSummary

router = APIRouter(prefix="/usage", tags=["Usage"])


@router.get(
    "/summary",
    response_model=GenerationUsageSummary,
    summary="Read the current user's estimated generation cost summary",
)
async def generation_usage_summary(
    current_user: User = Depends(get_current_user),
    repository: GenerationUsageRepository = Depends(get_generation_usage_repository),
) -> GenerationUsageSummary:
    now = datetime.now(UTC)
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    return GenerationUsageSummary(
        **await repository.summary_for_owner(current_user.id, month_start)
    )
