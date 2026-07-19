"""
Unit tests for GenerationService.

Covers:
- Successful delegation to the resolved provider
- Validation failure for an empty user prompt
- Validation failure for empty prompt context
- Provider resolution failure propagates from the registry
- GenerationError subclasses raised by a provider propagate unchanged
- Unexpected (non-domain) exceptions raised by a provider are wrapped in
  GenerationExecutionError
- ValidationService integration: the report lands on result.validation,
  and only output-stage failures (not input-stage ones) trigger the
  regeneration loop
- GuardrailService integration (guardrail_integration_prd.md): a blocked
  input guardrail raises before the provider is ever called; a blocked
  generation guardrail raises after the provider ran but before
  ValidationService; an allowed run attaches the full GuardrailReport to
  result.guardrails; no GuardrailService wired leaves it None
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest
from app.ai.guardrails.enums import GuardrailCategory, GuardrailSeverity
from app.ai.guardrails.interfaces import (
    GenerationGuardrailInterface,
    InputGuardrailInterface,
)
from app.ai.guardrails.models import GuardrailIssue
from app.ai.guardrails.registry import GuardrailRegistry
from app.ai.guardrails.service import GuardrailService
from app.ai.knowledge.context.models import PromptContext
from app.ai.runtime.generation.catalog.models import ModelMetadata
from app.ai.runtime.generation.enums import GenerationProvider
from app.ai.runtime.generation.exceptions import (
    GenerationExecutionError,
    GenerationProviderNotFoundError,
    GenerationValidationError,
    GuardrailViolationError,
)
from app.ai.runtime.generation.models import (
    GenerationExecution,
    GenerationRequest,
    GenerationResult,
    GenerationStatistics,
    ProviderCapabilities,
    StreamChunk,
    StreamEventType,
)
from app.ai.runtime.generation.observability.service import GenerationMetricsService
from app.ai.runtime.generation.policies.fail_fast import FailFastPolicy
from app.ai.runtime.generation.policies.runtime import RuntimeValidationPolicy
from app.ai.runtime.generation.registry import GenerationRegistry
from app.ai.runtime.generation.routing.enums import RoutingStrategy
from app.ai.runtime.generation.routing.exceptions import NoEligibleModelsError
from app.ai.runtime.generation.routing.models import RoutingDecision
from app.ai.runtime.generation.service import GenerationService
from app.ai.runtime.generation.validation.models import (
    ValidationIssue,
    ValidationReport,
    ValidationResult,
    ValidationSeverity,
)


def _make_context(text: str = "some retrieved context") -> PromptContext:
    return PromptContext(context=text, chunks=[])


def _make_request(
    user_prompt: str = "hello",
    context: str = "some retrieved context",
) -> GenerationRequest:
    return GenerationRequest(
        prompt_context=_make_context(context),
        user_prompt=user_prompt,
    )


def _make_result(request: GenerationRequest) -> GenerationResult:
    return GenerationResult(
        request=request,
        execution=GenerationExecution(),
        statistics=GenerationStatistics(
            provider=GenerationProvider.GROQ,
            model="test-model",
        ),
        provider=GenerationProvider.GROQ,
        model="test-model",
        content="hello world",
    )


def _make_provider(provider: GenerationProvider = GenerationProvider.GROQ) -> AsyncMock:
    fake = AsyncMock()
    fake.provider = provider
    return fake


async def test_generate_delegates_to_the_resolved_provider() -> None:
    request = _make_request()
    result = _make_result(request)

    provider = _make_provider()
    provider.generate = AsyncMock(return_value=result)

    registry = GenerationRegistry(providers=[provider])
    service = GenerationService(registry=registry)

    returned = await service.generate(provider=GenerationProvider.GROQ, request=request)

    assert returned is result
    provider.generate.assert_awaited_once_with(request)


async def test_generate_records_owner_scoped_usage_after_completion() -> None:
    request = _make_request()
    request.owner_id = uuid4()
    result = _make_result(request)
    provider = _make_provider()
    provider.generate = AsyncMock(return_value=result)
    usage_service = AsyncMock()

    service = GenerationService(
        registry=GenerationRegistry(providers=[provider]),
        usage_service=usage_service,
    )

    await service.generate(provider=GenerationProvider.GROQ, request=request)

    usage_service.record.assert_awaited_once_with(result)


async def test_generate_raises_validation_error_for_empty_user_prompt() -> None:
    provider = _make_provider()
    registry = GenerationRegistry(providers=[provider])
    service = GenerationService(registry=registry)

    request = _make_request(user_prompt="   ")

    with pytest.raises(GenerationValidationError, match="empty"):
        await service.generate(provider=GenerationProvider.GROQ, request=request)

    provider.generate.assert_not_awaited()


async def test_generate_allows_empty_prompt_context() -> None:
    """
    `prompt_context.context` being empty must not be rejected --
    chat.py legitimately builds this shape (no retrieval wired yet,
    optionally memory-only context) and relies on `user_prompt` alone
    being a valid, complete request. This used to raise
    `GenerationValidationError`, which made every `/chat/stream` and
    `/chat/ws` call fail unconditionally; `_validate()` now only
    requires a non-empty `user_prompt`.
    """
    request = _make_request(context="")
    result = _make_result(request)

    provider = _make_provider()
    provider.generate = AsyncMock(return_value=result)

    registry = GenerationRegistry(providers=[provider])
    service = GenerationService(registry=registry)

    returned = await service.generate(provider=GenerationProvider.GROQ, request=request)

    assert returned is result
    provider.generate.assert_awaited_once_with(request)


async def test_generate_raises_provider_not_found_error_when_unregistered() -> None:
    service = GenerationService(registry=GenerationRegistry(providers=[]))

    with pytest.raises(GenerationProviderNotFoundError):
        await service.generate(provider=GenerationProvider.GROQ, request=_make_request())


async def test_generate_propagates_generation_error_subclasses_unchanged() -> None:
    provider = _make_provider()
    provider.generate = AsyncMock(side_effect=GuardrailViolationError("blocked"))

    registry = GenerationRegistry(providers=[provider])
    service = GenerationService(registry=registry)

    with pytest.raises(GuardrailViolationError, match="blocked"):
        await service.generate(provider=GenerationProvider.GROQ, request=_make_request())


async def test_generate_wraps_unexpected_exceptions_in_execution_error() -> None:
    provider = _make_provider()
    provider.generate = AsyncMock(side_effect=RuntimeError("sdk exploded"))

    registry = GenerationRegistry(providers=[provider])
    service = GenerationService(registry=registry)

    with pytest.raises(GenerationExecutionError) as exc_info:
        await service.generate(provider=GenerationProvider.GROQ, request=_make_request())

    assert isinstance(exc_info.value.__cause__, RuntimeError)
    assert str(exc_info.value.__cause__) == "sdk exploded"


async def test_generate_id_uses_the_provider_argument_not_the_result_provider() -> None:
    """
    The service resolves the provider from the registry using the
    `provider` argument; a mismatched `GenerationResult.provider` on the
    returned object should not affect which provider is looked up.
    """

    request = _make_request()
    result = _make_result(request)

    groq_provider = _make_provider(GenerationProvider.GROQ)
    groq_provider.generate = AsyncMock(return_value=result)

    other_provider = _make_provider(GenerationProvider.OPENAI)
    other_provider.generate = AsyncMock(return_value=result)

    registry = GenerationRegistry(providers=[groq_provider, other_provider])
    service = GenerationService(registry=registry)

    await service.generate(provider=GenerationProvider.OPENAI, request=request)

    other_provider.generate.assert_awaited_once()
    groq_provider.generate.assert_not_awaited()


# ==========================================================
# ValidationService integration
# ==========================================================


def _make_capable_provider(provider: GenerationProvider = GenerationProvider.GROQ) -> AsyncMock:
    """
    Like `_make_provider`, but with real (non-Mock) `capabilities` and
    `config.context_window` values, since `_execute_once` now reads
    both to build an `InputValidationContext` whenever a
    `ValidationService` is wired in.
    """

    fake = _make_provider(provider)
    fake.capabilities = ProviderCapabilities()
    fake.config.context_window = 100_000
    return fake


def _make_validation_service(report: ValidationReport) -> AsyncMock:
    service = AsyncMock()
    service.validate = AsyncMock(return_value=report)
    return service


def _valid_result() -> ValidationResult:
    return ValidationResult(valid=True)


def _failing_output_result() -> ValidationResult:
    return ValidationResult(
        valid=False,
        issues=[
            ValidationIssue(
                validator="schema",
                severity=ValidationSeverity.ERROR,
                message="parsed_output does not match schema",
            )
        ],
    )


def _failing_input_result() -> ValidationResult:
    return ValidationResult(
        valid=False,
        issues=[
            ValidationIssue(
                validator="token_budget",
                severity=ValidationSeverity.ERROR,
                message="estimated tokens exceed the context window",
            )
        ],
    )


async def test_generate_populates_result_validation_from_the_report() -> None:
    request = _make_request()
    result = _make_result(request)

    provider = _make_capable_provider()
    provider.generate = AsyncMock(return_value=result)

    report = ValidationReport(
        input_validation=_valid_result(),
        output_validation=_valid_result(),
        hallucination_validation=_valid_result(),
        valid=True,
    )

    registry = GenerationRegistry(providers=[provider])
    service = GenerationService(
        registry=registry,
        validation_service=_make_validation_service(report),
    )

    returned = await service.generate(provider=GenerationProvider.GROQ, request=request)

    assert returned.validation is report


async def test_generate_does_not_regenerate_on_input_only_validation_failure() -> None:
    """
    An input-stage failure (e.g. token budget) describes the request,
    not the response -- regenerating with the same request plus a
    corrective note appended wouldn't fix it, so it must not trigger
    the regeneration loop.
    """

    request = _make_request()
    result = _make_result(request)
    request.max_regeneration_attempts = 2

    provider = _make_capable_provider()
    provider.generate = AsyncMock(return_value=result)

    report = ValidationReport(
        input_validation=_failing_input_result(),
        output_validation=_valid_result(),
        hallucination_validation=_valid_result(),
        valid=False,
    )

    registry = GenerationRegistry(providers=[provider])
    service = GenerationService(
        registry=registry,
        validation_service=_make_validation_service(report),
    )

    await service.generate(provider=GenerationProvider.GROQ, request=request)

    provider.generate.assert_awaited_once()


async def test_generate_regenerates_on_output_stage_validation_failure() -> None:
    request = _make_request()
    request.max_regeneration_attempts = 2
    result = _make_result(request)

    provider = _make_capable_provider()
    provider.generate = AsyncMock(return_value=result)

    failing_report = ValidationReport(
        input_validation=_valid_result(),
        output_validation=_failing_output_result(),
        hallucination_validation=_valid_result(),
        valid=False,
    )

    registry = GenerationRegistry(providers=[provider])
    service = GenerationService(
        registry=registry,
        validation_service=_make_validation_service(failing_report),
    )

    await service.generate(provider=GenerationProvider.GROQ, request=request)

    # Exhausts every attempt (1 initial + 2 regenerations) since the
    # fake ValidationService always returns the same failing report.
    assert provider.generate.await_count == 3


# ==========================================================
# Routing integration (generate() called without a provider)
# ==========================================================


def _make_model(
    model_name: str,
    provider: GenerationProvider = GenerationProvider.GROQ,
) -> ModelMetadata:
    return ModelMetadata(
        provider=provider,
        model_name=model_name,
        display_name=model_name,
        context_window=100_000,
        capabilities=ProviderCapabilities(),
    )


def _make_decision(
    *,
    selected: ModelMetadata,
    fallbacks: list[ModelMetadata] | None = None,
    strategy: RoutingStrategy = RoutingStrategy.AUTO,
) -> RoutingDecision:
    return RoutingDecision(
        request_id=uuid4(),
        strategy=strategy,
        selected_model=selected,
        fallback_models=fallbacks or [],
        score=8.5,
        reasons=["highest quality score"],
    )


def _make_routing_service(decision: RoutingDecision) -> MagicMock:
    routing_service = MagicMock()
    routing_service.route = MagicMock(return_value=decision)
    return routing_service


async def test_generate_without_provider_routes_to_the_selected_model() -> None:
    request = _make_request()
    result = _make_result(request)

    provider = _make_provider(GenerationProvider.GROQ)
    provider.generate = AsyncMock(return_value=result)

    selected = _make_model("llama-3.3-70b-versatile", GenerationProvider.GROQ)
    decision = _make_decision(selected=selected)

    registry = GenerationRegistry(providers=[provider])
    service = GenerationService(
        registry=registry,
        routing_service=_make_routing_service(decision),
    )

    returned = await service.generate(request=request)

    assert returned is result
    provider.generate.assert_awaited_once()
    assert returned.metadata["routing"]["selected_provider"] == "groq"
    assert returned.metadata["routing"]["used_fallback"] is False


async def test_generate_without_provider_raises_when_no_routing_service_wired() -> None:
    registry = GenerationRegistry(providers=[])
    service = GenerationService(registry=registry)

    with pytest.raises(GenerationValidationError, match="RoutingService"):
        await service.generate(request=_make_request())


async def test_generate_without_provider_defaults_routing_strategy_to_auto() -> None:
    request = _make_request()
    result = _make_result(request)

    provider = _make_provider(GenerationProvider.GROQ)
    provider.generate = AsyncMock(return_value=result)

    selected = _make_model("llama-3.3-70b-versatile", GenerationProvider.GROQ)
    routing_service = _make_routing_service(_make_decision(selected=selected))

    registry = GenerationRegistry(providers=[provider])
    service = GenerationService(registry=registry, routing_service=routing_service)

    assert request.routing_strategy is None

    await service.generate(request=request)

    passed_request = routing_service.route.call_args.args[0]
    assert passed_request.strategy == RoutingStrategy.AUTO


async def test_generate_falls_back_to_the_next_candidate_on_execution_failure() -> None:
    request = _make_request()
    result = _make_result(request)

    failing_provider = _make_provider(GenerationProvider.CLAUDE)
    failing_provider.generate = AsyncMock(side_effect=GenerationExecutionError("down"))

    healthy_provider = _make_provider(GenerationProvider.GROQ)
    healthy_provider.generate = AsyncMock(return_value=result)

    selected = _make_model("claude-sonnet-4", GenerationProvider.CLAUDE)
    fallback = _make_model("llama-3.3-70b-versatile", GenerationProvider.GROQ)
    decision = _make_decision(selected=selected, fallbacks=[fallback])

    registry = GenerationRegistry(providers=[failing_provider, healthy_provider])
    service = GenerationService(
        registry=registry,
        routing_service=_make_routing_service(decision),
    )

    returned = await service.generate(request=request)

    assert returned is result
    failing_provider.generate.assert_awaited_once()
    healthy_provider.generate.assert_awaited_once()
    assert returned.metadata["routing"]["used_fallback"] is True
    assert returned.metadata["routing"]["selected_provider"] == "claude"


async def test_generate_skips_candidates_whose_provider_is_not_registered() -> None:
    request = _make_request()
    result = _make_result(request)

    registered_provider = _make_provider(GenerationProvider.GROQ)
    registered_provider.generate = AsyncMock(return_value=result)

    unregistered = _make_model("gpt-5", GenerationProvider.OPENAI)
    registered = _make_model("llama-3.3-70b-versatile", GenerationProvider.GROQ)
    decision = _make_decision(selected=unregistered, fallbacks=[registered])

    registry = GenerationRegistry(providers=[registered_provider])
    service = GenerationService(
        registry=registry,
        routing_service=_make_routing_service(decision),
    )

    returned = await service.generate(request=request)

    assert returned is result
    registered_provider.generate.assert_awaited_once()


async def test_generate_raises_when_every_routed_candidate_fails() -> None:
    request = _make_request()

    first = _make_provider(GenerationProvider.CLAUDE)
    first.generate = AsyncMock(side_effect=GenerationExecutionError("down"))

    second = _make_provider(GenerationProvider.GROQ)
    second.generate = AsyncMock(side_effect=GenerationExecutionError("also down"))

    decision = _make_decision(
        selected=_make_model("claude-sonnet-4", GenerationProvider.CLAUDE),
        fallbacks=[_make_model("llama-3.3-70b-versatile", GenerationProvider.GROQ)],
    )

    registry = GenerationRegistry(providers=[first, second])
    service = GenerationService(
        registry=registry,
        routing_service=_make_routing_service(decision),
    )

    with pytest.raises(GenerationExecutionError, match="All routed candidate models failed"):
        await service.generate(request=request)


async def test_generate_wraps_no_eligible_models_error_as_validation_error() -> None:
    request = _make_request()

    routing_service = MagicMock()
    routing_service.route = MagicMock(side_effect=NoEligibleModelsError("nothing eligible"))

    registry = GenerationRegistry(providers=[])
    service = GenerationService(registry=registry, routing_service=routing_service)

    with pytest.raises(GenerationValidationError, match="nothing eligible"):
        await service.generate(request=request)


# ==========================================================
# stream_generate() (R2 -- Streaming Platform)
# ==========================================================


async def _collect(async_gen):
    return [item async for item in async_gen]


async def _fake_stream(chunks):
    for chunk in chunks:
        yield chunk


def test_registry_exposes_the_registry_it_was_built_with() -> None:
    registry = GenerationRegistry(providers=[])
    service = GenerationService(registry=registry)

    assert service.registry is registry


async def test_stream_generate_yields_from_the_explicit_providers_stream() -> None:
    request = _make_request()

    chunks = [
        StreamChunk(event=StreamEventType.START),
        StreamChunk(event=StreamEventType.TOKEN, content="hi"),
        StreamChunk(event=StreamEventType.COMPLETED),
    ]

    provider = _make_capable_provider(GenerationProvider.GROQ)
    provider.stream = MagicMock(return_value=_fake_stream(chunks))

    registry = GenerationRegistry(providers=[provider])
    service = GenerationService(registry=registry)

    result = await _collect(
        service.stream_generate(request=request, provider=GenerationProvider.GROQ)
    )

    assert result == chunks
    provider.stream.assert_called_once_with(request)


async def test_stream_generate_raises_for_an_unregistered_explicit_provider() -> None:
    request = _make_request()

    registry = GenerationRegistry(providers=[])
    service = GenerationService(registry=registry)

    with pytest.raises(GenerationProviderNotFoundError):
        await _collect(service.stream_generate(request=request, provider=GenerationProvider.GROQ))


async def test_stream_generate_raises_validation_error_for_empty_prompt() -> None:
    request = _make_request(user_prompt="   ")

    registry = GenerationRegistry(providers=[])
    service = GenerationService(registry=registry)

    with pytest.raises(GenerationValidationError):
        await _collect(service.stream_generate(request=request, provider=GenerationProvider.GROQ))


async def test_stream_generate_without_provider_routes_to_the_selected_model() -> None:
    request = _make_request()

    chunks = [StreamChunk(event=StreamEventType.TOKEN, content="hi")]

    provider = _make_capable_provider(GenerationProvider.GROQ)
    provider.stream = MagicMock(return_value=_fake_stream(chunks))

    selected = _make_model("llama-3.3-70b-versatile", GenerationProvider.GROQ)
    decision = _make_decision(selected=selected)

    registry = GenerationRegistry(providers=[provider])
    service = GenerationService(
        registry=registry,
        routing_service=_make_routing_service(decision),
    )

    result = await _collect(service.stream_generate(request=request))

    assert result == chunks


async def test_stream_generate_without_provider_raises_when_no_routing_service_wired() -> None:
    request = _make_request()

    registry = GenerationRegistry(providers=[])
    service = GenerationService(registry=registry)

    with pytest.raises(GenerationValidationError, match="RoutingService"):
        await _collect(service.stream_generate(request=request))


async def test_stream_generate_raises_when_routed_provider_is_not_registered() -> None:
    request = _make_request()

    selected = _make_model("llama-3.3-70b-versatile", GenerationProvider.GROQ)
    decision = _make_decision(selected=selected)

    registry = GenerationRegistry(providers=[])
    service = GenerationService(
        registry=registry,
        routing_service=_make_routing_service(decision),
    )

    with pytest.raises(GenerationProviderNotFoundError):
        await _collect(service.stream_generate(request=request))


# ==============================================================
# GuardrailService integration
# ==============================================================


class _AlwaysBlockInputGuardrail(InputGuardrailInterface):
    @property
    def name(self) -> str:
        return "always_block_input"

    async def check(self, request: GenerationRequest) -> list[GuardrailIssue]:
        return [
            GuardrailIssue(
                code="blocked",
                severity=GuardrailSeverity.CRITICAL,
                category=GuardrailCategory.PROMPT_INJECTION,
                message="input blocked by test guardrail",
            )
        ]


class _AlwaysBlockGenerationGuardrail(GenerationGuardrailInterface):
    @property
    def name(self) -> str:
        return "always_block_generation"

    async def check(self, result: GenerationResult) -> list[GuardrailIssue]:
        return [
            GuardrailIssue(
                code="blocked",
                severity=GuardrailSeverity.CRITICAL,
                category=GuardrailCategory.MODERATION,
                message="generation blocked by test guardrail",
            )
        ]


def _make_guardrail_service(registry: GuardrailRegistry | None = None) -> GuardrailService:
    return GuardrailService(registry=registry or GuardrailRegistry())


async def test_generate_raises_guardrail_violation_when_input_blocked() -> None:
    registry = GuardrailRegistry()
    registry.register_input_guardrail(_AlwaysBlockInputGuardrail())

    provider = _make_provider()
    generation_registry = GenerationRegistry(providers=[provider])
    service = GenerationService(
        registry=generation_registry,
        guardrail_service=_make_guardrail_service(registry),
    )

    with pytest.raises(GuardrailViolationError, match="Input blocked"):
        await service.generate(provider=GenerationProvider.GROQ, request=_make_request())

    provider.generate.assert_not_awaited()


async def test_generate_raises_guardrail_violation_when_generation_blocked() -> None:
    registry = GuardrailRegistry()
    registry.register_generation_guardrail(_AlwaysBlockGenerationGuardrail())

    request = _make_request()
    result = _make_result(request)

    provider = _make_provider()
    provider.generate = AsyncMock(return_value=result)

    generation_registry = GenerationRegistry(providers=[provider])
    service = GenerationService(
        registry=generation_registry,
        guardrail_service=_make_guardrail_service(registry),
    )

    with pytest.raises(GuardrailViolationError, match="Generation blocked"):
        await service.generate(provider=GenerationProvider.GROQ, request=request)

    provider.generate.assert_awaited_once()


async def test_generate_attaches_guardrail_report_when_allowed() -> None:
    request = _make_request()
    result = _make_result(request)

    provider = _make_provider()
    provider.generate = AsyncMock(return_value=result)

    generation_registry = GenerationRegistry(providers=[provider])
    service = GenerationService(
        registry=generation_registry,
        guardrail_service=_make_guardrail_service(),
    )

    returned = await service.generate(provider=GenerationProvider.GROQ, request=request)

    assert returned.guardrails is not None
    assert returned.guardrails.blocked is False


async def test_generate_leaves_guardrails_none_without_a_guardrail_service() -> None:
    request = _make_request()
    result = _make_result(request)

    provider = _make_provider()
    provider.generate = AsyncMock(return_value=result)

    registry = GenerationRegistry(providers=[provider])
    service = GenerationService(registry=registry)

    returned = await service.generate(provider=GenerationProvider.GROQ, request=request)

    assert returned.guardrails is None


# ==============================================================
# Validation Policy Layer integration
# ==============================================================


def _failing_runtime_result() -> ValidationResult:
    return ValidationResult(
        valid=False,
        issues=[
            ValidationIssue(
                validator="research_contract",
                severity=ValidationSeverity.ERROR,
                message="missing required field 'citations'",
            )
        ],
    )


async def test_generate_stops_before_the_provider_call_when_fail_fast_policy_trips() -> None:
    """
    A pre-flight `validate_input()` failure (FailFastPolicy default:
    stop_on_error=True) must raise before any provider is ever called --
    this is what "Input Validation precedes Provider Execution" means in
    practice.
    """

    provider = _make_capable_provider()
    registry = GenerationRegistry(providers=[provider])

    validation_service = AsyncMock()
    validation_service.validate_input = AsyncMock(return_value=_failing_input_result())

    service = GenerationService(registry=registry, validation_service=validation_service)

    with pytest.raises(GenerationValidationError, match="Input failed validation"):
        await service.generate(provider=GenerationProvider.GROQ, request=_make_request())

    provider.generate.assert_not_awaited()


async def test_generate_proceeds_when_fail_fast_policy_is_disabled() -> None:
    request = _make_request()
    result = _make_result(request)

    provider = _make_capable_provider()
    provider.generate = AsyncMock(return_value=result)
    registry = GenerationRegistry(providers=[provider])

    validation_service = AsyncMock()
    validation_service.validate_input = AsyncMock(return_value=_failing_input_result())
    validation_service.validate = AsyncMock(
        return_value=ValidationReport(
            input_validation=_failing_input_result(),
            output_validation=_valid_result(),
            hallucination_validation=_valid_result(),
            valid=False,
        )
    )

    service = GenerationService(
        registry=registry,
        validation_service=validation_service,
        fail_fast_policy=FailFastPolicy(stop_on_error=False),
    )

    await service.generate(provider=GenerationProvider.GROQ, request=request)

    provider.generate.assert_awaited_once()


async def test_generate_does_not_regenerate_on_failed_runtime_validation_by_default() -> None:
    request = _make_request()
    request.max_regeneration_attempts = 2
    result = _make_result(request)

    provider = _make_capable_provider()
    provider.generate = AsyncMock(return_value=result)

    report = ValidationReport(
        input_validation=_valid_result(),
        output_validation=_valid_result(),
        hallucination_validation=_valid_result(),
        runtime_validation=_failing_runtime_result(),
        valid=False,
    )

    registry = GenerationRegistry(providers=[provider])
    service = GenerationService(
        registry=registry,
        validation_service=_make_validation_service(report),
    )

    await service.generate(provider=GenerationProvider.GROQ, request=request)

    provider.generate.assert_awaited_once()


async def test_generate_regenerates_on_failed_runtime_validation_when_policy_opts_in() -> None:
    request = _make_request()
    request.max_regeneration_attempts = 1
    result = _make_result(request)

    provider = _make_capable_provider()
    provider.generate = AsyncMock(return_value=result)

    report = ValidationReport(
        input_validation=_valid_result(),
        output_validation=_valid_result(),
        hallucination_validation=_valid_result(),
        runtime_validation=_failing_runtime_result(),
        valid=False,
    )

    registry = GenerationRegistry(providers=[provider])
    service = GenerationService(
        registry=registry,
        validation_service=_make_validation_service(report),
        runtime_validation_policy=RuntimeValidationPolicy(block_on_error=True),
    )

    await service.generate(provider=GenerationProvider.GROQ, request=request)

    assert provider.generate.await_count == 2


# ==============================================================
# Runtime Metrics Integration
# ==============================================================


async def test_generate_records_metrics_through_the_metrics_service() -> None:
    request = _make_request()
    result = _make_result(request)

    provider = _make_provider()
    provider.generate = AsyncMock(return_value=result)

    metrics_service = MagicMock(spec=GenerationMetricsService)

    registry = GenerationRegistry(providers=[provider])
    service = GenerationService(
        registry=registry,
        metrics_service=metrics_service,
    )

    returned = await service.generate(provider=GenerationProvider.GROQ, request=request)

    metrics_service.record.assert_called_once_with(returned)


async def test_generate_uses_a_default_metrics_service_when_none_is_wired() -> None:
    """
    Unlike artifact_writer/caching_service/guardrail_service (opt-in,
    None skips them), GenerationService always has a real
    GenerationMetricsService -- generate() must succeed without one
    being explicitly passed in.
    """

    request = _make_request()
    result = _make_result(request)

    provider = _make_provider()
    provider.generate = AsyncMock(return_value=result)

    registry = GenerationRegistry(providers=[provider])
    service = GenerationService(registry=registry)

    returned = await service.generate(provider=GenerationProvider.GROQ, request=request)

    assert returned is result


async def test_generate_records_observability_when_wired() -> None:
    """
    AI Runtime Observability Platform PRD §8: when an ObservabilityService
    is wired, generate() forwards the metrics snapshot produced by
    `metrics_service.record()` to it, tagged with the request's resolved
    artifact runtime (defaulting to CHAT, same default
    `_persist_generation_artifact` uses).
    """

    request = _make_request()
    result = _make_result(request)

    provider = _make_provider()
    provider.generate = AsyncMock(return_value=result)

    from app.ai.artifacts.enums import ArtifactRuntime
    from app.ai.observability.service import ObservabilityService

    observability_service = MagicMock(spec=ObservabilityService)
    observability_service.record_generation = AsyncMock()

    registry = GenerationRegistry(providers=[provider])
    service = GenerationService(
        registry=registry,
        observability_service=observability_service,
    )

    await service.generate(provider=GenerationProvider.GROQ, request=request)

    observability_service.record_generation.assert_awaited_once()
    call_kwargs = observability_service.record_generation.await_args.kwargs
    assert call_kwargs["artifact_runtime"] == ArtifactRuntime.CHAT
    assert call_kwargs["metrics"].generation_id == result.generation_id


async def test_generate_skips_observability_when_not_wired() -> None:
    """Default GenerationService (no observability_service) must behave
    exactly as before this platform existed -- no attribute error, no
    extra calls."""

    request = _make_request()
    result = _make_result(request)

    provider = _make_provider()
    provider.generate = AsyncMock(return_value=result)

    registry = GenerationRegistry(providers=[provider])
    service = GenerationService(registry=registry)

    returned = await service.generate(provider=GenerationProvider.GROQ, request=request)

    assert returned is result


async def test_generate_wraps_the_provider_call_in_the_configured_tracer() -> None:
    request = _make_request()
    result = _make_result(request)

    provider = _make_provider()
    provider.generate = AsyncMock(return_value=result)

    from app.ai.observability.providers.langsmith.tracing import RuntimeTracer

    tracer = MagicMock(spec=RuntimeTracer)
    trace_handle = MagicMock()
    tracer.trace.return_value.__enter__ = MagicMock(return_value=trace_handle)
    tracer.trace.return_value.__exit__ = MagicMock(return_value=False)

    registry = GenerationRegistry(providers=[provider])
    service = GenerationService(registry=registry, tracer=tracer)

    returned = await service.generate(provider=GenerationProvider.GROQ, request=request)

    assert returned is result
    tracer.trace.assert_called_once()
    assert tracer.trace.call_args.kwargs["name"] == "generation"
    assert tracer.trace.call_args.kwargs["inputs"] == {"prompt": request.user_prompt}
    assert tracer.trace.call_args.kwargs["tags"]["provider"] == GenerationProvider.GROQ.value

    trace_handle.set_output.assert_called_once_with(
        content=result.content,
        prompt_tokens=result.statistics.prompt_tokens,
        completion_tokens=result.statistics.completion_tokens,
        total_tokens=result.statistics.total_tokens,
    )


# ==========================================================
# score_completed_stream (informational, non-blocking scoring for
# already-completed streams -- see StreamingService._stream_live())
# ==========================================================


async def test_score_completed_stream_attaches_guardrail_report_when_allowed() -> None:
    request = _make_request()
    result = _make_result(request)

    provider = _make_capable_provider()
    registry = GenerationRegistry(providers=[provider])
    service = GenerationService(
        registry=registry,
        guardrail_service=_make_guardrail_service(),
    )

    returned = await service.score_completed_stream(request=request, result=result)

    assert returned is result
    assert returned.guardrails is not None
    assert returned.guardrails.blocked is False


async def test_score_completed_stream_does_not_raise_when_guardrails_blocked() -> None:
    """
    Unlike `_enforce_generation_guardrails()` (used by `generate()`), a
    blocked verdict here must never raise -- the stream has already
    reached the client, there is nothing left to stop.
    """
    guardrail_registry = GuardrailRegistry()
    guardrail_registry.register_generation_guardrail(_AlwaysBlockGenerationGuardrail())

    request = _make_request()
    result = _make_result(request)

    provider = _make_capable_provider()
    registry = GenerationRegistry(providers=[provider])
    service = GenerationService(
        registry=registry,
        guardrail_service=_make_guardrail_service(guardrail_registry),
    )

    returned = await service.score_completed_stream(request=request, result=result)

    assert returned.guardrails is not None
    assert returned.guardrails.blocked is True


async def test_score_completed_stream_populates_validation_report() -> None:
    request = _make_request()
    result = _make_result(request)

    provider = _make_capable_provider()
    registry = GenerationRegistry(providers=[provider])

    report = ValidationReport(
        input_validation=_valid_result(),
        output_validation=_valid_result(),
        hallucination_validation=_valid_result(),
        valid=True,
    )
    service = GenerationService(
        registry=registry,
        validation_service=_make_validation_service(report),
    )

    returned = await service.score_completed_stream(request=request, result=result)

    assert returned.validation is report


async def test_score_completed_stream_swallows_guardrail_evaluation_failure() -> None:
    request = _make_request()
    result = _make_result(request)

    provider = _make_capable_provider()
    registry = GenerationRegistry(providers=[provider])

    guardrail_service = AsyncMock()
    guardrail_service.evaluate = AsyncMock(side_effect=RuntimeError("guardrail backend down"))

    service = GenerationService(registry=registry, guardrail_service=guardrail_service)

    # Must not raise.
    returned = await service.score_completed_stream(request=request, result=result)

    assert returned.guardrails is None


async def test_score_completed_stream_swallows_validation_failure() -> None:
    request = _make_request()
    result = _make_result(request)

    provider = _make_capable_provider()
    registry = GenerationRegistry(providers=[provider])

    validation_service = AsyncMock()
    validation_service.validate = AsyncMock(side_effect=RuntimeError("validation backend down"))

    service = GenerationService(registry=registry, validation_service=validation_service)

    # Must not raise.
    returned = await service.score_completed_stream(request=request, result=result)

    assert returned.validation is None


async def test_score_completed_stream_noop_when_neither_service_wired() -> None:
    request = _make_request()
    result = _make_result(request)

    provider = _make_capable_provider()
    registry = GenerationRegistry(providers=[provider])
    service = GenerationService(registry=registry)

    returned = await service.score_completed_stream(request=request, result=result)

    assert returned is result
    assert returned.guardrails is None
    assert returned.validation is None
