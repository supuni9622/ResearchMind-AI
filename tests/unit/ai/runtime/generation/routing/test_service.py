"""
Unit tests for RoutingService.

Covers:
- Capability filtering removes models missing a required capability
- Policy filtering excludes disabled/experimental/local models by default
- allow_experimental/allow_local opt models back in
- min_context_window filtering (request-level and profile-level)
- excluded_models is honored
- The LOCAL strategy narrows candidates to local models only
- An unknown strategy falls back to AUTO's profile
- Fallback chain prefers distinct providers before repeating one
- max_fallbacks bounds the fallback chain length (including 0)
- NoEligibleModelsError is raised when nothing survives filtering
- Every RoutingDecision carries the request_id it was built for
"""

from __future__ import annotations

import pytest
from app.ai.runtime.generation.catalog.models import (
    ModelMetadata,
)
from app.ai.runtime.generation.catalog.registry import (
    ModelCatalogRegistry,
)
from app.ai.runtime.generation.config import (
    ProviderCapabilities,
)
from app.ai.runtime.generation.enums import (
    GenerationProvider,
)
from app.ai.runtime.generation.routing.enums import (
    RequiredCapability,
    RoutingStrategy,
)
from app.ai.runtime.generation.routing.exceptions import (
    NoEligibleModelsError,
)
from app.ai.runtime.generation.routing.models import (
    RoutingRequest,
    RoutingStrategyProfile,
)
from app.ai.runtime.generation.routing.scoring.service import (
    ScoringService,
)
from app.ai.runtime.generation.routing.scoring.weights import (
    ScoringWeights,
)
from app.ai.runtime.generation.routing.service import (
    RoutingService,
)


def _make_model(
    model_name: str,
    *,
    provider: GenerationProvider = GenerationProvider.OPENAI,
    quality_score: float = 0.5,
    context_window: int = 100_000,
    structured_output: bool = False,
    tool_calling: bool = False,
    enabled: bool = True,
    experimental: bool = False,
    local: bool = False,
) -> ModelMetadata:
    return ModelMetadata(
        provider=provider,
        model_name=model_name,
        display_name=model_name,
        context_window=context_window,
        capabilities=ProviderCapabilities(
            structured_output=structured_output,
            tool_calling=tool_calling,
        ),
        quality_score=quality_score,
        enabled=enabled,
        experimental=experimental,
        local=local,
    )


_QUALITY_ONLY_WEIGHTS = ScoringWeights(quality=1.0)


def _make_service(
    models: list[ModelMetadata],
    profiles: dict[RoutingStrategy, RoutingStrategyProfile] | None = None,
) -> RoutingService:

    default_profiles = {
        strategy: RoutingStrategyProfile(strategy=strategy, weights=_QUALITY_ONLY_WEIGHTS)
        for strategy in RoutingStrategy
    }

    if profiles:
        default_profiles.update(profiles)

    return RoutingService(
        catalog=ModelCatalogRegistry(models=models),
        scoring_engine=ScoringService(),
        strategy_profiles=default_profiles,
    )


def test_route_selects_the_highest_scoring_candidate() -> None:
    weak = _make_model("weak", quality_score=0.2)
    strong = _make_model("strong", quality_score=0.9)

    service = _make_service([weak, strong])

    decision = service.route(RoutingRequest(strategy=RoutingStrategy.AUTO))

    assert decision.selected_model.model_name == "strong"


def test_route_excludes_disabled_models_unconditionally() -> None:
    disabled = _make_model("disabled", enabled=False)
    enabled = _make_model("enabled")

    service = _make_service([disabled, enabled])

    decision = service.route(
        RoutingRequest(strategy=RoutingStrategy.AUTO, allow_experimental=True, allow_local=True)
    )

    assert decision.selected_model.model_name == "enabled"
    assert "disabled" not in [m.model_name for m in decision.fallback_models]


def test_route_excludes_experimental_models_by_default() -> None:
    experimental = _make_model("experimental", experimental=True, quality_score=0.99)
    stable = _make_model("stable", quality_score=0.1)

    service = _make_service([experimental, stable])

    decision = service.route(RoutingRequest(strategy=RoutingStrategy.AUTO))

    assert decision.selected_model.model_name == "stable"


def test_allow_experimental_opts_experimental_models_back_in() -> None:
    experimental = _make_model("experimental", experimental=True, quality_score=0.99)
    stable = _make_model("stable", quality_score=0.1)

    service = _make_service([experimental, stable])

    decision = service.route(RoutingRequest(strategy=RoutingStrategy.AUTO, allow_experimental=True))

    assert decision.selected_model.model_name == "experimental"


def test_route_excludes_local_models_by_default() -> None:
    local = _make_model("local", local=True, quality_score=0.99)
    cloud = _make_model("cloud", quality_score=0.1)

    service = _make_service([local, cloud])

    decision = service.route(RoutingRequest(strategy=RoutingStrategy.AUTO))

    assert decision.selected_model.model_name == "cloud"


def test_allow_local_opts_local_models_back_in() -> None:
    local = _make_model("local", local=True, quality_score=0.99)
    cloud = _make_model("cloud", quality_score=0.1)

    service = _make_service([local, cloud])

    decision = service.route(RoutingRequest(strategy=RoutingStrategy.AUTO, allow_local=True))

    assert decision.selected_model.model_name == "local"


