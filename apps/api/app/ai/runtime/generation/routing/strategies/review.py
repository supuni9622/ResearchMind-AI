from __future__ import annotations

from app.ai.runtime.generation.routing.enums import (
    RoutingStrategy,
)
from app.ai.runtime.generation.routing.models import (
    RoutingStrategyProfile,
)
from app.ai.runtime.generation.routing.scoring.weights import (
    ScoringWeights,
)

#
# Reviewers critique someone else's output, so review skill and
# reasoning matter more than raw generation speed or cost.
#

REVIEW_PROFILE = RoutingStrategyProfile(
    strategy=RoutingStrategy.REVIEW,
    weights=ScoringWeights(
        review=0.40,
        reasoning=0.30,
        quality=0.20,
        reliability=0.10,
    ),
)
