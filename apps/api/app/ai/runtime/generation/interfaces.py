from __future__ import annotations

from abc import (
    ABC,
    abstractmethod,
)

from app.ai.runtime.generation.config import (
    BaseGenerationConfig,
)
from app.ai.runtime.generation.enums import (
    GenerationProvider,
)
from app.ai.runtime.generation.models import (
    GenerationRequest,
    GenerationResult,
)


class GenerationProviderInterface(
    ABC,
):
    @property
    @abstractmethod
    def provider(
        self,
    ) -> GenerationProvider:
        pass

    @property
    @abstractmethod
    def version(
        self,
    ) -> str:
        pass

    @property
    @abstractmethod
    def config(
        self,
    ) -> BaseGenerationConfig:
        pass

    @property
    def configuration_fingerprint(
        self,
    ) -> str:
        return self.config.model_dump_json()

    @abstractmethod
    async def generate(
        self,
        request: GenerationRequest,
    ) -> GenerationResult:
        pass
