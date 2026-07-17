"""
Unit tests for build_generation_metrics_snapshot.

Covers:
- Core request/execution/token/cost fields are read straight off the result
- runtime is None when GenerationRequest.runtime is unset, else its value
- validation/hallucination/runtime scores are read from ValidationReport
  when present, else None
- guardrail risk score/blocked are read from GuardrailReport when present,
  else risk score None and blocked False
- cumulative_session_cost_usd passes through the optional param
"""

from __future__ import annotations

from app.ai.guardrails.enums import GuardrailAction, GuardrailStage
from app.ai.guardrails.models import GuardrailReport, GuardrailResult
from app.ai.runtime.generation.enums import GenerationProvider
from app.ai.runtime.generation.observability.models import build_generation_metrics_snapshot
from app.ai.runtime.generation.validation.models import ValidationReport, ValidationResult
from app.ai.runtime.generation.validation.runtime.enums import RuntimeType

from tests.unit.ai.runtime.generation.validation.factories import make_request, make_result


def _guardrail_report(*, overall_risk: float | None, blocked: bool) -> GuardrailReport:
    stage_result = GuardrailResult(
        stage=GuardrailStage.INPUT,
        passed=not blocked,
        blocked=blocked,
        action=GuardrailAction.BLOCK if blocked else GuardrailAction.ALLOW,
    )

    return GuardrailReport(
        input_result=stage_result,
        retrieval_result=stage_result,
        generation_result=stage_result,
        overall_risk=overall_risk,
        final_action=stage_result.action,
        blocked=blocked,
    )


async def test_core_fields_are_read_from_the_result() -> None:
    result = make_result()

    snapshot = build_generation_metrics_snapshot(result)

    assert snapshot.request_id == result.request.request_id
    assert snapshot.generation_id == result.generation_id
    assert snapshot.provider == GenerationProvider.GROQ
    assert snapshot.model == "test-model"
    assert snapshot.retries == result.statistics.retries
    assert snapshot.prompt_tokens == result.statistics.prompt_tokens
    assert snapshot.total_tokens == result.statistics.total_tokens
    assert snapshot.estimated_cost_usd == result.statistics.estimated_cost_usd


async def test_runtime_is_none_when_request_runtime_unset() -> None:
    result = make_result(request=make_request(runtime=None))

    snapshot = build_generation_metrics_snapshot(result)

    assert snapshot.runtime is None


async def test_runtime_reflects_the_request_runtime_value() -> None:
    result = make_result(request=make_request(runtime=RuntimeType.RESEARCH))

    snapshot = build_generation_metrics_snapshot(result)

    assert snapshot.runtime == "research"


async def test_validation_scores_default_to_none_without_a_report() -> None:
    result = make_result()

    snapshot = build_generation_metrics_snapshot(result)

    assert snapshot.validation_score is None
    assert snapshot.hallucination_score is None
    assert snapshot.runtime_score is None


async def test_validation_scores_are_read_from_the_report() -> None:
    result = make_result()

    result.validation = ValidationReport(
        input_validation=ValidationResult(valid=True),
        output_validation=ValidationResult(valid=True, score=0.9),
        hallucination_validation=ValidationResult(valid=True, score=0.8),
        runtime_validation=ValidationResult(valid=True, score=0.7),
        valid=True,
    )

    snapshot = build_generation_metrics_snapshot(result)

    assert snapshot.validation_score == 0.9
    assert snapshot.hallucination_score == 0.8
    assert snapshot.runtime_score == 0.7


async def test_guardrail_fields_default_without_a_report() -> None:
    result = make_result()

    snapshot = build_generation_metrics_snapshot(result)

    assert snapshot.guardrail_risk_score is None
    assert snapshot.guardrail_blocked is False


async def test_guardrail_fields_are_read_from_the_report() -> None:
    result = make_result()

    result.guardrails = _guardrail_report(overall_risk=0.4, blocked=True)

    snapshot = build_generation_metrics_snapshot(result)

    assert snapshot.guardrail_risk_score == 0.4
    assert snapshot.guardrail_blocked is True


async def test_cumulative_session_cost_passes_through() -> None:
    result = make_result()

    snapshot = build_generation_metrics_snapshot(result, cumulative_session_cost_usd=12.5)

    assert snapshot.cumulative_session_cost_usd == 12.5
