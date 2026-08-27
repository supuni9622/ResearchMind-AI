"""Request-scoped dependencies for `eval_scores` (E5/E6/E7)."""

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.repositories.eval_score import EvalScoreRepository


def get_eval_score_repository(
    session: AsyncSession = Depends(get_db),
) -> EvalScoreRepository:
    return EvalScoreRepository(session)
