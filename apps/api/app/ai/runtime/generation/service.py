from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Any
from uuid import uuid4

import structlog
from app.ai.artifacts.enums import (
    ArtifactCategory,
    ArtifactRuntime,
)
from app.ai.artifacts.generation.builders import (
    GenerationArtifactBuilder,
)
from app.ai.artifacts.generation.writers import (
    GenerationArtifactWriter,
)
from app.ai.artifacts.policies.service import (
    ArtifactPolicyService,
)
from app.ai.guardrails.service import (
    GuardrailService,
)
from app.ai.knowledge.context.models import (
    PromptContext,
)
from app.ai.observability.providers.langsmith.tracing import (
    NoOpTracer,
    RuntimeTracer,
)
from app.ai.observability.service import (
    ObservabilityService,
)
from app.ai.runtime.generation.caching.models import (
    CacheResult,
)
from app.ai.runtime.generation.caching.service import (
    CachingService,
)
from app.ai.runtime.generation.enums import (
    GenerationProvider,
    ResponseFormat,
)
from app.ai.runtime.generation.exceptions import (
    GenerationError,
    GenerationExecutionError,
    GenerationProviderNotFoundError,
    GenerationValidationError,
    GuardrailViolationError,
)
from app.ai.runtime.generation.interfaces import (
    GenerationProviderInterface,
)
from app.ai.runtime.generation.models import (
    GenerationRequest,
    GenerationResult,
    StreamChunk,
    ToolDefinition,
)
from app.ai.runtime.generation.observability.service import (
    GenerationMetricsService,
)
from app.ai.runtime.generation.policies.acceptance import (
    AcceptanceDecision,
    AcceptancePolicy,
)
from app.ai.runtime.generation.policies.fail_fast import (
    FailFastPolicy,
)
from app.ai.runtime.generation.policies.runtime import (
    RuntimeValidationPolicy,
)
from app.ai.runtime.generation.prompts.models import (
    PromptRenderRequest,
)
from app.ai.runtime.generation.prompts.service import (
    PromptService,
)
from app.ai.runtime.generation.registry import (
    GenerationRegistry,
)
from app.ai.runtime.generation.routing.enums import (
    RoutingStrategy,
)
from app.ai.runtime.generation.routing.exceptions import (
    NoEligibleModelsError,
)
from app.ai.runtime.generation.routing.models import (
    RoutingDecision,
    RoutingRequest,
)
from app.ai.runtime.generation.routing.service import (
    RoutingService,
)
from app.ai.runtime.generation.structured_output.models import (
    OutputFormat,
)
from app.ai.runtime.generation.structured_output.registry import (
    StructuredOutputRegistry,
)
from app.ai.runtime.generation.validation.models import (
    InputValidationContext,
    ValidationSeverity,
)
from app.ai.runtime.generation.validation.service import (
    ValidationService,
)
from app.services.generation_usage import GenerationUsageService
from langchain_core.messages import (
    AIMessage,
    BaseMessage,
    SystemMessage,
)
from langchain_core.output_parsers import (
    PydanticOutputParser,
)
from pydantic import (
    BaseModel,
)

logger = structlog.get_logger()

#
# response_format values whose parsed_output is derived by running
# result.content through the Structured Output Platform's parser
# registry, rather than through provider-native structured decoding
# (no provider supports schema-constrained Markdown/XML generation).
#

_REGISTRY_PARSED_FORMATS: dict[ResponseFormat, OutputFormat] = {
    ResponseFormat.MARKDOWN: OutputFormat.MARKDOWN,
    ResponseFormat.XML: OutputFormat.XML,
}


