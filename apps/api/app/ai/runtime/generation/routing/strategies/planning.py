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
# Planners need strong reasoning and a track record of producing
# coherent multi-step plans over raw output quality.
#

PLANNING_PROFILE = RoutingStrategyProfile(
    strategy=RoutingStrategy.PLANNING,
    weights=ScoringWeights(
        reasoning=0.40,
        planning=0.30,
        reliability=0.20,
        quality=0.10,
    ),
)
