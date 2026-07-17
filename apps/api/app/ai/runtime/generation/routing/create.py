"""
Routing Platform composition root.

Assembles the catalog registry, scoring engine, and every strategy
profile into a ready-to-use `RoutingService`.
"""

from __future__ import annotations

from functools import lru_cache

import structlog
from app.ai.runtime.generation.catalog.registry import (
    get_model_catalog_registry,
)
from app.ai.runtime.generation.routing.enums import (
    RoutingStrategy,
)
from app.ai.runtime.generation.routing.models import (
    RoutingStrategyProfile,
)
from app.ai.runtime.generation.routing.scoring.service import (
    ScoringService,
)
from app.ai.runtime.generation.routing.scoring.weights import (
    DEFAULT_STRATEGY_WEIGHTS,
)
from app.ai.runtime.generation.routing.service import (
    RoutingService,
)
from app.ai.runtime.generation.routing.strategies.coding import (
    CODING_PROFILE,
)
from app.ai.runtime.generation.routing.strategies.planning import (
    PLANNING_PROFILE,
)
from app.ai.runtime.generation.routing.strategies.research import (
    RESEARCH_PROFILE,
)
from app.ai.runtime.generation.routing.strategies.review import (
    REVIEW_PROFILE,
)
from app.ai.runtime.generation.routing.strategies.summarization import (
    SUMMARIZATION_PROFILE,
)
from app.ai.runtime.generation.routing.strategies.validation import (
    VALIDATION_PROFILE,
)

logger = structlog.get_logger()

#
# The six task strategies carry dedicated capability/context
# requirements defined alongside their weights. Every other
# `RoutingStrategy` value only needs a weight profile, sourced from
# `DEFAULT_STRATEGY_WEIGHTS`.
#

_TASK_PROFILES: list[RoutingStrategyProfile] = [
    PLANNING_PROFILE,
    SUMMARIZATION_PROFILE,
    REVIEW_PROFILE,
    VALIDATION_PROFILE,
    CODING_PROFILE,
    RESEARCH_PROFILE,
]


def build_strategy_profiles() -> dict[RoutingStrategy, RoutingStrategyProfile]:

    profiles: dict[RoutingStrategy, RoutingStrategyProfile] = {
        profile.strategy: profile for profile in _TASK_PROFILES
    }

    for strategy, weights in DEFAULT_STRATEGY_WEIGHTS.items():
        profiles[strategy] = RoutingStrategyProfile(
            strategy=strategy,
            weights=weights,
            require_local=(strategy == RoutingStrategy.LOCAL),
        )

    return profiles


@lru_cache
def create_routing_service() -> RoutingService:

    strategy_profiles = build_strategy_profiles()

    service = RoutingService(
        catalog=get_model_catalog_registry(),
        scoring_engine=ScoringService(),
        strategy_profiles=strategy_profiles,
    )

    logger.info(
        "routing.service.initialized",
        strategies=sorted(strategy.value for strategy in strategy_profiles),
    )

    return service
