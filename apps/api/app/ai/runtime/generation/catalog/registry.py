from __future__ import annotations

from functools import lru_cache

from app.ai.runtime.generation.catalog.models import (
    ALL_MODELS,
    ModelMetadata,
)
from app.ai.runtime.generation.enums import (
    GenerationProvider,
)


class ModelCatalogRegistry:
    """
    Lookup surface over the model catalog.

    Holds no routing logic itself — filtering and scoring live in
    `routing/`. This only answers "what models exist" and "what do we
    know about them".
    """

    def __init__(
        self,
        models: list[ModelMetadata] | None = None,
    ) -> None:
        self._models: list[ModelMetadata] = list(
            models if models is not None else ALL_MODELS,
        )

    # ==========================================================
    # Bulk Access
    # ==========================================================

    def all(
        self,
    ) -> list[ModelMetadata]:
        return list(
            self._models,
        )

    def enabled(
        self,
    ) -> list[ModelMetadata]:
        """
        Models that have not been hard-disabled. Still includes
        `experimental`/`local` entries — those are gated later, at
        routing time, based on the request (see `routing/service.py`).
        """

        return [model for model in self._models if model.enabled]

    def by_provider(
        self,
        provider: GenerationProvider,
    ) -> list[ModelMetadata]:
        return [model for model in self._models if model.provider == provider]

    def local_models(
        self,
    ) -> list[ModelMetadata]:
        return [model for model in self._models if model.local]

    # ==========================================================
    # Single Lookup
    # ==========================================================

    def get(
        self,
        provider: GenerationProvider,
        model_name: str,
    ) -> ModelMetadata | None:

        for model in self._models:
            if model.provider == provider and model.model_name == model_name:
                return model

        return None

    def has(
        self,
        provider: GenerationProvider,
        model_name: str,
    ) -> bool:
        return self.get(provider, model_name) is not None

    # ==========================================================
    # Diagnostics
    # ==========================================================

    def total_models(
        self,
    ) -> int:
        return len(self._models)


@lru_cache
def get_model_catalog_registry() -> ModelCatalogRegistry:
    return ModelCatalogRegistry()
