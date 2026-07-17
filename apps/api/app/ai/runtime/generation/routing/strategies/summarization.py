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
# Summarization runs at high volume, so speed and cost matter almost
# as much as summarization quality itself.
#

SUMMARIZATION_PROFILE = RoutingStrategyProfile(
    strategy=RoutingStrategy.SUMMARIZATION,
    weights=ScoringWeights(
        summarization=0.40,
        speed=0.30,
        cost=0.20,
        quality=0.10,
    ),
)
