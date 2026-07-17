from __future__ import annotations

from app.ai.runtime.generation.catalog.models import (
    ModelMetadata,
)
from app.ai.runtime.generation.routing.scoring.interfaces import (
    ScoredModel,
    ScoringEngineInterface,
)
from app.ai.runtime.generation.routing.scoring.weights import (
    ScoringWeights,
)

#
# Dimension name -> human-readable reason, shown for a model's
# highest-weighted contributing dimensions in `RoutingDecision.reasons`.
#

_DIMENSION_REASONS: dict[str, str] = {
    "quality": "highest quality score",
    "reasoning": "highest reasoning score",
    "planning": "highest planning score",
    "review": "highest review score",
    "coding": "highest coding score",
    "summarization": "highest summarization score",
    "classification": "highest classification score",
    "extraction": "highest extraction score",
    "speed": "fastest response time",
    "reliability": "highest reliability score",
    "cost": "lowest cost",
    "context": "largest context window",
    "structured_output": "supports structured output",
}

#
# Dimensions scored directly off a 0-1 ModelMetadata field. `cost`,
# `context`, and `structured_output` aren't listed here — they're
# derived relative to the candidate set (see `_normalized_dimensions`).
#

_DIRECT_DIMENSIONS: dict[str, str] = {
    "quality": "quality_score",
    "reasoning": "reasoning_score",
    "planning": "planning_score",
    "review": "review_score",
    "coding": "coding_score",
    "summarization": "summarization_score",
    "classification": "classification_score",
    "extraction": "extraction_score",
    "speed": "speed_score",
    "reliability": "reliability_score",
}

#
# Assumed input:output token ratio used to blend the two per-1M costs
# into a single comparable number — completions typically dominate
# spend, so output cost is weighted more heavily.
#

_INPUT_COST_WEIGHT = 0.25

_OUTPUT_COST_WEIGHT = 0.75

_LONG_CONTEXT_THRESHOLD = 500_000


class ScoringService(
    ScoringEngineInterface,
):
    def score_candidates(
        self,
        *,
        models: list[ModelMetadata],
        weights: ScoringWeights,
    ) -> list[ScoredModel]:

        if not models:
            return []

        cost_scores, context_scores = self._normalized_dimensions(
            models,
        )

        max_context_window = max(model.context_window for model in models)

        scored = [
            self._score_one(
                model=model,
                weights=weights,
                cost_score=cost_scores[model.model_name],
                context_score=context_scores[model.model_name],
                max_context_window=max_context_window,
            )
            for model in models
        ]

        return sorted(
            scored,
            key=lambda scored_model: scored_model.score,
            reverse=True,
        )

    # ==========================================================
    # Internals
    # ==========================================================

    @classmethod
    def _score_one(
        cls,
        *,
        model: ModelMetadata,
        weights: ScoringWeights,
        cost_score: float,
        context_score: float,
        max_context_window: int,
    ) -> ScoredModel:

        dimension_values: dict[str, float] = {
            name: getattr(model, field) for name, field in _DIRECT_DIMENSIONS.items()
        }

        dimension_values["cost"] = cost_score

        dimension_values["context"] = context_score

        dimension_values["structured_output"] = 1.0 if model.capabilities.structured_output else 0.0

        contributions: dict[str, float] = {}

        total_weight = 0.0

        weighted_sum = 0.0

        for dimension, value in dimension_values.items():
            weight = getattr(weights, dimension)

            if weight <= 0:
                continue

            contributions[dimension] = weight * value

            weighted_sum += weight * value

            total_weight += weight

        normalized_score = (
            (weighted_sum / total_weight) if total_weight > 0 else model.quality_score
        )

        reasons = cls._build_reasons(
            contributions=contributions,
            model=model,
            max_context_window=max_context_window,
        )

        return ScoredModel(
            model=model,
            score=round(normalized_score * 10, 2),
            reasons=reasons,
        )

    @staticmethod
    def _build_reasons(
        *,
        contributions: dict[str, float],
        model: ModelMetadata,
        max_context_window: int,
    ) -> list[str]:

        top_dimensions = sorted(
            contributions.items(),
            key=lambda item: item[1],
            reverse=True,
        )[:3]

        reasons = [
            _DIMENSION_REASONS[dimension]
            for dimension, contribution in top_dimensions
            if contribution > 0
        ]

        if (
            model.context_window == max_context_window
            and model.context_window >= _LONG_CONTEXT_THRESHOLD
            and _DIMENSION_REASONS["context"] not in reasons
        ):
            reasons.append(
                "supports long context",
            )

        return reasons

    @staticmethod
    def _normalized_dimensions(
        models: list[ModelMetadata],
    ) -> tuple[dict[str, float], dict[str, float]]:
        """
        Min-max normalizes blended cost (inverted — cheaper is higher)
        and context window across `models`, so `cost`/`context` weights
        compare candidates against each other rather than against an
        arbitrary fixed scale.
        """

        blended_costs = {
            model.model_name: (
                _INPUT_COST_WEIGHT * model.cost_per_input_1m
                + _OUTPUT_COST_WEIGHT * model.cost_per_output_1m
            )
            for model in models
        }

        min_cost = min(blended_costs.values())

        max_cost = max(blended_costs.values())

        cost_spread = max_cost - min_cost

        cost_scores = {
            model_name: (1.0 if cost_spread == 0 else (max_cost - cost) / cost_spread)
            for model_name, cost in blended_costs.items()
        }

        context_windows = {model.model_name: model.context_window for model in models}

        min_context = min(context_windows.values())

        max_context = max(context_windows.values())

        context_spread = max_context - min_context

        context_scores = {
            model_name: (1.0 if context_spread == 0 else (window - min_context) / context_spread)
            for model_name, window in context_windows.items()
        }

        return cost_scores, context_scores
