"""
Unit tests for ModelCatalogRegistry.

Covers:
- all()/enabled() reflect the seeded model list
- enabled() keeps experimental/local models (only enabled=False is excluded)
- get()/has() exact provider+model_name lookup
- by_provider() filters correctly
- local_models() returns only local=True entries
- get_model_catalog_registry() returns a cached singleton
"""

from __future__ import annotations

from app.ai.runtime.generation.catalog.models import (
    ModelMetadata,
)
from app.ai.runtime.generation.catalog.registry import (
    ModelCatalogRegistry,
    get_model_catalog_registry,
)
from app.ai.runtime.generation.config import (
    ProviderCapabilities,
)
from app.ai.runtime.generation.enums import (
    GenerationProvider,
)


def _make_model(
    provider: GenerationProvider = GenerationProvider.OPENAI,
    model_name: str = "test-model",
    enabled: bool = True,
    experimental: bool = False,
    local: bool = False,
) -> ModelMetadata:
    return ModelMetadata(
        provider=provider,
        model_name=model_name,
        display_name=model_name,
        context_window=100_000,
        capabilities=ProviderCapabilities(),
        enabled=enabled,
        experimental=experimental,
        local=local,
    )


def test_all_returns_every_seeded_model() -> None:
    models = [_make_model(model_name="a"), _make_model(model_name="b")]
    registry = ModelCatalogRegistry(models=models)

    assert registry.all() == models


def test_enabled_excludes_only_hard_disabled_models() -> None:
    enabled_model = _make_model(model_name="enabled")
    disabled_model = _make_model(model_name="disabled", enabled=False)
    experimental_model = _make_model(model_name="experimental", experimental=True)
    local_model = _make_model(model_name="local", local=True)

    registry = ModelCatalogRegistry(
        models=[enabled_model, disabled_model, experimental_model, local_model],
    )

    assert registry.enabled() == [enabled_model, experimental_model, local_model]


def test_get_finds_exact_provider_and_model_name() -> None:
    target = _make_model(provider=GenerationProvider.CLAUDE, model_name="claude-sonnet-4")
    registry = ModelCatalogRegistry(models=[target, _make_model(model_name="other")])

    assert registry.get(GenerationProvider.CLAUDE, "claude-sonnet-4") is target


def test_get_returns_none_for_unknown_model() -> None:
    registry = ModelCatalogRegistry(models=[_make_model()])

    assert registry.get(GenerationProvider.CLAUDE, "does-not-exist") is None


def test_has_reflects_get_result() -> None:
    registry = ModelCatalogRegistry(
        models=[_make_model(provider=GenerationProvider.GROQ, model_name="llama")],
    )

    assert registry.has(GenerationProvider.GROQ, "llama") is True
    assert registry.has(GenerationProvider.GROQ, "missing") is False


def test_by_provider_filters_to_matching_provider() -> None:
    openai_model = _make_model(provider=GenerationProvider.OPENAI, model_name="gpt")
    claude_model = _make_model(provider=GenerationProvider.CLAUDE, model_name="claude")

    registry = ModelCatalogRegistry(models=[openai_model, claude_model])

    assert registry.by_provider(GenerationProvider.OPENAI) == [openai_model]


def test_local_models_returns_only_local_entries() -> None:
    local_model = _make_model(model_name="local", local=True)
    cloud_model = _make_model(model_name="cloud", local=False)

    registry = ModelCatalogRegistry(models=[local_model, cloud_model])

    assert registry.local_models() == [local_model]


def test_total_models_counts_seeded_models() -> None:
    models = [_make_model(model_name="a"), _make_model(model_name="b")]
    registry = ModelCatalogRegistry(models=models)

    assert registry.total_models() == 2


def test_default_registry_is_seeded_from_all_models() -> None:
    registry = ModelCatalogRegistry()

    assert registry.total_models() > 0
    assert registry.has(GenerationProvider.OPENAI, "gpt-5")


def test_get_model_catalog_registry_is_a_cached_singleton() -> None:
    assert get_model_catalog_registry() is get_model_catalog_registry()
