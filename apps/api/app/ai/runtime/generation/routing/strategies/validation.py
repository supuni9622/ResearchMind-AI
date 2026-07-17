from __future__ import annotations

from app.ai.runtime.generation.routing.enums import (
    RequiredCapability,
    RoutingStrategy,
)
from app.ai.runtime.generation.routing.models import (
    RoutingStrategyProfile,
)
from app.ai.runtime.generation.routing.scoring.weights import (
    ScoringWeights,
)

#
# Validation checks are cheap, structured, high-volume calls — the
# reasoning depth a planner needs would be wasted spend here.
# Structured output support is required outright rather than merely
# weighted, since a validator that can't return structured judgments
# isn't usable for this strategy at all.
#

VALIDATION_PROFILE = RoutingStrategyProfile(
    strategy=RoutingStrategy.VALIDATION,
    weights=ScoringWeights(
        speed=0.35,
        cost=0.35,
        structured_output=0.20,
        reliability=0.10,
    ),
    required_capabilities=[
        RequiredCapability.STRUCTURED_OUTPUT,
    ],
)
