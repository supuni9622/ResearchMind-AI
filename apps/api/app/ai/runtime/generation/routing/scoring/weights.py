from __future__ import annotations

from app.ai.runtime.generation.routing.enums import (
    RoutingStrategy,
)
from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
)


class ScoringWeights(
    BaseModel,
):
    """
    Per-dimension weights the scoring engine blends into a single
    score for a candidate model. Dimensions left at 0 don't influence
    the result. Weights don't need to sum to 1 — the engine normalizes
    by the total weight actually used.
    """

    model_config = ConfigDict(
        extra="forbid",
        frozen=True,
    )

    quality: float = Field(default=0.0, ge=0)

    reasoning: float = Field(default=0.0, ge=0)

    planning: float = Field(default=0.0, ge=0)

    review: float = Field(default=0.0, ge=0)

    coding: float = Field(default=0.0, ge=0)

    summarization: float = Field(default=0.0, ge=0)

    classification: float = Field(default=0.0, ge=0)

    extraction: float = Field(default=0.0, ge=0)

    speed: float = Field(default=0.0, ge=0)

    reliability: float = Field(default=0.0, ge=0)

    cost: float = Field(default=0.0, ge=0)
    """
    Weight on being cheap. Scored from `cost_per_input_1m`/
    `cost_per_output_1m`, normalized across the candidate set so the
    cheapest of the group scores 1.0 — see `scoring/service.py`.
    """

    context: float = Field(default=0.0, ge=0)
    """
    Weight on having a large context window, normalized across the
    candidate set the same way `cost` is.
    """

    structured_output: float = Field(default=0.0, ge=0)
    """
    Weight on `ProviderCapabilities.structured_output` — scored as 1.0
    or 0.0 rather than a continuous value.
    """


#
# Task-based strategies with a canonical weight profile live in
# `routing/strategies/` alongside their capability/context requirements.
# These are the remaining, more generic strategies that need weights
# but no extra filtering.
#

DEFAULT_STRATEGY_WEIGHTS: dict[RoutingStrategy, ScoringWeights] = {
    RoutingStrategy.AUTO: ScoringWeights(
        quality=0.30,
        reliability=0.25,
        reasoning=0.20,
        speed=0.15,
        cost=0.10,
    ),
    RoutingStrategy.FAST: ScoringWeights(
        speed=0.60,
        reliability=0.20,
        cost=0.10,
        quality=0.10,
    ),
    RoutingStrategy.CHEAP: ScoringWeights(
        cost=0.60,
        reliability=0.20,
        speed=0.10,
        quality=0.10,
    ),
    RoutingStrategy.QUALITY: ScoringWeights(
        quality=0.50,
        reliability=0.25,
        reasoning=0.15,
        review=0.10,
    ),
    RoutingStrategy.LONG_CONTEXT: ScoringWeights(
        context=0.45,
        quality=0.25,
        reliability=0.20,
        reasoning=0.10,
    ),
    RoutingStrategy.STRUCTURED_OUTPUT: ScoringWeights(
        structured_output=0.45,
        reliability=0.30,
        quality=0.15,
        speed=0.10,
    ),
    RoutingStrategy.CLASSIFICATION: ScoringWeights(
        classification=0.50,
        speed=0.25,
        cost=0.15,
        reliability=0.10,
    ),
    RoutingStrategy.EXTRACTION: ScoringWeights(
        extraction=0.50,
        reliability=0.25,
        quality=0.15,
        speed=0.10,
    ),
    RoutingStrategy.LOCAL: ScoringWeights(
        reliability=0.40,
        cost=0.30,
        quality=0.20,
        speed=0.10,
    ),
}
