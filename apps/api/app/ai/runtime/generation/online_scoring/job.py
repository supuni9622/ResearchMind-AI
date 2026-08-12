"""
Online scoring job (E5, EVALUATION_PLAN.md §14/§16 phase 6).

Pulls recently-completed, answer-producing generations
(`GenerationUsage.surface` set), runs the free deterministic citation
check on all of them, and runs the Ragas LLM-judge suite on the subset
`decide_sampling()` selects. Persists one `eval_scores` row per metric.

**E16 follow-up (2026-08-12):** optionally also runs the rubric-adherence
judge on that same sampled subset, gated by `Settings.
eval_online_rubric_judge_enabled` (default off -- a genuinely new,
ongoing LLM-call cost). Golden-set examples have a curated per-example
`rubric`; a live production generation has no such thing, so this judges
against one fixed, generic quality rubric instead
(`_GENERIC_ONLINE_RUBRIC` below) rather than inventing a per-request
rubric. Deliberately rides the *existing* sampling decision rather than
adding a second, separately-tuned rate -- one more check within "LLM
judges run on the sampled subset" (§14), not a new cost-control knob to
reason about.

Deliberately does not import anything from repo-root `benchmarks/`: that
package is offline/CI tooling, one-directional today (`benchmarks/`
imports `app/`, never the reverse -- confirmed empirically, no existing
counter-example anywhere in this codebase), and this job is production
runtime code. `ScoreGenerationFn`/`_GenerationScoreReportLike` below are
local structural Protocols matching `benchmarks.generation.ragas_scoring.
score_generation`/`GenerationScoreReport`'s real shape -- the concrete
function and a real judge (`benchmarks.generation.ragas_scoring.
score_generation`, `benchmarks.generation.ragas_judge.
build_openai_ragas_judge()`) are wired in only at the process entrypoint
(`apps/worker/eval_scoring_main.py`), which is allowed to cross that
boundary the way `bootstrap/worker.py` already wires concrete
infrastructure into other workers.
"""

from __future__ import annotations

import random
from collections.abc import Awaitable, Callable, Sequence
from datetime import UTC, datetime, timedelta
from typing import Protocol
from uuid import UUID

import structlog
from app.ai.artifacts.exceptions import ArtifactNotFoundError
from app.ai.artifacts.generation.readers import GenerationArtifactReader
from app.ai.knowledge.context.citations.validity import check_prompt_context_citation_validity
from app.ai.observability.providers.langsmith.eval_score_sync import sync_eval_score
from app.ai.runtime.generation.online_scoring.sampling import (
    OnlineScoringConfig,
    decide_sampling,
)
from app.models.enums import EvalScoreSource
from app.models.eval_score import EvalScore
from app.models.generation_usage import GenerationUsage
from app.repositories.eval_score import EvalScoreRepository
from app.repositories.generation_usage import GenerationUsageRepository
from app.repositories.research_run import ResearchRunRepository

logger = structlog.get_logger()


class _MetricCheckResultLike(Protocol):
    """
    Declared as read-only `@property` members, not plain attributes --
    mypy checks plain `Protocol` attributes invariantly, which would
    reject the structurally-compatible-but-not-identical real
    `benchmarks.generation.ragas_scoring.MetricCheckResult` (and any test
    fake). Properties are checked covariantly instead, matching the exact
    workaround already documented in `ragas_scoring.py`'s own
    `GenerationJudge` Protocol.
    """

    @property
    def metric(self) -> str: ...

    @property
    def score(self) -> float: ...

    @property
    def passed(self) -> bool: ...

    @property
    def reason(self) -> str: ...


class _GenerationScoreReportLike(Protocol):
    @property
    def checks(self) -> Sequence[_MetricCheckResultLike]: ...


ScoreGenerationFn = Callable[..., Awaitable[_GenerationScoreReportLike]]
"""Structurally: `async def(*, question, answer, contexts, reference,
judge, rubric=None, rubric_judge=None) -> _GenerationScoreReportLike`."""

_GENERIC_ONLINE_RUBRIC = (
    "The answer directly addresses the question asked, is appropriately "
    "complete for its complexity (neither padded nor missing an obvious "
    "part of the question), and does not hedge or caveat unnecessarily "
    "when the retrieved evidence actually supports a direct answer."
)
"""E16 follow-up -- online generations have no per-example curated
`rubric` like golden-set examples do, so this is one fixed, generic
quality rubric applied uniformly instead of inventing a per-request one.
Only used when `Settings.eval_online_rubric_judge_enabled` is set."""


