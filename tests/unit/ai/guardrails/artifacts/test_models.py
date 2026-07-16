from __future__ import annotations

from uuid import uuid4

from app.ai.guardrails.artifacts.models import GuardrailArtifact
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


def test_artifact_defaults_version_and_generates_ids() -> None:
    artifact = GuardrailArtifact(run_id=uuid4(), report=_report())

    assert artifact.version == "1.0"
    assert artifact.artifact_id is not None
    assert artifact.generated_at is not None
