"""
Unit tests for guardrails/models.py.

Covers:
- extra="forbid" on GuardrailIssue/GuardrailResult/GuardrailReport
- GuardrailReport.issues flattens every stage's issues, in stage order
- GuardrailReport.issues skips a None runtime_result
"""

from __future__ import annotations

import pytest
from app.ai.guardrails.enums import GuardrailAction, GuardrailStage
from app.ai.guardrails.models import GuardrailIssue, GuardrailReport, GuardrailResult
from pydantic import ValidationError

from tests.unit.ai.guardrails.factories import make_guardrail_issue


def _result(stage: GuardrailStage, *, issues: list | None = None) -> GuardrailResult:
    return GuardrailResult(
        stage=stage,
        passed=True,
        blocked=False,
        action=GuardrailAction.ALLOW,
        issues=issues or [],
    )


def test_guardrail_issue_rejects_unknown_fields() -> None:
    with pytest.raises(ValidationError):
        GuardrailIssue(
            code="x",
            severity="warning",
            category="pii",
            message="x",
            unexpected="x",  # type: ignore[call-arg]
        )


def test_guardrail_report_issues_flattens_all_stages_in_order() -> None:
    input_issue = make_guardrail_issue(code="input_issue", stage=GuardrailStage.INPUT)
    retrieval_issue = make_guardrail_issue(code="retrieval_issue", stage=GuardrailStage.RETRIEVAL)
    generation_issue = make_guardrail_issue(
        code="generation_issue", stage=GuardrailStage.GENERATION
    )
    runtime_issue = make_guardrail_issue(code="runtime_issue", stage=GuardrailStage.RUNTIME)

    report = GuardrailReport(
        input_result=_result(GuardrailStage.INPUT, issues=[input_issue]),
        retrieval_result=_result(GuardrailStage.RETRIEVAL, issues=[retrieval_issue]),
        generation_result=_result(GuardrailStage.GENERATION, issues=[generation_issue]),
        runtime_result=_result(GuardrailStage.RUNTIME, issues=[runtime_issue]),
        final_action=GuardrailAction.ALLOW,
        blocked=False,
    )

    assert [issue.code for issue in report.issues] == [
        "input_issue",
        "retrieval_issue",
        "generation_issue",
        "runtime_issue",
    ]


def test_guardrail_report_issues_skips_none_runtime_result() -> None:
    report = GuardrailReport(
        input_result=_result(GuardrailStage.INPUT),
        retrieval_result=_result(GuardrailStage.RETRIEVAL),
        generation_result=_result(GuardrailStage.GENERATION),
        runtime_result=None,
        final_action=GuardrailAction.ALLOW,
        blocked=False,
    )

    assert report.issues == []
