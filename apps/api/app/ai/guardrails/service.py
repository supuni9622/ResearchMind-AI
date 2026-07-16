from __future__ import annotations

from collections.abc import Coroutine
from typing import Any
from uuid import UUID

import structlog

from app.ai.guardrails.constants import SEVERITY_RISK_SCORES
from app.ai.guardrails.enums import (
    GuardrailAction,
    GuardrailCategory,
    GuardrailSeverity,
    GuardrailStage,
)
from app.ai.guardrails.models import (
    GuardrailIssue,
    GuardrailReport,
    GuardrailResult,
)
from app.ai.guardrails.policies.fail_policy import FailPolicy, is_blocking_crash
from app.ai.guardrails.policies.regeneration_policy import RegenerationPolicy
from app.ai.guardrails.policies.risk_policy import RiskPolicy
from app.ai.guardrails.policies.runtime_policy import RuntimePolicy
from app.ai.guardrails.registry import GuardrailRegistry
from app.ai.guardrails.runtime.execution_limits import BudgetPolicy, ExecutionState
from app.ai.guardrails.scoring.overall_risk import compute_overall_risk
from app.ai.knowledge.context.citations.models import Citation
from app.ai.knowledge.context.models import ContextChunk
from app.ai.runtime.generation.models import GenerationRequest, GenerationResult

logger = structlog.get_logger()

_CRASH_CODE = "guardrail_crashed"

_ACTION_PRECEDENCE: dict[GuardrailAction, int] = {
    GuardrailAction.ALLOW: 0,
    GuardrailAction.WARN: 1,
    GuardrailAction.REGENERATE: 2,
    GuardrailAction.BLOCK: 3,
    GuardrailAction.ESCALATE: 4,
}


