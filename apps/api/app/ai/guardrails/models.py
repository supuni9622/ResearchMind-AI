from __future__ import annotations

from typing import Any

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
)

from app.ai.guardrails.enums import (
    GuardrailAction,
    GuardrailCategory,
    GuardrailSeverity,
    GuardrailStage,
)


class GuardrailIssue(
    BaseModel,
):
    model_config = ConfigDict(
        extra="forbid",
    )

    code: str

    severity: GuardrailSeverity

    category: GuardrailCategory

    stage: GuardrailStage = GuardrailStage.INPUT
    """
    Which guardrail stage produced this issue. Individual guardrails do
    not need to set this themselves — `GuardrailService` stamps the
    correct stage when it aggregates each stage's issues (mirrors
    `ValidationIssue.stage`); the default here only matters for issues
    constructed outside that path (e.g. directly in tests).
    """

    message: str

    metadata: dict[str, Any] = Field(
        default_factory=dict,
    )


class GuardrailResult(
    BaseModel,
):
    model_config = ConfigDict(
        extra="forbid",
    )

    stage: GuardrailStage

    passed: bool

    blocked: bool

    score: float | None = None
    """
    Risk score for this stage in `[0, 1]` — the highest
    `SEVERITY_RISK_SCORES` value among this stage's issues, or `None`
    when the stage produced no issues at all.
    """

    action: GuardrailAction

    issues: list[GuardrailIssue] = Field(
        default_factory=list,
    )


class GuardrailReport(
    BaseModel,
):
    """
    Aggregated, multi-stage guardrail outcome for a single run (PRD §7).
    """

    model_config = ConfigDict(
        extra="forbid",
    )

    input_result: GuardrailResult

    retrieval_result: GuardrailResult

    generation_result: GuardrailResult

    runtime_result: GuardrailResult | None = None
    """
    `None` when the run has no runtime/execution state to evaluate yet
    (e.g. a single-shot generation with no agent loop) — mirrors
    `ValidationReport.runtime_validation`'s optionality.
    """

    overall_risk: float | None = None

    final_action: GuardrailAction

    blocked: bool
    """`True` when any stage that ran was itself blocked."""

    @property
    def issues(
        self,
    ) -> list[GuardrailIssue]:
        """
        Every issue across every stage that ran, in stage order
        (input, retrieval, generation, runtime).
        """

        all_issues = [
            *self.input_result.issues,
            *self.retrieval_result.issues,
            *self.generation_result.issues,
        ]

        if self.runtime_result is not None:
            all_issues.extend(
                self.runtime_result.issues,
            )

        return all_issues
