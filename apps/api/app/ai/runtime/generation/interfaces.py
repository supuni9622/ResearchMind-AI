from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import AsyncIterator
from typing import Any

from app.ai.runtime.generation.config import (
    BaseGenerationConfig,
)
from app.ai.runtime.generation.enums import (
    GenerationProvider,
)
from app.ai.runtime.generation.models import (
    GenerationRequest,
    GenerationResult,
    ProviderCapabilities,
    StreamChunk,
)


class GenerationProviderInterface(
    ABC,
):
    """
    Canonical contract for all LLM providers.

    Providers should normalize their SDK responses into
    GenerationResult so the rest of the platform remains
    provider independent.
    """

    # ==========================================================
    # Metadata
    # ==========================================================

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
    @abstractmethod
    def capabilities(
        self,
    ) -> ProviderCapabilities:
        """
        Exposes provider capabilities to:

        - routing
        - planner
        - agents
        - structured outputs
        - benchmarks
        """
        pass

    @property
    def configuration_fingerprint(
        self,
    ) -> str:
        return self.config.model_dump_json()

    # ==========================================================
    # Generation
    # ==========================================================

    @abstractmethod
    async def generate(
        self,
        request: GenerationRequest,
    ) -> GenerationResult:
        """
        Standard text generation.
        """
        pass

    # ==========================================================
    # Structured Generation
    # ==========================================================

    async def generate_structured(
        self,
        request: GenerationRequest,
    ) -> GenerationResult:
        """
        Default implementation.

        Providers with native structured output support
        should override this.
        """

        return await self.generate(
            request,
        )

    # ==========================================================
    # Streaming
    # ==========================================================

    def stream(
        self,
        request: GenerationRequest,
    ) -> AsyncIterator[StreamChunk]:
        """
        Providers supporting streaming should override.

        Default implementation raises.
        """

        raise NotImplementedError(f"{self.provider.value} does not support streaming.")

    # ==========================================================
    # Validation
    # ==========================================================

    def supports_streaming(
        self,
    ) -> bool:
        return self.capabilities.streaming

    def supports_structured_output(
        self,
    ) -> bool:
        return self.capabilities.structured_output

    def supports_json_mode(
        self,
    ) -> bool:
        return self.capabilities.json_mode

    def supports_tools(
        self,
    ) -> bool:
        return self.capabilities.tool_calling

    def supports_reasoning(
        self,
    ) -> bool:
        return self.capabilities.reasoning

    def supports_vision(
        self,
    ) -> bool:
        return self.capabilities.vision

    # ==========================================================
    # Future Runtime Hooks
    # ==========================================================

    def supports_parallel_tools(
        self,
    ) -> bool:
        return self.capabilities.parallel_tool_calls

    def supports_multimodal_input(
        self,
    ) -> bool:
        return self.capabilities.multimodal_input

    def supports_multimodal_output(
        self,
    ) -> bool:
        return self.capabilities.multimodal_output

    # ==========================================================
    # Future Tool Runtime
    # ==========================================================

    async def count_tokens(
        self,
        text: str,
    ) -> int:
        """
        Future:

        - token budgeting
        - routing
        - compression
        - observability
        """

        raise NotImplementedError()

    def estimate_cost(
        self,
        *,
        prompt_tokens: int,
        completion_tokens: int,
    ) -> float:
        """
        Future:

        - routing
        - budgeting
        - observability
        """

        input_cost = (prompt_tokens / 1_000_000) * self.config.cost_per_input_1m

        output_cost = (completion_tokens / 1_000_000) * self.config.cost_per_output_1m

        return input_cost + output_cost

    # ==========================================================
    # Raw Access
    # ==========================================================

    async def health_check(
        self,
    ) -> bool:
        """
        Future:

        - startup checks
        - admin dashboard
        - routing
        """

        return True

    async def get_model_metadata(
        self,
    ) -> dict[str, Any]:
        """
        Future:

        - model catalog
        - routing engine
        - benchmarks
        """

        return {
            "provider": self.provider.value,
            "model": self.config.model_name,
            "context_window": self.config.context_window,
            "capabilities": self.capabilities.model_dump(),
        }
