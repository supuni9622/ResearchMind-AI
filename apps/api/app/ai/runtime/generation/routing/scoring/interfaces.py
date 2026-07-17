from __future__ import annotations

from abc import ABC, abstractmethod

from app.ai.runtime.generation.catalog.models import (
    ModelMetadata,
)
from app.ai.runtime.generation.routing.scoring.weights import (
    ScoringWeights,
)
from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
)


class ScoredModel(
    BaseModel,
):
    model_config = ConfigDict(
        extra="forbid",
        frozen=True,
    )

    model: ModelMetadata

    score: float
    """
    Weighted score on a 0-10 scale, so it reads naturally in logs and
    routing decisions (e.g. 9.3) rather than a raw 0-1 fraction.
    """

    reasons: list[str] = Field(
        default_factory=list,
    )
    """
    Human-readable explanation of why this model scored the way it
    did — the dimensions that contributed most, in descending order.
    """


class ScoringEngineInterface(
    ABC,
):
    """
    Blends a candidate model's catalog scores into a single ranking
    number for a given strategy's weights.
    """

    @abstractmethod
    def score_candidates(
        self,
        *,
        models: list[ModelMetadata],
        weights: ScoringWeights,
    ) -> list[ScoredModel]:
        """
        Scores every model in `models` against `weights` and returns
        them sorted best-first. Cost and context-window dimensions are
        normalized relative to this candidate set, so the result of
        scoring the same model can differ between calls with a
        different candidate set.
        """

        pass
