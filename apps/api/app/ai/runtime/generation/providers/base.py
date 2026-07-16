from __future__ import annotations

import asyncio
import hashlib
import json
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
from app.ai.runtime.generation.structured_output.repair import (
    StructuredOutputRepair,
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
        last_error: Exception | None = None

        max_attempts = self.config.max_retries + 1

        for attempt in range(
            max_attempts,
        ):
            try:
                return await fn()

            except Exception as exc:
                last_error = exc

                is_final_attempt = attempt == max_attempts - 1

                logger.warning(
                    "generation.retry" if not is_final_attempt else "generation.retry_exhausted",
                    provider=self.provider.value,
                    model=self.config.model_name,
                    attempt=attempt + 1,
                    max_attempts=max_attempts,
                    error_type=type(exc).__name__,
                    error=str(exc),
                )

                if not is_final_attempt:
                    await asyncio.sleep(
                        2**attempt,
                    )

        logger.error(
            "generation.execution_failed",
            provider=self.provider.value,
            model=self.config.model_name,
            attempts=max_attempts,
            error_type=type(last_error).__name__,
            error=str(last_error),
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

    def parse_structured_output(
        self,
        content: str,
    ) -> Any | None:
        """
        Parser fallback for structured generation.

        Native schema-constrained decoding (OpenAI json_schema, Gemini
        response_json_schema, Claude output_config.format, Ollama schema
        format) should already return valid JSON. This exists for the
        remaining cases: providers without schema enforcement (JSON mode,
        prompt-only instructions) or a model that drifts from the schema.

        Tries strict parsing first, then falls back to StructuredOutputRepair
        for common formatting mistakes (markdown fences, trailing commas,
        single quotes, unbalanced braces) before giving up.
        """

        try:
            return json.loads(
                content,
            )
        except (TypeError, ValueError):
            pass

        try:
            parsed = StructuredOutputRepair.try_parse_json(
                content,
            )
        except (TypeError, ValueError):
            logger.warning(
                "generation.structured_output.parse_failed",
                provider=self.provider.value,
                model=self.config.model_name,
            )

            return None

        logger.info(
            "generation.structured_output.repaired",
            provider=self.provider.value,
            model=self.config.model_name,
        )

        return parsed

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
