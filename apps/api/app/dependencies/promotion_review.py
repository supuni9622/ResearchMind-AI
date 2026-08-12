"""Request-scoped dependencies for E10's promotion-review queue."""

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.repositories.promotion_review import PromotionReviewRepository


def get_promotion_review_repository(
    session: AsyncSession = Depends(get_db),
) -> PromotionReviewRepository:
    return PromotionReviewRepository(session)