class GuardrailService:
    """
    Full Guardrails flow (PRD §15): input -> retrieval -> generation ->
    runtime -> report. Each stage can also be run independently, mirroring
    `ValidationService`.
    """

    def __init__(
        self,
        registry: GuardrailRegistry,
        *,
        fail_policy: FailPolicy = FailPolicy.FAIL_OPEN,
        risk_policy: RiskPolicy = RiskPolicy.MEDIUM,
        regeneration_policy: RegenerationPolicy | None = None,
        runtime_policy: RuntimePolicy | None = None,
    ) -> None:
        self._registry = registry

        self._fail_policy = fail_policy

        self._risk_policy = risk_policy

        self._regeneration_policy = regeneration_policy or RegenerationPolicy()

        self._runtime_policy = runtime_policy or RuntimePolicy()

    @property
    def guardrail_names(
        self,
    ) -> list[str]:
        return [
            *(g.name for g in self._registry.input_guardrails),
            *(g.name for g in self._registry.retrieval_guardrails),
            *(g.name for g in self._registry.generation_guardrails),
            *(g.name for g in self._registry.runtime_guardrails),
        ]

    # ==========================================================
    # Per-stage
    # ==========================================================

    async def evaluate_input(
        self,
        request: GenerationRequest,
    ) -> GuardrailResult:

        issues: list[GuardrailIssue] = []

        for guardrail in self._registry.input_guardrails:
            issues.extend(
                await self._run_check(
                    guardrail.name,
                    GuardrailStage.INPUT,
                    guardrail.check(request),
                )
            )

        return self._aggregate(
            GuardrailStage.INPUT,
            issues,
        )

    async def evaluate_retrieval(
        self,
        chunks: list[ContextChunk],
        citations: list[Citation] | None = None,
    ) -> GuardrailResult:

        issues: list[GuardrailIssue] = []

        for guardrail in self._registry.retrieval_guardrails:
            issues.extend(
                await self._run_check(
                    guardrail.name,
                    GuardrailStage.RETRIEVAL,
                    guardrail.check(chunks),
                )
            )

            #
            # citation_integrity.py needs both chunks and citations, which
            # doesn't fit the shared `check(chunks)` signature — rather
            # than widen `RetrievalGuardrailInterface` for one consumer,
            # a guardrail may optionally expose `check_citations()`,
            # called here when citations are actually available.
            #

            check_citations = getattr(guardrail, "check_citations", None)

            if citations is not None and check_citations is not None:
                issues.extend(
                    await self._run_check(
                        guardrail.name,
                        GuardrailStage.RETRIEVAL,
                        check_citations(
                            chunks=chunks,
                            citations=citations,
                        ),
                    )
                )

        return self._aggregate(
            GuardrailStage.RETRIEVAL,
            issues,
        )

    async def evaluate_generation(
        self,
        result: GenerationResult,
    ) -> GuardrailResult:

        issues: list[GuardrailIssue] = []

        for guardrail in self._registry.generation_guardrails:
            issues.extend(
                await self._run_check(
                    guardrail.name,
                    GuardrailStage.GENERATION,
                    guardrail.check(result),
                )
            )

        return self._aggregate(
            GuardrailStage.GENERATION,
            issues,
        )

    async def evaluate_runtime(
        self,
        state: ExecutionState,
        policy: BudgetPolicy,
    ) -> GuardrailResult:

        issues: list[GuardrailIssue] = []

        for guardrail in self._registry.runtime_guardrails:
            issues.extend(
                await self._run_check(
                    guardrail.name,
                    GuardrailStage.RUNTIME,
                    guardrail.check(state, policy),
                )
            )

        return self._aggregate(
            GuardrailStage.RUNTIME,
            issues,
        )

    # ==========================================================
    # Full report
    # ==========================================================

    async def evaluate(
        self,
        *,
        request: GenerationRequest,
        chunks: list[ContextChunk],
        result: GenerationResult,
        citations: list[Citation] | None = None,
        execution_state: ExecutionState | None = None,
        budget_policy: BudgetPolicy | None = None,
        run_id: UUID | None = None,
    ) -> GuardrailReport:

        input_result = await self.evaluate_input(
            request,
        )

        retrieval_result = await self.evaluate_retrieval(
            chunks,
            citations,
        )

        generation_result = await self.evaluate_generation(
            result,
        )

        runtime_result: GuardrailResult | None = None

        if execution_state is not None and budget_policy is not None:
            runtime_result = await self.evaluate_runtime(
                execution_state,
                budget_policy,
            )

        overall_risk = compute_overall_risk(
            input_score=input_result.score,
            retrieval_score=retrieval_result.score,
            generation_score=generation_result.score,
            runtime_score=runtime_result.score if runtime_result else None,
        )

        stage_results = [input_result, retrieval_result, generation_result]

        if runtime_result is not None:
            stage_results.append(
                runtime_result,
            )

        blocked = any(stage.blocked for stage in stage_results)

        final_action = max(
            (stage.action for stage in stage_results),
            key=lambda action: _ACTION_PRECEDENCE[action],
        )

        report = GuardrailReport(
            input_result=input_result,
            retrieval_result=retrieval_result,
            generation_result=generation_result,
            runtime_result=runtime_result,
            overall_risk=overall_risk,
            final_action=final_action,
            blocked=blocked,
        )

        logger.info(
            "guardrails.evaluate.completed",
            run_id=str(run_id) if run_id else None,
            final_action=report.final_action.value,
            blocked=report.blocked,
            overall_risk=report.overall_risk,
            issue_count=len(report.issues),
        )

        return report

    # ==========================================================
    # Internal
    # ==========================================================

    async def _run_check(
        self,
        guardrail_name: str,
        stage: GuardrailStage,
        coro: Coroutine[Any, Any, list[GuardrailIssue]],
    ) -> list[GuardrailIssue]:
        """
        Runs a single guardrail check, converting a crash into a WARNING
        issue instead of propagating it — never lets one bad check take
        down the rest of a stage. Mirrors `ValidationService._crash_outcome`.
        """

        try:
            return list(
                await coro,
            )
        except Exception as exc:
            logger.warning(
                "guardrails.check_failed",
                guardrail=guardrail_name,
                stage=stage.value,
                error_type=type(exc).__name__,
                error=str(exc),
            )

            return [
                GuardrailIssue(
                    code=_CRASH_CODE,
                    severity=GuardrailSeverity.WARNING,
                    category=GuardrailCategory.SYSTEM,
                    stage=stage,
                    message=f"Guardrail '{guardrail_name}' crashed: {exc}",
                    metadata={
                        "guardrail": guardrail_name,
                    },
                )
            ]

    def _aggregate(
        self,
        stage: GuardrailStage,
        issues: list[GuardrailIssue],
    ) -> GuardrailResult:

        stamped = [
            issue.model_copy(
                update={
                    "stage": stage,
                },
            )
            for issue in issues
        ]

        has_error_or_critical = any(
            issue.severity in (GuardrailSeverity.ERROR, GuardrailSeverity.CRITICAL)
            for issue in stamped
        )

        has_critical = any(issue.severity == GuardrailSeverity.CRITICAL for issue in stamped)

        crashed = any(issue.code == _CRASH_CODE for issue in stamped)

        passed = not has_error_or_critical

        score = max(SEVERITY_RISK_SCORES[issue.severity] for issue in stamped) if stamped else None

        action, policy_blocked = self._derive_action(
            stage,
            stamped,
        )

        blocked = (
            has_critical or policy_blocked or (crashed and is_blocking_crash(self._fail_policy))
        )

        if blocked and action != GuardrailAction.ESCALATE:
            action = GuardrailAction.BLOCK

        return GuardrailResult(
            stage=stage,
            passed=passed,
            blocked=blocked,
            score=score,
            action=action,
            issues=stamped,
        )

    def _derive_action(
        self,
        stage: GuardrailStage,
        issues: list[GuardrailIssue],
    ) -> tuple[GuardrailAction, bool]:
        """
        Maps a stage's issues to a `GuardrailAction`, applying the
        configured regeneration/runtime policies (PRD §12). Returns the
        action plus whether policy alone decided to block (independent of
        `has_critical`/crash handling, which `_aggregate` layers on top).
        """

        if stage == GuardrailStage.GENERATION:
            faithfulness_error = any(
                issue.category == GuardrailCategory.FAITHFULNESS
                and issue.severity == GuardrailSeverity.ERROR
                for issue in issues
            )

            schema_error = any(
                issue.category == GuardrailCategory.SCHEMA
                and issue.severity == GuardrailSeverity.ERROR
                for issue in issues
            )

            if (faithfulness_error and self._regeneration_policy.regenerate_on_hallucination) or (
                schema_error and self._regeneration_policy.regenerate_on_schema_failure
            ):
                return GuardrailAction.REGENERATE, False

        if stage == GuardrailStage.RUNTIME:
            budget_or_loop_error = any(
                issue.category in (GuardrailCategory.BUDGET, GuardrailCategory.LOOP)
                and issue.severity in (GuardrailSeverity.ERROR, GuardrailSeverity.CRITICAL)
                for issue in issues
            )

            if budget_or_loop_error and self._runtime_policy.stop_on_budget_violation:
                return GuardrailAction.BLOCK, True

        if issues:
            return GuardrailAction.WARN, False

        return GuardrailAction.ALLOW, False
