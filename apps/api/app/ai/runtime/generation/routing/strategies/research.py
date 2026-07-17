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
# Research work needs deep reasoning over large amounts of retrieved
# context, so a minimum context window is required outright rather
# than only nudged for via the `context` weight.
#

RESEARCH_PROFILE = RoutingStrategyProfile(
    strategy=RoutingStrategy.REASONING,
    weights=ScoringWeights(
        reasoning=0.45,
        quality=0.25,
        reliability=0.20,
        context=0.10,
    ),
    min_context_window=100_000,
)
