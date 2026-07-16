from __future__ import annotations

from uuid import uuid4

from app.ai.guardrails.artifacts.builders import GuardrailArtifactBuilder
from app.ai.guardrails.enums import GuardrailAction, GuardrailStage
from app.ai.guardrails.models import GuardrailReport, GuardrailResult


def _report() -> GuardrailReport:
    def result(stage: GuardrailStage) -> GuardrailResult:
        return GuardrailResult(
            stage=stage, passed=True, blocked=False, action=GuardrailAction.ALLOW
        )

    return GuardrailReport(
        input_result=result(GuardrailStage.INPUT),
        retrieval_result=result(GuardrailStage.RETRIEVAL),
        generation_result=result(GuardrailStage.GENERATION),
        final_action=GuardrailAction.ALLOW,
        blocked=False,
    )


def test_build_wraps_run_id_and_report() -> None:
    run_id = uuid4()
    report = _report()

    artifact = GuardrailArtifactBuilder().build(run_id=run_id, report=report)

    assert artifact.run_id == run_id
    assert artifact.report is report