class GenerationService:
    def __init__(
        self,
        registry: GenerationRegistry,
        structured_output_registry: StructuredOutputRegistry | None = None,
        validation_service: ValidationService | None = None,
        prompt_service: PromptService | None = None,
        routing_service: RoutingService | None = None,
        caching_service: CachingService | None = None,
        guardrail_service: GuardrailService | None = None,
        artifact_writer: GenerationArtifactWriter | None = None,
        artifact_policy_service: ArtifactPolicyService | None = None,
        acceptance_policy: AcceptancePolicy | None = None,
        fail_fast_policy: FailFastPolicy | None = None,
        runtime_validation_policy: RuntimeValidationPolicy | None = None,
        metrics_service: GenerationMetricsService | None = None,
        observability_service: ObservabilityService | None = None,
        tracer: RuntimeTracer | None = None,
        usage_service: GenerationUsageService | None = None,
    ):
        self._registry = registry

        self._structured_output_registry = structured_output_registry

        self._validation_service = validation_service

        self._prompt_service = prompt_service

        self._routing_service = routing_service

        self._caching_service = caching_service

        self._guardrail_service = guardrail_service

        self._artifact_writer = artifact_writer
        """
        Optional (Artifact Platform PRD §24). When set, `generate()`
        persists every result via `GenerationArtifactBuilder` + this
        writer, gated by `_artifact_policy_service`. `None` skips
        persistence entirely -- matches how every other optional
        collaborator on this service degrades.
        """

        self._artifact_policy_service = artifact_policy_service

        self._acceptance_policy = acceptance_policy or AcceptancePolicy()

        self._fail_fast_policy = fail_fast_policy or FailFastPolicy()

        self._runtime_validation_policy = runtime_validation_policy or RuntimeValidationPolicy()

        self._metrics_service = metrics_service or GenerationMetricsService()
        """
        Unlike `artifact_writer`/`caching_service`/`guardrail_service`
        (opt-in, `None` skips them entirely), this always defaults to a
        real `GenerationMetricsService` -- its own `MetricsRecorder`
        collaborator defaults to `NoOpMetricsRecorder`, so recording is
        zero-cost/zero-risk (a structured log event, no I/O) and every
        `generate()` call gets metrics captured whether or not a caller
        wires a real recorder in.
        """

        self._observability_service = observability_service
        """
        Optional (AI Runtime Observability Platform PRD §8). When set,
        `generate()` persists a Generation Report + `ObservabilityArtifact`
        via this service after metrics recording, gated by its own
        artifact policy check. `None` skips it entirely -- same
        opt-in/no-I/O-by-default shape as `artifact_writer`, not the
        always-on shape `metrics_service` uses (this does real storage
        I/O, metrics recording doesn't).
        """

        self._tracer = tracer or NoOpTracer()
        """
        Always a real `RuntimeTracer` (PRD §11.1) -- defaults to
        `NoOpTracer`, which brackets nothing, so every `generate()` call
        behaves identically whether or not a real tracer (e.g.
        `LangSmithTracer`) is wired in. Same always-a-real-instance shape
        as `metrics_service`/`NoOpMetricsRecorder`.
        """

        self._usage_service = usage_service

    @property
    def registry(
        self,
    ) -> GenerationRegistry:
        """
        Exposes the provider registry this service was built with, so
        `StreamingService` (generation/streaming/create.py) can reuse the
        same registered provider instances instead of composing a second,
        duplicate registry.
        """

        return self._registry

    @property
    def metrics_service(
        self,
    ) -> GenerationMetricsService:
        """
        Exposes this service's `GenerationMetricsService`, so
        `StreamingService` records metrics through the same instance
        `generate()` uses rather than composing a second one.
        """

        return self._metrics_service

    @property
    def observability_service(
        self,
    ) -> ObservabilityService | None:
        """
        Exposes this service's `ObservabilityService` (may be `None`), so
        `StreamingService` persists observability artifacts through the
        same instance `generate()` uses rather than composing a second one.
        """

        return self._observability_service

    @property
    def tracer(
        self,
    ) -> RuntimeTracer:
        """
        Exposes this service's `RuntimeTracer`, so `StreamingService` traces
        through the same instance `generate()`/`_execute_once()` use rather
        than composing a second one.
        """

        return self._tracer

    # ==========================================================
    # Public
    # ==========================================================

    async def generate(
        self,
        *,
        request: GenerationRequest,
        provider: GenerationProvider | None = None,
    ) -> GenerationResult:
        """
        Generates against an explicit `provider`, or — when omitted —
        resolves one via the Routing Platform from
        `request.routing_strategy` (defaulting to `RoutingStrategy.AUTO`),
        trying the selected model and then each fallback in order until
        one succeeds. See `_generate_with_routing`.
        """

        logger.info(
            "generation.started",
            request_id=str(request.request_id),
            runtime=(request.runtime.value if request.runtime else None),
            provider=(provider.value if provider else None),
        )

        self._validate(
            request,
        )

        await self._enforce_fail_fast_input_validation(
            request,
        )

        await self._enforce_input_guardrails(
            request,
        )

        try:
            if provider is not None:
                result = await self._generate_with_provider(
                    provider=provider,
                    request=request,
                )
            else:
                result = await self._generate_with_routing(
                    request=request,
                )
        except GenerationError as exc:
            logger.error(
                "generation.failed",
                request_id=str(request.request_id),
                error_type=type(exc).__name__,
                error=str(exc),
            )
            raise

        snapshot = self._metrics_service.record(
            result,
        )

        if self._artifact_writer is not None:
            await self._persist_generation_artifact(
                request=request,
                result=result,
            )

        if self._observability_service is not None:
            await self._observability_service.record_generation(
                metrics=snapshot,
                artifact_runtime=(request.artifact_runtime or ArtifactRuntime.CHAT),
                session_id=request.session_id,
            )

        if self._usage_service is not None:
            await self._usage_service.record(result)

        return result

    async def stream_generate(
        self,
        *,
        request: GenerationRequest,
        provider: GenerationProvider | None = None,
    ) -> AsyncIterator[StreamChunk]:
        """
        Streaming counterpart to generate().

        Resolves a provider the same way generate() does -- an explicit
        `provider`, or otherwise the Routing Platform's top candidate for
        `request.routing_strategy` -- then yields directly from that
        provider's `stream()`. Unlike generate(), there is no regeneration
        loop and no automatic fallback to the next routing candidate on
        failure: once the first chunk has reached a caller, switching
        providers mid-stream isn't attempted.

        As an async generator, none of this runs until the caller starts
        iterating (same as every provider's own `stream()`), so
        validation/capability errors surface on the first `__anext__`,
        not on the call to `stream_generate()` itself.
        """

        self._validate(
            request,
        )

        await self._enforce_fail_fast_input_validation(
            request,
        )

        await self._enforce_input_guardrails(
            request,
        )

        resolved_provider = provider or self.resolve_streaming_provider(
            request,
        )

        generation_provider = self._registry.get(
            resolved_provider,
        )

        self._check_capability_support(
            provider=resolved_provider,
            generation_provider=generation_provider,
            request=request,
        )

        async for chunk in generation_provider.stream(
            request,
        ):
            yield chunk

    async def score_completed_stream(
        self,
        *,
        request: GenerationRequest,
        result: GenerationResult,
    ) -> GenerationResult:
        """
        Best-effort, informational-only validation/guardrail scoring for
        a stream that has already completed and reached the caller.

        `stream_generate()` only runs input guardrails before generation
        starts (see its own docstring) -- there is no regeneration loop,
        and once tokens have streamed out there is nothing left to block.
        This computes the same output-side scores `_execute_once()`
        records via `_enforce_generation_guardrails()`/`ValidationService.
        validate()`, purely so streamed generations carry the same
        `GenerationMetricsSnapshot.{validation_score,hallucination_score,
        runtime_score,guardrail_risk_score}` fields non-streamed ones do
        -- it can only ever attach information to a result the caller
        already has, never change what already happened. Unlike
        `_enforce_generation_guardrails()`, a `blocked=True` verdict here
        is recorded, not raised; unlike both callers in `_execute_once()`,
        a scoring failure itself is swallowed (logged) rather than
        propagated, since this runs after the client-facing work is done
        and must never turn a successful stream into a failed request.

        Caller: `StreamingService._stream_live()`, right after
        `_build_stream_result()` -- see streaming/service.py.
        """

        generation_provider = self._registry.get(
            result.provider,
        )

        if self._guardrail_service is not None:
            try:
                result.guardrails = await self._guardrail_service.evaluate(
                    request=request,
                    chunks=request.prompt_context.chunks,
                    result=result,
                    citations=request.prompt_context.citations,
                    run_id=result.generation_id,
                )
            except Exception:
                logger.warning(
                    "streaming.guardrails.scoring_failed",
                    request_id=str(request.request_id),
                    exc_info=True,
                )

        if self._validation_service is not None:
            try:
                result.validation = await self._validation_service.validate(
                    request=request,
                    result=result,
                    context=InputValidationContext(
                        context_window=generation_provider.config.context_window,
                        supports_streaming=generation_provider.capabilities.streaming,
                        supports_structured_output=(
                            generation_provider.capabilities.structured_output
                        ),
                        supports_json_mode=generation_provider.capabilities.json_mode,
                        supports_tool_calling=generation_provider.capabilities.tool_calling,
                    ),
                )
            except Exception:
                logger.warning(
                    "streaming.validation.scoring_failed",
                    request_id=str(request.request_id),
                    exc_info=True,
                )

        return result

    def resolve_streaming_provider(
        self,
        request: GenerationRequest,
    ) -> GenerationProvider:
        """
        Picks a provider via the Routing Platform for a streaming request
        with no explicit `provider`. Only the top candidate is used --
        streaming has no fallback loop, see `stream_generate`.

        Public (unlike the routing internals `generate()` uses) because
        `StreamingService` (generation/streaming/service.py) needs to know
        the resolved provider/model up front for cache-key derivation and
        statistics, before it starts consuming `stream_generate()`.
        """

        if self._routing_service is None:
            raise GenerationValidationError(
                "stream_generate() was called without a provider, which requires a "
                "RoutingService wired into this GenerationService (see "
                "generation/create.py) to resolve request.routing_strategy."
            )

        try:
            decision = self._routing_service.route(
                RoutingRequest(
                    strategy=request.routing_strategy or RoutingStrategy.AUTO,
                    required_capabilities=request.required_capabilities,
                )
            )
        except NoEligibleModelsError as exc:
            raise GenerationValidationError(
                str(exc),
            ) from exc

        if not self._registry.has(decision.selected_model.provider):
            raise GenerationProviderNotFoundError(
                f"Routed provider '{decision.selected_model.provider}' is not registered."
            )

        return decision.selected_model.provider

    async def _generate_with_routing(
        self,
        *,
        request: GenerationRequest,
    ) -> GenerationResult:

        if self._routing_service is None:
            raise GenerationValidationError(
                "generate() was called without a provider, which requires a "
                "RoutingService wired into this GenerationService (see "
                "generation/create.py) to resolve request.routing_strategy."
            )

        try:
            decision = self._routing_service.route(
                RoutingRequest(
                    strategy=request.routing_strategy or RoutingStrategy.AUTO,
                    required_capabilities=request.required_capabilities,
                )
            )
        except NoEligibleModelsError as exc:
            raise GenerationValidationError(
                str(exc),
            ) from exc

        candidates = [decision.selected_model, *decision.fallback_models]

        last_error: Exception | None = None

        for attempt, candidate in enumerate(candidates):
            if not self._registry.has(candidate.provider):
                logger.warning(
                    "generation.routing.candidate_not_registered",
                    provider=candidate.provider.value,
                    model=candidate.model_name,
                )
                continue

            try:
                result = await self._generate_with_provider(
                    provider=candidate.provider,
                    request=request,
                )
            except (GenerationExecutionError, GenerationProviderNotFoundError) as exc:
                last_error = exc

                logger.warning(
                    "generation.routing.candidate_failed",
                    provider=candidate.provider.value,
                    model=candidate.model_name,
                    error_type=type(exc).__name__,
                    error=str(exc),
                )
                continue

            if attempt > 0:
                logger.info(
                    "generation.routing.fallback_used",
                    strategy=decision.strategy.value,
                    selected_provider=decision.selected_model.provider.value,
                    used_provider=candidate.provider.value,
                    attempt=attempt + 1,
                )

            result.metadata["routing"] = self._routing_metadata(
                decision=decision,
                used_fallback=attempt > 0,
            )

            return result

        raise GenerationExecutionError(
            f"All routed candidate models failed for strategy '{decision.strategy.value}'."
        ) from last_error

    @staticmethod
    def _routing_metadata(
        *,
        decision: RoutingDecision,
        used_fallback: bool,
    ) -> dict[str, Any]:

        return {
            "strategy": decision.strategy.value,
            "selected_provider": decision.selected_model.provider.value,
            "selected_model": decision.selected_model.model_name,
            "score": decision.score,
            "reasons": decision.reasons,
            "used_fallback": used_fallback,
        }

    async def _generate_with_provider(
        self,
        *,
        provider: GenerationProvider,
        request: GenerationRequest,
    ) -> GenerationResult:

        generation_provider = self._registry.get(
            provider,
        )

        if self._caching_service is not None:
            cache_result = await self._caching_service.lookup(
                request=request,
                provider=provider,
                model=generation_provider.config.model_name,
                routing_strategy=request.routing_strategy,
            )

            if cache_result.hit:
                return self._apply_cache_hit(
                    cache_result,
                )

        self._check_capability_support(
            provider=provider,
            generation_provider=generation_provider,
            request=request,
        )

        result = await self._execute_once(
            provider=provider,
            generation_provider=generation_provider,
            request=request,
        )

        #
        # Regeneration (opt-in via request.max_regeneration_attempts).
        #
        # Re-calls the provider, appending corrective feedback about
        # what was wrong, when the attempt's output failed to parse or
        # failed validation. Each attempt is independent — corrective
        # feedback always describes the *latest* failure, not an
        # accumulation of every prior one.
        #

        attempt = 0

        while attempt < request.max_regeneration_attempts and self._needs_regeneration(
            request=request,
            result=result,
        ):
            attempt += 1

            corrected_request = self._build_corrected_request(
                request,
                result,
            )

            logger.warning(
                "generation.regeneration.attempting",
                provider=provider.value,
                attempt=attempt,
                max_attempts=request.max_regeneration_attempts,
            )

            result = await self._execute_once(
                provider=provider,
                generation_provider=generation_provider,
                request=corrected_request,
            )

            result.regeneration_attempts = attempt

        if request.max_regeneration_attempts and self._needs_regeneration(
            request=request,
            result=result,
        ):
            logger.warning(
                "generation.regeneration.exhausted",
                provider=provider.value,
                attempts=attempt,
            )

        logger.info(
            "generation.completed",
            provider=provider.value,
            model=result.model,
            latency_ms=result.statistics.latency_ms,
            prompt_tokens=result.statistics.prompt_tokens,
            completion_tokens=result.statistics.completion_tokens,
            total_tokens=result.statistics.total_tokens,
            regeneration_attempts=result.regeneration_attempts,
        )

        if self._caching_service is not None:
            result.metadata["cache"] = {
                "hit": False,
                "level": None,
            }

            await self._caching_service.store(
                request=request,
                provider=provider,
                model=generation_provider.config.model_name,
                routing_strategy=request.routing_strategy,
                result=result,
            )

        return result

    @staticmethod
    def _apply_cache_hit(
        cache_result: CacheResult,
    ) -> GenerationResult:
        """
        Returns a cached `GenerationResult` as if it were a fresh
        response: a new `generation_id` (so repeated hits are
        individually traceable) and `metadata["cache"]` populated per
        the Runtime Caching Platform's artifact schema (ADR-027). The
        original `execution`/`statistics` are carried over as-is — they
        describe the generation that actually happened, not this reuse.
        """

        cached = cache_result.generation_result

        assert cached is not None

        return cached.model_copy(
            update={
                "generation_id": uuid4(),
                "metadata": {
                    **cached.metadata,
                    "cache": {
                        "hit": True,
                        "level": (cache_result.level.value if cache_result.level else None),
                        "tokens_saved": cached.statistics.total_tokens,
                        "cost_saved": cached.statistics.estimated_cost_usd,
                    },
                },
            },
        )

    async def generate_from_template(
        self,
        *,
        provider: GenerationProvider,
        template_name: str,
        variables: dict[str, Any],
        prompt_context: PromptContext,
        version: str | None = None,
        examples: list[dict[str, Any]] | None = None,
        output_model: type[BaseModel] | None = None,
        output_schema: dict[str, Any] | None = None,
        response_format: ResponseFormat | None = None,
        temperature: float | None = None,
        max_tokens: int | None = None,
        tools: list[ToolDefinition] | None = None,
        max_regeneration_attempts: int | None = None,
    ) -> GenerationResult:
        """
        Prompt Platform → Generation Platform bridge.

        Renders a named `PromptTemplate` (via `PromptService` —
        `generation/prompts/`) into messages, flattens them into the flat
        `system_prompt`/`user_prompt` strings `GenerationRequest` carries,
        and — when `output_model` is set — appends schema-aware format
        instructions (`PydanticOutputParser.get_format_instructions()`,
        e.g. "You MUST respond using this schema...") before calling
        `generate()`.

        These format instructions reinforce, not replace, native provider
        structured output (`output_config.format` / `response_format` /
        `response_json_schema` — see `providers/helpers/structured.py`):
        both apply. Rendering happens before a provider is selected, so
        there's no way to skip the prompt-level instruction only for
        providers with reliable native enforcement.
        """

        if self._prompt_service is None:
            raise GenerationValidationError(
                "generate_from_template() requires a PromptService — none "
                "was wired into this GenerationService (see "
                "generation/create.py)."
            )

        messages = await self._prompt_service.render_messages(
            PromptRenderRequest(
                template_name=template_name,
                version=version,
                variables=variables,
                examples=examples or [],
            ),
        )

        system_prompt, user_prompt = self._split_rendered_messages(
            messages,
        )

        if output_model is not None:
            system_prompt = self._append_format_instructions(
                system_prompt,
                output_model,
            )

        request_kwargs: dict[str, Any] = {
            "prompt_context": prompt_context,
            "user_prompt": user_prompt,
            "system_prompt": system_prompt,
            "response_format": (
                response_format
                or (ResponseFormat.STRUCTURED if output_model else ResponseFormat.TEXT)
            ),
            "output_model": output_model,
            "output_schema": output_schema,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "tools": tools or [],
        }

        if max_regeneration_attempts is not None:
            request_kwargs["max_regeneration_attempts"] = max_regeneration_attempts

        request = GenerationRequest(
            **request_kwargs,
        )

        return await self.generate(
            provider=provider,
            request=request,
        )

    @staticmethod
    def _split_rendered_messages(
        messages: list[BaseMessage],
    ) -> tuple[str | None, str]:
        """
        `GenerationRequest` only carries flat `system_prompt`/`user_prompt`
        strings, not a full message list, so a rendered `ChatPromptTemplate`
        (system message + few-shot examples + human message) is flattened:
        `SystemMessage` content becomes `system_prompt`; everything else
        (few-shot pairs, role-labeled, plus the final human message)
        becomes `user_prompt`.
        """

        system_parts: list[str] = []

        user_parts: list[str] = []

        for message in messages:
            content = str(message.content) if message.content else ""

            if not content:
                continue

            if isinstance(message, SystemMessage):
                system_parts.append(content)
            elif isinstance(message, AIMessage):
                user_parts.append(f"Assistant: {content}")
            else:
                user_parts.append(content)

        system_prompt = "\n\n".join(system_parts) if system_parts else None

        user_prompt = "\n\n".join(user_parts)

        return system_prompt, user_prompt

    @staticmethod
    def _append_format_instructions(
        system_prompt: str | None,
        output_model: type[BaseModel],
    ) -> str:

        format_instructions = PydanticOutputParser(
            pydantic_object=output_model,
        ).get_format_instructions()

        return f"{system_prompt}\n\n{format_instructions}" if system_prompt else format_instructions

    # ==========================================================
    # Single Attempt
    # ==========================================================

    async def _execute_once(
        self,
        *,
        provider: GenerationProvider,
        generation_provider: GenerationProviderInterface,
        request: GenerationRequest,
    ) -> GenerationResult:
        """
        One provider call plus the full structured-output post-processing
        pipeline: native/registry parsing, output_model validation, and
        ValidationService checks. No retry logic lives here — `generate()`
        owns the regeneration loop and calls this once per attempt.
        """

        logger.info(
            "generation.requested",
            provider=provider.value,
            prompt_strategy=request.prompt_strategy.value,
            response_format=request.response_format.value,
        )

        logger.info(
            "provider.started",
            provider=provider.value,
            model=generation_provider.config.model_name,
        )

        try:
            with self._tracer.trace(
                name="generation",
                inputs={"prompt": request.user_prompt},
                tags={
                    "provider": provider.value,
                    "model": generation_provider.config.model_name,
                    "runtime": (request.runtime.value if request.runtime else None),
                },
            ) as trace_handle:
                result = (
                    await generation_provider.generate_structured(
                        request,
                    )
                    if self._is_structured_request(
                        request,
                    )
                    else await generation_provider.generate(
                        request,
                    )
                )

                trace_handle.set_output(
                    content=result.content,
                    prompt_tokens=result.statistics.prompt_tokens,
                    completion_tokens=result.statistics.completion_tokens,
                    total_tokens=result.statistics.total_tokens,
                )
        except GenerationError:
            raise
        except Exception as exc:
            logger.error(
                "generation.unexpected_error",
                provider=provider.value,
                error_type=type(exc).__name__,
                error=str(exc),
            )
            raise GenerationExecutionError(
                f"Generation failed unexpectedly for provider '{provider}'."
            ) from exc

        logger.info(
            "provider.completed",
            provider=provider.value,
            model=result.model,
            latency_ms=result.statistics.latency_ms,
        )

        if request.response_format in _REGISTRY_PARSED_FORMATS:
            await self._parse_via_registry(
                request=request,
                result=result,
            )

        if request.output_model is not None:
            self._validate_parsed_output(
                request=request,
                result=result,
            )

        if self._guardrail_service is not None:
            await self._enforce_generation_guardrails(
                request=request,
                result=result,
            )

        if self._validation_service is not None:
            result.validation = await self._validation_service.validate(
                request=request,
                result=result,
                context=InputValidationContext(
                    context_window=generation_provider.config.context_window,
                    supports_streaming=generation_provider.capabilities.streaming,
                    supports_structured_output=generation_provider.capabilities.structured_output,
                    supports_json_mode=generation_provider.capabilities.json_mode,
                    supports_tool_calling=generation_provider.capabilities.tool_calling,
                ),
            )

            if not result.validation.valid:
                logger.warning(
                    "generation.validation.failed",
                    provider=provider.value,
                    issues=[issue.model_dump() for issue in result.validation.issues],
                )

        return result

    @staticmethod
    def _is_structured_request(
        request: GenerationRequest,
    ) -> bool:
        """
        Structured requests (a schema, or an explicit structured/JSON
        response format) are routed through generate_structured() so
        providers can apply native schema-constrained decoding.
        """

        return request.output_schema is not None or request.response_format in (
            ResponseFormat.JSON,
            ResponseFormat.STRUCTURED,
        )

    @classmethod
    def _check_capability_support(
        cls,
        *,
        provider: GenerationProvider,
        generation_provider: GenerationProviderInterface,
        request: GenerationRequest,
    ) -> None:
        """
        Capability guard (Provider Capability Flags).

        `ProviderCapabilities` (`generation/models.py`) and the matching
        `supports_*` accessors on `GenerationProviderInterface` already
        exist — this makes them observable. It never blocks the call:
        capability flags are self-reported and every provider already
        degrades gracefully when a feature isn't natively supported
        (e.g. Claude falls back to prompt-enforced JSON without a
        schema). This only logs so a silent degradation is visible
        instead of a caller wondering why a "structured" request came
        back unparsed.
        """

        missing_capabilities: list[str] = []

        if (
            cls._is_structured_request(
                request,
            )
            and not generation_provider.supports_structured_output()
        ):
            missing_capabilities.append(
                "structured_output",
            )

        if (
            request.response_format == ResponseFormat.JSON
            and not generation_provider.supports_json_mode()
        ):
            missing_capabilities.append(
                "json_mode",
            )

        if request.tools and not generation_provider.supports_tools():
            missing_capabilities.append(
                "tool_calling",
            )

        if missing_capabilities:
            logger.warning(
                "generation.capability_mismatch",
                provider=provider.value,
                missing_capabilities=missing_capabilities,
            )

    # ==========================================================
    # Regeneration
    # ==========================================================

    def _needs_regeneration(
        self,
        *,
        request: GenerationRequest,
        result: GenerationResult,
    ) -> bool:
        """
        Delegates the accept/reject/regenerate call to `AcceptancePolicy`
        (PRD "Validation Policy Layer") rather than hard-coding it here.

        Default behavior is unchanged from before the policy layer
        existed: only a structured-request parse failure or an
        output-stage validation failure trigger regeneration.
        Input-stage issues (token budget, missing capability, ...)
        describe the request itself, and re-calling the provider with
        the same request (plus a corrective note) wouldn't fix them —
        it could even make a token-budget overflow worse — so
        `AcceptancePolicy.reject_on_input_invalid` defaults to `False`.
        Hallucination-stage issues are WARNING-only heuristics (see
        HallucinationValidator) and never flip `valid` to `False` on
        their own, so they never reach this decision either way.

        A failed runtime-stage contract additionally gates regeneration
        only when `RuntimeValidationPolicy.block_on_error` is opted in
        (defaults to `False` — see that policy's docstring for why).
        """

        parsed_output_missing = (
            self._is_structured_request(
                request,
            )
            and result.parsed_output is None
        )

        decision = self._acceptance_policy.decide(
            report=result.validation,
            parsed_output_missing=parsed_output_missing,
        )

        if decision == AcceptanceDecision.REGENERATE:
            return True

        runtime_validation = result.validation.runtime_validation if result.validation else None

        return runtime_validation is not None and self._runtime_validation_policy.should_block(
            runtime_validation,
        )

    @classmethod
    def _build_corrected_request(
        cls,
        request: GenerationRequest,
        result: GenerationResult,
    ) -> GenerationRequest:

        correction = cls._build_correction_message(
            request,
            result,
        )

        corrected_system_prompt = (
            f"{request.system_prompt}\n\n{correction}" if request.system_prompt else correction
        )

        return request.model_copy(
            update={
                "system_prompt": corrected_system_prompt,
            },
        )

    @classmethod
    def _build_correction_message(
        cls,
        request: GenerationRequest,
        result: GenerationResult,
    ) -> str:
        """
        Combines guidance from every applicable signal rather than picking
        one — a structured request with no parsed_output always gets the
        JSON-formatting instruction, and any validation errors (which can
        fire independently of parsing, e.g. a fabricated citation on a
        plain-text answer) are always appended on top.
        """

        parts: list[str] = []

        if (
            cls._is_structured_request(
                request,
            )
            and result.parsed_output is None
        ):
            parts.append(
                "Your previous response could not be parsed as valid JSON. "
                "Return ONLY valid JSON matching the requested schema — "
                "no markdown code fences, no commentary, no extra text "
                "before or after the JSON."
            )

        if result.validation is not None and not result.validation.output_validation.valid:
            error_messages = "; ".join(
                f"[{issue.validator}] {issue.message}"
                for issue in result.validation.output_validation.issues
                if issue.severity == ValidationSeverity.ERROR
            )

            if error_messages:
                parts.append(
                    "Your previous response did not pass validation: "
                    f"{error_messages}. Correct these issues and respond "
                    "again — match the requested schema exactly, and only "
                    "cite sources present in the provided context."
                )

        if parts:
            return " ".join(
                parts,
            )

        return "Your previous response was invalid. Please try again."

    # ==========================================================
    # Structured Output Helpers
    # ==========================================================

    async def _parse_via_registry(
        self,
        *,
        request: GenerationRequest,
        result: GenerationResult,
    ) -> None:
        """
        Populates `result.parsed_output` for response formats with no
        provider-native structured decoding (Markdown, XML) by running
        `result.content` through the matching Structured Output Platform
        parser.

        Best effort: an unregistered parser, or content that fails to
        parse (e.g. the model didn't actually emit XML), is logged and
        leaves `parsed_output` unset rather than failing the generation.
        """

        if self._structured_output_registry is None:
            logger.warning(
                "generation.structured_output.registry_unavailable",
                response_format=request.response_format.value,
            )
            return

        output_format = _REGISTRY_PARSED_FORMATS[request.response_format]

        try:
            parser = self._structured_output_registry.get(
                output_format,
            )

            result.parsed_output = await parser.parse(
                result.content,
            )
        except Exception as exc:
            logger.warning(
                "generation.structured_output.registry_parse_failed",
                response_format=request.response_format.value,
                error_type=type(exc).__name__,
                error=str(exc),
            )

    @staticmethod
    def _validate_parsed_output(
        *,
        request: GenerationRequest,
        result: GenerationResult,
    ) -> None:
        """
        Validates `result.parsed_output` (a dict produced by native
        structured output or the parser-repair fallback) back into an
        instance of `request.output_model`.

        Best effort: a model that drifted from the schema is logged and
        left as the raw dict rather than failing the whole generation.
        """

        assert request.output_model is not None

        if not isinstance(result.parsed_output, dict):
            logger.warning(
                "generation.structured_output.validation_skipped",
                output_model=request.output_model.__name__,
                reason="parsed_output_missing_or_not_a_dict",
            )
            return

        try:
            result.parsed_output = request.output_model.model_validate(
                result.parsed_output,
            )
        except Exception as exc:
            logger.warning(
                "generation.structured_output.validation_failed",
                output_model=request.output_model.__name__,
                error_type=type(exc).__name__,
                error=str(exc),
            )

    # ==========================================================
    # Validation Policy
    # ==========================================================

    async def _enforce_fail_fast_input_validation(
        self,
        request: GenerationRequest,
    ) -> None:
        """
        Runs input-stage validation up front -- before guardrails,
        routing, or any provider call -- so a request already known to
        be invalid never pays for any of that work (PRD "Full Generation
        Flow Activation": Input Validation precedes Provider Execution).

        Called with no provider-specific `InputValidationContext` (the
        provider isn't resolved yet at this point in `generate()`/
        `stream_generate()`), so only provider-agnostic checks
        (`EmptyPromptValidator`, `ContextValidator`) can meaningfully
        fire here; `TokenBudgetValidator`/`ProviderLimitsValidator` no-op
        without a context window and run for real later, inside
        `_execute_once`'s full `ValidationService.validate()` call, once
        a provider is known. Re-running `validate_input()` there is
        intentional, not duplicate logic -- mirrors how
        `_enforce_generation_guardrails` re-runs `evaluate_input()`.
        """

        if self._validation_service is None:
            return

        input_result = await self._validation_service.validate_input(
            request,
        )

        if self._fail_fast_policy.should_stop(input_result):
            raise GenerationValidationError(
                f"Input failed validation: "
                f"{'; '.join(issue.message for issue in input_result.issues)}"
            )

    # ==========================================================
    # Guardrails
    # ==========================================================

    async def _enforce_input_guardrails(
        self,
        request: GenerationRequest,
    ) -> None:
        """
        PRD (guardrail_integration_prd.md) §7 "Input Guardrails": runs
        before the provider is invoked at all, once per top-level
        `generate()`/`stream_generate()` call (not per regeneration
        attempt -- those re-check the corrected prompt themselves via
        `_enforce_generation_guardrails`'s full `evaluate()` call below).
        A blocked result terminates generation immediately.
        """

        if self._guardrail_service is None:
            return

        input_result = await self._guardrail_service.evaluate_input(
            request,
        )

        if input_result.blocked:
            raise GuardrailViolationError(
                f"Input blocked by guardrails: "
                f"{'; '.join(issue.message for issue in input_result.issues)}"
            )

    async def _enforce_generation_guardrails(
        self,
        *,
        request: GenerationRequest,
        result: GenerationResult,
    ) -> None:
        """
        PRD §7 "Generation Guardrails": runs immediately after a
        provider result (and its structured-output post-processing) is
        available, before `ValidationService`. Reuses the platform's own
        full `evaluate()` (input + retrieval + generation) rather than
        calling `evaluate_generation()` alone, since `request.prompt_context`
        already carries whatever chunks/citations were retrieved --
        `GenerationResult.guardrails` (PRD §10) is meant to be the
        complete multi-stage report, not just this stage. Re-running
        `evaluate_input()` here is intentional, not duplicate logic: every
        input guardrail is a pure/stateless check (see e.g.
        `input/rate_limit.py`), and a regeneration attempt's corrected
        `system_prompt` deserves its own check.
        """

        assert self._guardrail_service is not None

        result.guardrails = await self._guardrail_service.evaluate(
            request=request,
            chunks=request.prompt_context.chunks,
            result=result,
            citations=request.prompt_context.citations,
            run_id=result.generation_id,
        )

        if result.guardrails.blocked:
            raise GuardrailViolationError(
                f"Generation blocked by guardrails: "
                f"{'; '.join(issue.message for issue in result.guardrails.issues)}"
            )

    async def _persist_generation_artifact(
        self,
        *,
        request: GenerationRequest,
        result: GenerationResult,
    ) -> None:
        """
        Best-effort (Artifact Platform PRD §24): a storage hiccup while
        persisting the artifact must not fail a generation that already
        succeeded -- `GenerationArtifactWriter.write()` itself re-raises
        on failure (see its own logging), so that's caught and downgraded
        to an `artifacts.generation.failed` event here instead of
        propagating. Mirrors `GuardrailService._persist_artifact`.
        """

        assert self._artifact_writer is not None

        artifact_runtime = request.artifact_runtime or ArtifactRuntime.CHAT

        if self._artifact_policy_service is not None and not (
            self._artifact_policy_service.should_persist(
                artifact_runtime,
                ArtifactCategory.GENERATION,
            )
        ):
            logger.debug(
                "artifacts.generation.skipped",
                generation_id=str(result.generation_id),
                runtime=artifact_runtime.value,
            )
            return

        try:
            artifact = GenerationArtifactBuilder().build(
                result=result,
            )

            await self._artifact_writer.write(
                artifact,
            )
        except Exception as exc:
            logger.warning(
                "artifacts.generation.failed",
                generation_id=str(result.generation_id),
                reason="artifact_persistence_failed",
                error_type=type(exc).__name__,
                error=str(exc),
            )

    @staticmethod
    def _validate(
        request: GenerationRequest,
    ) -> None:
        """
        `prompt_context.context` is deliberately not required to be
        non-empty here: it's optional, assembled material (retrieved
        chunks, injected memory) layered on top of `user_prompt`, which
        is already required below. A user's message with no retrieval
        hits and no prior memory -- a brand-new account, an ungrounded
        chat question -- is a normal, common case, not an error;
        `ContextValidator` (`validation/input/context_validation.py`)
        already covers empty/duplicate/orphaned *chunks* as WARNINGs
        rather than a hard block, and this used to duplicate that at a
        stricter level for the one case (`context == ""`) that isn't
        even chunk-shaped.
        """

        if not request.user_prompt.strip():
            logger.warning(
                "generation.validation_failed",
                reason="empty_user_prompt",
            )
            raise (GenerationValidationError("Prompt cannot be empty."))
