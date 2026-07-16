from __future__ import annotations

import asyncio
import hashlib
from abc import ABC
from collections.abc import AsyncIterator
from datetime import UTC, datetime
from time import perf_counter
from typing import Any, Generic, TypeVar

import structlog
from app.ai.runtime.generation.config import (
    BaseGenerationConfig,
    ProviderCapabilities,
)
from app.ai.runtime.generation.exceptions import (
    GenerationExecutionError,
)
from app.ai.runtime.generation.interfaces import (
    GenerationProviderInterface,
)
from app.ai.runtime.generation.models import (
    GenerationExecution,
    GenerationRequest,
    GenerationResult,
    GenerationStatistics,
    StreamChunk,
)

logger = structlog.get_logger()

ConfigT = TypeVar(
    "ConfigT",
    bound=BaseGenerationConfig,
)


class BaseGenerationProvider(
    GenerationProviderInterface,
    Generic[ConfigT],
    ABC,
):
    VERSION = "1.0"

    def __init__(
        self,
        config: ConfigT,
    ) -> None:
        self._config = config

        self._configuration_fingerprint = hashlib.sha256(
            self._config.model_dump_json().encode("utf-8")
        ).hexdigest()

    # ==========================================================
    # Metadata
    # ==========================================================

    @property
    def version(
        self,
    ) -> str:
        return self.VERSION

    @property
    def config(
        self,
    ) -> ConfigT:
        return self._config

    @property
    def capabilities(
        self,
    ) -> ProviderCapabilities:
        return self._config.capabilities

    @property
    def configuration_fingerprint(
        self,
    ) -> str:
        return self._configuration_fingerprint

    # ==========================================================
    # Retry Handling
    # ==========================================================

    async def _execute_with_retry(
        self,
        fn,
    ):
        last_error = None

        for attempt in range(
            self.config.max_retries + 1,
        ):
            try:
                return await fn()

            except Exception as exc:
                last_error = exc

                logger.warning(
                    "generation.retry",
                    provider=self.provider.value,
                    attempt=attempt + 1,
                    error=str(exc),
                )

                if attempt < self.config.max_retries:
                    await asyncio.sleep(
                        2**attempt,
                    )

        raise GenerationExecutionError(
            str(last_error),
        ) from last_error

    # ==========================================================
    # Timing Helpers
    # ==========================================================

    @staticmethod
    def start_timer() -> float:
        return perf_counter()

    @staticmethod
    def stop_timer(
        started: float,
    ) -> float:
        return (perf_counter() - started) * 1000

    # ==========================================================
    # Cost Helpers
    # ==========================================================

    def estimate_cost(
        self,
        *,
        prompt_tokens: int,
        completion_tokens: int,
    ) -> float:

        input_cost = (prompt_tokens / 1_000_000) * self.config.cost_per_input_1m

        output_cost = (completion_tokens / 1_000_000) * self.config.cost_per_output_1m

        return input_cost + output_cost

    # ==========================================================
    # Statistics Builder
    # ==========================================================

    def build_statistics(
        self,
        *,
        latency_ms: float,
        prompt_tokens: int = 0,
        completion_tokens: int = 0,
        reasoning_tokens: int = 0,
        retries: int = 0,
        cache_hit: bool = False,
        streamed: bool = False,
    ) -> GenerationStatistics:

        total_tokens = prompt_tokens + completion_tokens + reasoning_tokens

        return GenerationStatistics(
            provider=self.provider,
            model=self.config.model_name,
            latency_ms=latency_ms,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            reasoning_tokens=reasoning_tokens,
            total_tokens=total_tokens,
            retries=retries,
            cache_hit=cache_hit,
            streamed=streamed,
            estimated_cost_usd=self.estimate_cost(
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
            ),
        )

    # ==========================================================
    # Result Builder
    # ==========================================================

    def build_result(
        self,
        *,
        request: GenerationRequest,
        content: str,
        statistics: GenerationStatistics,
        finish_reason: str | None = None,
        metadata: dict[str, Any] | None = None,
        parsed_output: Any | None = None,
        raw_response: dict[str, Any] | None = None,
        tool_calls: list[Any] | None = None,
        citations: list[Any] | None = None,
        reasoning: str | None = None,
    ) -> GenerationResult:

        return GenerationResult(
            request=request,
            execution=GenerationExecution(
                completed_at=datetime.now(
                    UTC,
                )
            ),
            statistics=statistics,
            provider=self.provider,
            model=self.config.model_name,
            content=content,
            finish_reason=finish_reason,
            metadata=metadata or {},
            parsed_output=parsed_output,
            raw_response=raw_response,
            tool_calls=tool_calls or [],
            citations=citations or [],
            reasoning=reasoning,
        )

    # ==========================================================
    # Prompt Builder
    # ==========================================================

    def build_messages(
        self,
        request: GenerationRequest,
    ) -> list[dict[str, str]]:

        messages = []

        if request.system_prompt:
            messages.append(
                {
                    "role": "system",
                    "content": request.system_prompt,
                }
            )

        messages.append(
            {
                "role": "user",
                "content": (f"{request.prompt_context.context}\n\n{request.user_prompt}"),
            }
        )

        return messages

    # ==========================================================
    # Structured Outputs
    # ==========================================================

    async def generate_structured(
        self,
        request: GenerationRequest,
    ) -> GenerationResult:

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

        raise NotImplementedError(f"{self.provider.value} does not support streaming.")

    # ==========================================================
    # Token Counting
    # ==========================================================

    async def count_tokens(
        self,
        text: str,
    ) -> int:
        """
        Placeholder.

        Future:
        - routing
        - context compression
        - budgeting
        """

        return len(text.split())

    # ==========================================================
    # Health Checks
    # ==========================================================

    async def health_check(
        self,
    ) -> bool:
        return True

    # ==========================================================
    # Metadata
    # ==========================================================

    async def get_model_metadata(
        self,
    ) -> dict[str, Any]:

        return {
            "provider": self.provider.value,
            "model": self.config.model_name,
            "version": self.version,
            "context_window": self.config.context_window,
            "capabilities": (self.capabilities.model_dump()),
        }