def test_local_strategy_narrows_candidates_to_local_models_only() -> None:
    local = _make_model("local", local=True, experimental=True, quality_score=0.1)
    cloud = _make_model("cloud", quality_score=0.99)

    profiles = {
        RoutingStrategy.LOCAL: RoutingStrategyProfile(
            strategy=RoutingStrategy.LOCAL,
            weights=_QUALITY_ONLY_WEIGHTS,
            require_local=True,
        ),
    }

    service = _make_service([local, cloud], profiles=profiles)

    decision = service.route(RoutingRequest(strategy=RoutingStrategy.LOCAL))

    assert decision.selected_model.model_name == "local"


def test_required_capability_filters_out_models_missing_it() -> None:
    lacks_tools = _make_model("lacks-tools", tool_calling=False, quality_score=0.99)
    has_tools = _make_model("has-tools", tool_calling=True, quality_score=0.1)

    service = _make_service([lacks_tools, has_tools])

    decision = service.route(
        RoutingRequest(
            strategy=RoutingStrategy.AUTO,
            required_capabilities=[RequiredCapability.TOOL_CALLING],
        )
    )

    assert decision.selected_model.model_name == "has-tools"


def test_profile_required_capabilities_are_combined_with_request_level_ones() -> None:
    unstructured = _make_model("unstructured", structured_output=False, quality_score=0.99)
    structured = _make_model("structured", structured_output=True, quality_score=0.1)

    profiles = {
        RoutingStrategy.VALIDATION: RoutingStrategyProfile(
            strategy=RoutingStrategy.VALIDATION,
            weights=_QUALITY_ONLY_WEIGHTS,
            required_capabilities=[RequiredCapability.STRUCTURED_OUTPUT],
        ),
    }

    service = _make_service([unstructured, structured], profiles=profiles)

    decision = service.route(RoutingRequest(strategy=RoutingStrategy.VALIDATION))

    assert decision.selected_model.model_name == "structured"


def test_min_context_window_filters_out_smaller_models() -> None:
    small = _make_model("small", context_window=50_000, quality_score=0.99)
    large = _make_model("large", context_window=500_000, quality_score=0.1)

    service = _make_service([small, large])

    decision = service.route(
        RoutingRequest(strategy=RoutingStrategy.AUTO, min_context_window=100_000)
    )

    assert decision.selected_model.model_name == "large"


def test_excluded_models_are_skipped() -> None:
    excluded = _make_model("excluded", quality_score=0.99)
    other = _make_model("other", quality_score=0.1)

    service = _make_service([excluded, other])

    decision = service.route(
        RoutingRequest(strategy=RoutingStrategy.AUTO, excluded_models=["excluded"])
    )

    assert decision.selected_model.model_name == "other"


def test_unknown_strategy_falls_back_to_auto_profile() -> None:
    model = _make_model("model", quality_score=0.5)

    profiles = {
        RoutingStrategy.AUTO: RoutingStrategyProfile(
            strategy=RoutingStrategy.AUTO,
            weights=_QUALITY_ONLY_WEIGHTS,
        ),
    }

    service = RoutingService(
        catalog=ModelCatalogRegistry(models=[model]),
        scoring_engine=ScoringService(),
        strategy_profiles=profiles,
    )

    decision = service.route(RoutingRequest(strategy=RoutingStrategy.CODING))

    assert decision.selected_model.model_name == "model"


def test_fallback_chain_prefers_distinct_providers_first() -> None:
    primary = _make_model("primary", provider=GenerationProvider.CLAUDE, quality_score=0.9)
    same_provider = _make_model(
        "same-provider", provider=GenerationProvider.CLAUDE, quality_score=0.8
    )
    other_provider = _make_model(
        "other-provider", provider=GenerationProvider.OPENAI, quality_score=0.7
    )

    service = _make_service([primary, same_provider, other_provider])

    decision = service.route(RoutingRequest(strategy=RoutingStrategy.AUTO, max_fallbacks=1))

    assert decision.selected_model.model_name == "primary"
    assert [m.model_name for m in decision.fallback_models] == ["other-provider"]


def test_fallback_chain_fills_remaining_slots_from_repeated_providers() -> None:
    primary = _make_model("primary", provider=GenerationProvider.CLAUDE, quality_score=0.9)
    same_provider = _make_model(
        "same-provider", provider=GenerationProvider.CLAUDE, quality_score=0.8
    )

    service = _make_service([primary, same_provider])

    decision = service.route(RoutingRequest(strategy=RoutingStrategy.AUTO, max_fallbacks=2))

    assert [m.model_name for m in decision.fallback_models] == ["same-provider"]


def test_max_fallbacks_zero_returns_no_fallbacks() -> None:
    primary = _make_model("primary", quality_score=0.9)
    other = _make_model("other", quality_score=0.1)

    service = _make_service([primary, other])

    decision = service.route(RoutingRequest(strategy=RoutingStrategy.AUTO, max_fallbacks=0))

    assert decision.fallback_models == []


def test_no_eligible_models_raises() -> None:
    service = _make_service([_make_model("only", enabled=False)])

    with pytest.raises(NoEligibleModelsError):
        service.route(RoutingRequest(strategy=RoutingStrategy.AUTO))


def test_decision_carries_the_request_id_and_evaluated_count() -> None:
    service = _make_service([_make_model("a"), _make_model("b")])

    request = RoutingRequest(strategy=RoutingStrategy.AUTO)

    decision = service.route(request)

    assert decision.request_id == request.request_id
    assert decision.evaluated_count == 2
    assert decision.strategy == RoutingStrategy.AUTO
