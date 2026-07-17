from __future__ import annotations

from time import perf_counter

import structlog
from app.ai.runtime.generation.catalog.models import (
    ModelMetadata,
)
from app.ai.runtime.generation.catalog.registry import (
    ModelCatalogRegistry,
)
from app.ai.runtime.generation.routing.enums import (
    RequiredCapability,
    RoutingStrategy,
)
from app.ai.runtime.generation.routing.exceptions import (
    NoEligibleModelsError,
)
from app.ai.runtime.generation.routing.interfaces import (
    RoutingServiceInterface,
)
from app.ai.runtime.generation.routing.models import (
    RoutingDecision,
    RoutingRequest,
    RoutingStrategyProfile,
)
from app.ai.runtime.generation.routing.scoring.interfaces import (
    ScoredModel,
    ScoringEngineInterface,
)

logger = structlog.get_logger()

#
# Maps a caller-facing capability requirement onto the boolean field
# it corresponds to on `ProviderCapabilities`.
#

_CAPABILITY_FIELDS: dict[RequiredCapability, str] = {
    RequiredCapability.STREAMING: "streaming",
    RequiredCapability.STRUCTURED_OUTPUT: "structured_output",
    RequiredCapability.TOOL_CALLING: "tool_calling",
    RequiredCapability.REASONING: "reasoning",
    RequiredCapability.VISION: "vision",
    RequiredCapability.JSON_MODE: "json_mode",
}


class RoutingService(
    RoutingServiceInterface,
):
    def __init__(
        self,
        *,
        catalog: ModelCatalogRegistry,
        scoring_engine: ScoringEngineInterface,
        strategy_profiles: dict[RoutingStrategy, RoutingStrategyProfile],
    ) -> None:
        self._catalog = catalog

        self._scoring_engine = scoring_engine

        self._strategy_profiles = strategy_profiles

    # ==========================================================
    # Public
    # ==========================================================

    def route(
        self,
        request: RoutingRequest,
    ) -> RoutingDecision:

        started = perf_counter()

        profile = self._resolve_profile(
            request.strategy,
        )

        candidates = self._filter_candidates(
            request=request,
            profile=profile,
        )

        if not candidates:
            logger.warning(
                "routing.no_eligible_models",
                strategy=request.strategy.value,
                request_id=str(request.request_id),
            )

            raise NoEligibleModelsError(
                f"No models satisfy strategy '{request.strategy.value}' after "
                "capability and policy filtering."
            )

        scored = self._scoring_engine.score_candidates(
            models=candidates,
            weights=profile.weights,
        )

        selected = scored[0]

        fallback_models = self._build_fallback_chain(
            scored=scored[1:],
            selected=selected.model,
            max_fallbacks=request.max_fallbacks,
        )

        routing_latency_ms = round(
            (perf_counter() - started) * 1000,
            3,
        )

        decision = RoutingDecision(
            request_id=request.request_id,
            strategy=request.strategy,
            selected_model=selected.model,
            fallback_models=fallback_models,
            score=selected.score,
            reasons=selected.reasons,
            evaluated_count=len(candidates),
            routing_latency_ms=routing_latency_ms,
        )

        logger.info(
            "routing.decision",
            request_id=str(request.request_id),
            strategy=decision.strategy.value,
            selected_provider=decision.selected_model.provider.value,
            selected_model=decision.selected_model.model_name,
            fallback_models=[model.model_name for model in decision.fallback_models],
            score=decision.score,
            reasons=decision.reasons,
            evaluated_count=decision.evaluated_count,
            routing_latency_ms=decision.routing_latency_ms,
        )

        return decision

    # ==========================================================
    # Strategy Resolution
    # ==========================================================

    def _resolve_profile(
        self,
        strategy: RoutingStrategy,
    ) -> RoutingStrategyProfile:

        profile = self._strategy_profiles.get(
            strategy,
        )

        if profile is not None:
            return profile

        logger.warning(
            "routing.unknown_strategy_fallback_to_auto",
            strategy=strategy.value,
        )

        return self._strategy_profiles[RoutingStrategy.AUTO]

    # ==========================================================
    # Capability + Policy Filtering
    # ==========================================================

    def _filter_candidates(
        self,
        *,
        request: RoutingRequest,
        profile: RoutingStrategyProfile,
    ) -> list[ModelMetadata]:

        required_capabilities = set(
            request.required_capabilities,
        ) | set(
            profile.required_capabilities,
        )

        min_context_window = max(
            request.min_context_window or 0,
            profile.min_context_window or 0,
        )

        allow_experimental = request.allow_experimental or profile.require_local

        allow_local = request.allow_local or profile.require_local

        candidates: list[ModelMetadata] = []

        for model in self._catalog.enabled():
            if model.model_name in request.excluded_models:
                continue

            if profile.require_local and not model.local:
                continue

            if model.experimental and not allow_experimental:
                continue

            if model.local and not allow_local:
                continue

            if model.context_window < min_context_window:
                continue

            if not self._satisfies_capabilities(
                model,
                required_capabilities,
            ):
                continue

            candidates.append(
                model,
            )

        return candidates

    @staticmethod
    def _satisfies_capabilities(
        model: ModelMetadata,
        required_capabilities: set[RequiredCapability],
    ) -> bool:

        return all(
            getattr(
                model.capabilities,
                _CAPABILITY_FIELDS[capability],
            )
            for capability in required_capabilities
        )

    # ==========================================================
    # Fallback Chain
    # ==========================================================

    @staticmethod
    def _build_fallback_chain(
        *,
        scored: list[ScoredModel],
        selected: ModelMetadata,
        max_fallbacks: int,
    ) -> list[ModelMetadata]:
        """
        Fills fallback slots preferring a provider not already used —
        by the primary selection or an earlier fallback — so a single
        provider outage can't take out the whole chain. Once distinct
        providers run out, remaining slots fall back to the next
        highest-scored candidates regardless of provider.
        """

        if max_fallbacks == 0 or not scored:
            return []

        used_providers = {selected.provider}

        fallbacks: list[ModelMetadata] = []

        same_provider: list[ScoredModel] = []

        for scored_model in scored:
            if len(fallbacks) >= max_fallbacks:
                break

            if scored_model.model.provider in used_providers:
                same_provider.append(
                    scored_model,
                )
                continue

            fallbacks.append(
                scored_model.model,
            )

            used_providers.add(
                scored_model.model.provider,
            )

        for scored_model in same_provider:
            if len(fallbacks) >= max_fallbacks:
                break

            fallbacks.append(
                scored_model.model,
            )

        return fallbacks
