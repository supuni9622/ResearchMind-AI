from __future__ import annotations

from app.ai.guardrails.enums import GuardrailAction, GuardrailStage
from app.ai.guardrails.models import GuardrailReport, GuardrailResult
from app.ai.guardrails.reports.guardrail_report import stage_summaries, summarize_report

from tests.unit.ai.guardrails.factories import make_guardrail_issue


def _result(
    stage: GuardrailStage,
    *,
    action: GuardrailAction = GuardrailAction.ALLOW,
    blocked: bool = False,
    issues: list | None = None,
) -> GuardrailResult:
    return GuardrailResult(
        stage=stage,
        passed=not blocked,
        blocked=blocked,
        action=action,
        issues=issues or [],
    )


def test_summarize_allowed_report() -> None:
    report = GuardrailReport(
        input_result=_result(GuardrailStage.INPUT),
        retrieval_result=_result(GuardrailStage.RETRIEVAL),
        generation_result=_result(GuardrailStage.GENERATION),
        final_action=GuardrailAction.ALLOW,
        blocked=False,
    )

    summary = summarize_report(report)

    assert summary.startswith("ALLOWED")
    assert "3 stage" in summary


def test_summarize_blocked_report_names_the_blocking_stage() -> None:
    report = GuardrailReport(
        input_result=_result(GuardrailStage.INPUT),
        retrieval_result=_result(GuardrailStage.RETRIEVAL),
        generation_result=_result(
            GuardrailStage.GENERATION,
            action=GuardrailAction.BLOCK,
            blocked=True,
            issues=[make_guardrail_issue()],
        ),
        final_action=GuardrailAction.BLOCK,
        blocked=True,
    )

    summary = summarize_report(report)

    assert summary.startswith("BLOCKED")
    assert "generation" in summary


def test_stage_summaries_covers_every_stage_that_ran() -> None:
    report = GuardrailReport(
        input_result=_result(GuardrailStage.INPUT),
        retrieval_result=_result(GuardrailStage.RETRIEVAL),
        generation_result=_result(GuardrailStage.GENERATION),
        runtime_result=_result(GuardrailStage.RUNTIME),
        final_action=GuardrailAction.ALLOW,
        blocked=False,
    )

    summaries = stage_summaries(report)

    assert set(summaries.keys()) == {"input", "retrieval", "generation", "runtime"}


def test_stage_summaries_omits_runtime_when_not_run() -> None:
    report = GuardrailReport(
        input_result=_result(GuardrailStage.INPUT),
        retrieval_result=_result(GuardrailStage.RETRIEVAL),
        generation_result=_result(GuardrailStage.GENERATION),
        final_action=GuardrailAction.ALLOW,
        blocked=False,
    )

    assert "runtime" not in stage_summaries(report)
