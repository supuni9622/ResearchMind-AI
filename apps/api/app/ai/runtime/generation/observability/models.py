"""
Runtime Metrics Integration -- captures the standardized set of
Request/Execution/Token/Cost/Validation/Guardrail metrics a completed
`GenerationResult` carries (see `service.py::GenerationMetricsService`),
so every consumer -- the metrics recorder, the `metrics.json` artifact,
future dashboards -- reads the same shape instead of each re-deriving
it from `GenerationResult` independently.
"""

from __future__ import annotations

from uuid import UUID

from app.ai.runtime.generation.enums import (
    GenerationProvider,
)
from app.ai.runtime.generation.models import (
    GenerationResult,
)
from pydantic import (
    BaseModel,
    ConfigDict,
)


class GenerationMetricsSnapshot(
    BaseModel,
):
    model_config = ConfigDict(
        extra="forbid",
    )

    #
    # Request
    #

    request_id: UUID

    generation_id: UUID

    runtime: str | None = None

    provider: GenerationProvider

    model: str

    #
    # Execution
    #

    latency_ms: float

    retries: int

    regeneration_count: int

    cache_hit: bool

    #
    # Token
    #

    prompt_tokens: int

    completion_tokens: int

    total_tokens: int

    #
    # Cost
    #

    estimated_cost_usd: float

    cumulative_session_cost_usd: float | None = None
    """
    Populated by `GenerationMetricsService` when a caller tracks
    per-session spend across multiple `record()` calls (see its
    `session_cost_usd` param) -- `None` when the caller doesn't (the
    common case today: nothing in this codebase groups generations
    into a billing session yet).
    """

    #
    # Validation
    #

    validation_score: float | None = None

    hallucination_score: float | None = None

    runtime_score: float | None = None

    #
    # Guardrail
    #

    guardrail_risk_score: float | None = None

    guardrail_blocked: bool


def build_generation_metrics_snapshot(
    result: GenerationResult,
    *,
    cumulative_session_cost_usd: float | None = None,
) -> GenerationMetricsSnapshot:
    """
    Pure derivation of a `GenerationMetricsSnapshot` from a completed
    `GenerationResult` -- no side effects, no recording. Shared by
    `GenerationMetricsService.record()` and `GenerationArtifactBuilder`
    (`artifacts/generation/builders.py`) so both produce byte-identical
    metrics for the same result instead of two independent readings of
    `GenerationResult` drifting apart over time.
    """

    validation = result.validation

    guardrails = result.guardrails

    return GenerationMetricsSnapshot(
        request_id=result.request.request_id,
        generation_id=result.generation_id,
        runtime=(result.request.runtime.value if result.request.runtime else None),
        provider=result.provider,
        model=result.model,
        latency_ms=result.statistics.latency_ms,
        retries=result.statistics.retries,
        regeneration_count=result.regeneration_attempts,
        cache_hit=result.statistics.cache_hit,
        prompt_tokens=result.statistics.prompt_tokens,
        completion_tokens=result.statistics.completion_tokens,
        total_tokens=result.statistics.total_tokens,
        estimated_cost_usd=result.statistics.estimated_cost_usd,
        cumulative_session_cost_usd=cumulative_session_cost_usd,
        validation_score=(validation.output_validation.score if validation else None),
        hallucination_score=(validation.hallucination_validation.score if validation else None),
        runtime_score=(
            validation.runtime_validation.score
            if validation and validation.runtime_validation
            else None
        ),
        guardrail_risk_score=(guardrails.overall_risk if guardrails else None),
        guardrail_blocked=(guardrails.blocked if guardrails else False),
    )