class OnlineScoringJob:
    def __init__(
        self,
        *,
        generation_usage_repository: GenerationUsageRepository,
        eval_score_repository: EvalScoreRepository,
        research_run_repository: ResearchRunRepository,
        artifact_reader: GenerationArtifactReader,
        config: OnlineScoringConfig,
        commit: Callable[[], Awaitable[None]],
        rollback: Callable[[], Awaitable[None]],
        score_generation_fn: ScoreGenerationFn | None = None,
        judge: object | None = None,
        rubric_judge: object | None = None,
        batch_size: int = 25,
        lookback_hours: float = 24.0,
        rng: random.Random | None = None,
        now: Callable[[], datetime] | None = None,
    ) -> None:
        self._generation_usage_repository = generation_usage_repository
        self._eval_score_repository = eval_score_repository
        self._research_run_repository = research_run_repository
        self._artifact_reader = artifact_reader
        self._config = config
        self._commit = commit
        self._rollback = rollback
        self._score_generation_fn = score_generation_fn
        self._judge = judge
        self._rubric_judge = rubric_judge
        """`None` unless `Settings.eval_online_rubric_judge_enabled` was
        set at composition time (see `apps/worker/eval_scoring_main.py`)
        -- same opt-in shape as `judge`/`score_generation_fn` above, not
        a new pattern."""
        self._batch_size = batch_size
        self._lookback_hours = lookback_hours
        self._rng = rng or random.Random()
        self._now = now or (lambda: datetime.now(UTC))

    async def run_once(self) -> int:
        """Score up to `batch_size` unscored generations. Returns how many
        were processed (not how many were sampled for judges) -- `0` means
        the caller should back off before polling again."""

        since = self._now() - timedelta(hours=self._lookback_hours)
        candidates = await self._generation_usage_repository.list_unscored_since(
            since=since,
            limit=self._batch_size,
        )

        for row in candidates:
            try:
                await self._score_one(row)
                await self._commit()
            except Exception:
                logger.exception(
                    "online_scoring_job.row_failed",
                    generation_id=str(row.generation_id),
                )
                await self._rollback()

        return len(candidates)

    async def _score_one(self, row: GenerationUsage) -> None:
        log = logger.bind(generation_id=str(row.generation_id), surface=row.surface)

        review_decision = await self._review_decision_for(row)
        sampling_decision = decide_sampling(
            guardrail_final_action=row.guardrail_final_action,
            review_decision=review_decision,
            prompt_version=row.prompt_version,
            config=self._config,
            random_value=self._rng.random(),
        )

        try:
            artifact = await self._artifact_reader.read(row.generation_id)
        except ArtifactNotFoundError:
            # Best-effort artifact persistence (Artifact Platform PRD §24)
            # means a completed generation can legitimately have no
            # artifact to score. Left unscored rather than retried
            # forever: it ages out of `list_unscored_since()`'s lookback
            # window on its own.
            log.warning("online_scoring_job.artifact_missing")
            return

        # Looked up once per generation, not once per metric -- reused
        # below for every sync_eval_score() call this row produces.
        langsmith_run_id = await self._generation_usage_repository.get_langsmith_run_id(
            row.generation_id
        )

        citation_report = check_prompt_context_citation_validity(
            content=artifact.response.content,
            prompt_context=artifact.request.prompt_context,
        )
        failed_reasons = [check.reason for check in citation_report.checks if not check.passed]
        citation_score = await self._eval_score_repository.record(
            owner_id=row.owner_id,
            generation_id=row.generation_id,
            metric_name="citation_validity",
            score=1.0 - citation_report.fabricated_citation_rate,
            passed=citation_report.valid,
            reason="; ".join(failed_reasons) if failed_reasons else "all citation checks passed",
            source=EvalScoreSource.ONLINE_SAMPLED.value,
            sample_category=sampling_decision.category.value,
        )
        self._sync_to_langsmith(langsmith_run_id, citation_score)

        if not sampling_decision.should_score_judges:
            log.debug("online_scoring_job.judges_skipped", reason=sampling_decision.reason)
            return

        if self._score_generation_fn is None or self._judge is None:
            log.debug("online_scoring_job.no_judge_configured", reason=sampling_decision.reason)
            return

        contexts = [chunk.content for chunk in artifact.request.prompt_context.chunks]
        report = await self._score_generation_fn(
            question=artifact.request.user_prompt,
            answer=artifact.response.content,
            contexts=contexts,
            reference=None,
            judge=self._judge,
            # E16 follow-up: rubric/rubric_judge default to None on
            # score_generation()'s own side when self._rubric_judge is
            # None (not wired at composition time), so this is a no-op
            # there -- no separate enabled-check needed here.
            rubric=(_GENERIC_ONLINE_RUBRIC if self._rubric_judge is not None else None),
            rubric_judge=self._rubric_judge,
        )
        for check in report.checks:
            judge_score = await self._eval_score_repository.record(
                owner_id=row.owner_id,
                generation_id=row.generation_id,
                metric_name=check.metric,
                score=check.score,
                passed=check.passed,
                reason=check.reason,
                source=EvalScoreSource.ONLINE_SAMPLED.value,
                sample_category=sampling_decision.category.value,
            )
            self._sync_to_langsmith(langsmith_run_id, judge_score)

    def _sync_to_langsmith(self, run_id: UUID | None, eval_score: EvalScore | None) -> None:
        """
        No-op when tracing wasn't configured for this generation
        (`run_id is None` -- matches `FeedbackService`'s same check
        before calling `sync_user_feedback`) or when `record()` no-op'd
        on a conflict (`eval_score is None` -- nothing new to mirror).
        `sync_eval_score()` itself is already best-effort/never-raises,
        this just supplies the two required, possibly-missing inputs.
        """

        if run_id is None or eval_score is None:
            return

        sync_eval_score(
            run_id=run_id,
            eval_score_id=eval_score.id,
            metric_name=eval_score.metric_name,
            score=eval_score.score,
            reason=eval_score.reason,
        )

    async def _review_decision_for(self, row: GenerationUsage) -> str | None:
        """Deep Research's `ResearchReview.decision` lives in `ResearchRun.
        budget_usage["review_decision"]` (see `execution.py`), keyed by
        `ResearchRun.id` -- which the synthesis call tags as `session_id`
        on `GenerationRequest` (see `runtime/research/synthesis/service.py`).
        `None` for Chat/Linear Research rows, which have no review step."""

        if row.surface != "deep_research" or row.session_id is None:
            return None

        run = await self._research_run_repository.get_by_id_for_owner(
            run_id=row.session_id,
            owner_id=row.owner_id,
        )
        if run is None:
            return None

        decision = (run.budget_usage or {}).get("review_decision")
        return decision if isinstance(decision, str) else None
