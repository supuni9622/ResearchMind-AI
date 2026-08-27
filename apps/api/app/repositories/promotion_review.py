"""Persistence for E10's promotion-review queue (EVALUATION_PLAN.md
§3/§15's "both directions" promotion loop).

Unreviewed candidates are derived live from `Feedback`/`eval_scores` --
see `list_candidates()` -- rather than snapshotted into
`promotion_reviews`, which only ever holds rows a human has already
acted on. Keeps this repository as the single source of truth for "has
this generation already been reviewed" without a separate sync step.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.enums import EvalScoreSource, FeedbackRating, PromotionCandidateSource
from app.models.eval_score import EvalScore
from app.models.feedback import Feedback
from app.models.promotion_review import PromotionReview


@dataclass(frozen=True)
class PromotionCandidate:
    source: PromotionCandidateSource
    owner_id: UUID
    generation_id: UUID
    reason: str
    created_at: datetime


class PromotionReviewRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def _reviewed_generation_ids(self) -> set[UUID]:
        statement = select(PromotionReview.generation_id)
        rows = (await self._session.execute(statement)).scalars().all()
        return set(rows)

    async def list_good_candidates(
        self,
        *,
        limit: int,
        offset: int,
    ) -> tuple[list[PromotionCandidate], int]:
        """Thumbs-up feedback, not yet reviewed -- the "good" direction of
        E10's promotion loop (not just harvesting failures)."""

        reviewed = await self._reviewed_generation_ids()

        conditions = [Feedback.rating == FeedbackRating.UP.value]
        if reviewed:
            conditions.append(Feedback.generation_id.notin_(reviewed))

        filters = and_(*conditions)

        count_statement = select(func.count()).select_from(Feedback).where(filters)
        total = await self._session.scalar(count_statement) or 0

        statement = (
            select(Feedback)
            .where(filters)
            .order_by(Feedback.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        rows = (await self._session.execute(statement)).scalars().all()

        candidates = [
            PromotionCandidate(
                source=PromotionCandidateSource.HUMAN_FEEDBACK,
                owner_id=row.owner_id,
                generation_id=row.generation_id,
                reason=row.comment or "thumbs up, no comment",
                created_at=row.created_at,
            )
            for row in rows
        ]
        return candidates, total

    async def list_failure_candidates(
        self,
        *,
        limit: int,
        offset: int,
    ) -> tuple[list[PromotionCandidate], int]:
        """Merges two signals per E10's own subtask wording -- "from E3's
        thumbs-down + E5's flagged-but-scored generations":
        - Feedback rows rated down with a comment E11 classified
          `objective` (a preference complaint should never reach here,
          per 1g).
        - Online-sampled `eval_scores` rows that failed a check
          (`passed=False`), deduplicated to the most recent failing
          check per generation -- a generation can fail several metrics
          at once, and the queue reviews the *generation*, not each
          metric separately.

        Merged and re-paginated in Python, not SQL -- this queue's
        expected volume is inherently low (gated by real feedback/
        guardrail-flag volume, same "needs real feedback volume" caveat
        the roadmap itself already applies to this whole item), so a
        UNION query's added complexity isn't worth it here.
        """

        reviewed = await self._reviewed_generation_ids()

        feedback_conditions = [
            Feedback.rating == FeedbackRating.DOWN.value,
            Feedback.comment_classification == "objective",
        ]
        if reviewed:
            feedback_conditions.append(Feedback.generation_id.notin_(reviewed))

        feedback_rows = (
            (
                await self._session.execute(
                    select(Feedback)
                    .where(and_(*feedback_conditions))
                    .order_by(Feedback.created_at.desc())
                )
            )
            .scalars()
            .all()
        )

        feedback_candidates = [
            PromotionCandidate(
                source=PromotionCandidateSource.HUMAN_FEEDBACK,
                owner_id=row.owner_id,
                generation_id=row.generation_id,
                reason=row.comment or "thumbs down",
                created_at=row.created_at,
            )
            for row in feedback_rows
        ]

        score_conditions = [
            EvalScore.source == EvalScoreSource.ONLINE_SAMPLED.value,
            EvalScore.passed.is_(False),
            EvalScore.owner_id.is_not(None),
            EvalScore.generation_id.is_not(None),
        ]
        if reviewed:
            score_conditions.append(EvalScore.generation_id.notin_(reviewed))

        # DISTINCT ON (generation_id), most-recent-first: one representative
        # failing check per generation, not one row per failing metric.
        score_statement = (
            select(EvalScore)
            .distinct(EvalScore.generation_id)
            .where(and_(*score_conditions))
            .order_by(EvalScore.generation_id, EvalScore.created_at.desc())
        )
        score_rows = (await self._session.execute(score_statement)).scalars().all()

        score_candidates = [
            PromotionCandidate(
                source=PromotionCandidateSource.ONLINE_FLAGGED,
                owner_id=row.owner_id,  # type: ignore[arg-type]
                generation_id=row.generation_id,  # type: ignore[arg-type]
                reason=f"{row.metric_name} failed: {row.reason or 'no reason recorded'}",
                created_at=row.created_at,
            )
            for row in score_rows
        ]

        merged = sorted(
            feedback_candidates + score_candidates, key=lambda c: c.created_at, reverse=True
        )
        total = len(merged)
        return merged[offset : offset + limit], total

    async def list_preference_candidates(
        self,
        *,
        limit: int,
        offset: int,
    ) -> tuple[list[PromotionCandidate], int]:
        """Thumbs-down feedback E11 classified `preference` rather than
        `objective` -- excluded from `list_failure_candidates()` by
        design (1g: a preference complaint should never silently
        contaminate `production_failures`), but a human reviewer may
        still disagree with the classifier's conservative call. Surfaced
        here, separately, so that override is possible instead of the
        feedback being permanently invisible to the queue."""

        reviewed = await self._reviewed_generation_ids()

        conditions = [
            Feedback.rating == FeedbackRating.DOWN.value,
            Feedback.comment_classification == "preference",
        ]
        if reviewed:
            conditions.append(Feedback.generation_id.notin_(reviewed))

        filters = and_(*conditions)

        count_statement = select(func.count()).select_from(Feedback).where(filters)
        total = await self._session.scalar(count_statement) or 0

        statement = (
            select(Feedback)
            .where(filters)
            .order_by(Feedback.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        rows = (await self._session.execute(statement)).scalars().all()

        candidates = [
            PromotionCandidate(
                source=PromotionCandidateSource.HUMAN_FEEDBACK,
                owner_id=row.owner_id,
                generation_id=row.generation_id,
                reason=f"{row.comment or 'thumbs down'} (classifier: preference)",
                created_at=row.created_at,
            )
            for row in rows
        ]
        return candidates, total

    async def create(
        self,
        *,
        source: str,
        direction: str,
        owner_id: UUID,
        generation_id: UUID,
        status: str,
        reviewed_by: UUID,
        question: str | None = None,
        reference_answer: str | None = None,
        contexts: list[str] | None = None,
        reference_context_ids: list[str] | None = None,
        expected_citation_ids: list[str] | None = None,
        query_type: str | None = None,
        difficulty: str | None = None,
        workflow: str | None = None,
        rubric: str | None = None,
        failure_category: str | None = None,
    ) -> PromotionReview:
        review = PromotionReview(
            source=source,
            direction=direction,
            owner_id=owner_id,
            generation_id=generation_id,
            status=status,
            reviewed_by=reviewed_by,
            question=question,
            reference_answer=reference_answer,
            contexts=contexts,
            reference_context_ids=reference_context_ids,
            expected_citation_ids=expected_citation_ids,
            query_type=query_type,
            difficulty=difficulty,
            workflow=workflow,
            rubric=rubric,
            failure_category=failure_category,
        )
        self._session.add(review)
        await self._session.flush()
        return review

    async def list_confirmed_unsynced(self) -> list[PromotionReview]:
        """Feeds `sync_promoted_examples.py` -- confirmed rows not yet
        appended to the actual dataset JSON files."""

        statement = select(PromotionReview).where(
            PromotionReview.status == "confirmed",
            PromotionReview.synced.is_(False),
        )
        return list((await self._session.execute(statement)).scalars().all())

    async def mark_synced(self, review_id: UUID) -> None:
        review = await self._session.get(PromotionReview, review_id)
        if review is None:
            return
        review.synced = True
        review.synced_at = datetime.now(UTC)
        await self._session.flush()
