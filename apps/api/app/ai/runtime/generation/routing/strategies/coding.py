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
# Coding tasks weight coding skill above everything else, with
# reasoning as a secondary signal for multi-step or debugging work.
#

CODING_PROFILE = RoutingStrategyProfile(
    strategy=RoutingStrategy.CODING,
    weights=ScoringWeights(
        coding=0.50,
        reasoning=0.20,
        quality=0.20,
        reliability=0.10,
    ),
)
