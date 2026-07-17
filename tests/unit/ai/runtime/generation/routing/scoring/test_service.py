"""
Unit tests for ScoringService.

Covers:
- Weighted blending of direct 0-1 score dimensions
- Cost normalization is relative to the candidate set (cheapest -> 1.0)
- Context-window normalization is relative to the candidate set
- structured_output is scored as a 0/1 capability flag
- Results are sorted best-first
- Reasons surface the top contributing dimensions
- A single-candidate set normalizes cost/context to 1.0 (no spread)
- An empty candidate set returns an empty list
"""

from __future__ import annotations

from app.ai.runtime.generation.catalog.models import (
    ModelMetadata,
)
from app.ai.runtime.generation.config import (
    ProviderCapabilities,
)
from app.ai.runtime.generation.enums import (
    GenerationProvider,
)
from app.ai.runtime.generation.routing.scoring.service import (
    ScoringService,
)
from app.ai.runtime.generation.routing.scoring.weights import (
    ScoringWeights,
)


def _make_model(
    model_name: str,
    *,
    quality_score: float = 0.5,
    speed_score: float = 0.5,
    reliability_score: float = 0.5,
    cost_per_input_1m: float = 1.0,
    cost_per_output_1m: float = 1.0,
    context_window: int = 100_000,
    structured_output: bool = False,
) -> ModelMetadata:
    return ModelMetadata(
        provider=GenerationProvider.OPENAI,
        model_name=model_name,
        display_name=model_name,
        context_window=context_window,
        capabilities=ProviderCapabilities(structured_output=structured_output),
        cost_per_input_1m=cost_per_input_1m,
        cost_per_output_1m=cost_per_output_1m,
        quality_score=quality_score,
        speed_score=speed_score,
        reliability_score=reliability_score,
    )


def test_score_candidates_returns_empty_list_for_no_models() -> None:
    service = ScoringService()

    assert service.score_candidates(models=[], weights=ScoringWeights(quality=1.0)) == []


def test_score_candidates_sorts_best_first() -> None:
    weak = _make_model("weak", quality_score=0.2)
    strong = _make_model("strong", quality_score=0.9)

    service = ScoringService()

    scored = service.score_candidates(models=[weak, strong], weights=ScoringWeights(quality=1.0))

    assert [entry.model.model_name for entry in scored] == ["strong", "weak"]
    assert scored[0].score > scored[1].score


def test_direct_dimension_uses_the_raw_0_to_1_field_scaled_to_ten() -> None:
    model = _make_model("solo", quality_score=0.8)

    service = ScoringService()

    scored = service.score_candidates(models=[model], weights=ScoringWeights(quality=1.0))

    assert scored[0].score == 8.0


def test_cost_normalization_ranks_the_cheapest_candidate_highest() -> None:
    cheap = _make_model("cheap", cost_per_input_1m=0.1, cost_per_output_1m=0.1)
    expensive = _make_model("expensive", cost_per_input_1m=10.0, cost_per_output_1m=10.0)

    service = ScoringService()

    scored = service.score_candidates(
        models=[expensive, cheap],
        weights=ScoringWeights(cost=1.0),
    )

    assert scored[0].model.model_name == "cheap"
    assert scored[0].score == 10.0
    assert scored[1].score == 0.0


def test_context_normalization_ranks_the_largest_window_highest() -> None:
    small = _make_model("small", context_window=50_000)
    large = _make_model("large", context_window=1_000_000)

    service = ScoringService()

    scored = service.score_candidates(
        models=[small, large],
        weights=ScoringWeights(context=1.0),
    )

    assert scored[0].model.model_name == "large"
    assert scored[0].score == 10.0
    assert scored[1].score == 0.0


def test_structured_output_weight_is_scored_as_a_boolean_flag() -> None:
    supports = _make_model("supports", structured_output=True)
    lacks = _make_model("lacks", structured_output=False)

    service = ScoringService()

    scored = service.score_candidates(
        models=[lacks, supports],
        weights=ScoringWeights(structured_output=1.0),
    )

    assert scored[0].model.model_name == "supports"
    assert scored[0].score == 10.0
    assert scored[1].score == 0.0


def test_single_candidate_normalizes_cost_and_context_to_the_maximum() -> None:
    model = _make_model(
        "solo", cost_per_input_1m=5.0, cost_per_output_1m=5.0, context_window=200_000
    )

    service = ScoringService()

    scored = service.score_candidates(
        models=[model],
        weights=ScoringWeights(cost=0.5, context=0.5),
    )

    assert scored[0].score == 10.0


def test_reasons_surface_the_top_weighted_contributing_dimensions() -> None:
    model = _make_model("winner", quality_score=0.9, speed_score=0.9, reliability_score=0.1)

    service = ScoringService()

    scored = service.score_candidates(
        models=[model],
        weights=ScoringWeights(quality=0.5, speed=0.5, reliability=0.1),
    )

    assert "highest quality score" in scored[0].reasons
    assert "fastest response time" in scored[0].reasons


def test_reasons_flag_the_widest_context_window_above_the_long_context_threshold() -> None:
    small = _make_model("small", context_window=100_000)
    huge = _make_model("huge", context_window=1_000_000)

    service = ScoringService()

    scored = service.score_candidates(
        models=[small, huge],
        weights=ScoringWeights(quality=1.0),
    )

    winner = next(entry for entry in scored if entry.model.model_name == "huge")

    assert "supports long context" in winner.reasons


def test_zero_weighted_dimensions_do_not_influence_the_score() -> None:
    model = _make_model("model", quality_score=0.1, speed_score=0.9)

    service = ScoringService()

    scored = service.score_candidates(
        models=[model],
        weights=ScoringWeights(quality=1.0, speed=0.0),
    )

    assert scored[0].score == 1.0
