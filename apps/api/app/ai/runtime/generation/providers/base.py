from __future__ import annotations

import hashlib
from abc import ABC
from typing import Generic, TypeVar

from app.ai.runtime.generation.config import (
    BaseGenerationConfig,
)
from app.ai.runtime.generation.interfaces import (
    GenerationProviderInterface,
)

ConfigT = TypeVar(
    "ConfigT",
    bound=BaseGenerationConfig,
)


class BaseGenerationProvider(
    GenerationProviderInterface,
    Generic[ConfigT],
    ABC,
):
    def __init__(
        self,
        config: ConfigT,
    ) -> None:
        self._config = config

        self._configuration_fingerprint = hashlib.sha256(
            self._config.model_dump_json().encode("utf-8")
        ).hexdigest()

    @property
    def version(
        self,
    ) -> str:
        return "1.0"

    @property
    def config(
        self,
    ) -> ConfigT:
        return self._config

    @property
    def configuration_fingerprint(
        self,
    ) -> str:
        return self._configuration_fingerprint
