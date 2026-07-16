from __future__ import annotations

from typing import Any

import structlog
from app.ai.knowledge.context.models import (
    PromptContext,
)
from app.ai.runtime.generation.enums import (
    GenerationProvider,
    ResponseFormat,
)
from app.ai.runtime.generation.exceptions import (
    GenerationError,
    GenerationExecutionError,
    GenerationValidationError,
)
from app.ai.runtime.generation.interfaces import (
    GenerationProviderInterface,
)
from app.ai.runtime.generation.models import (
    GenerationRequest,
    GenerationResult,
    ToolDefinition,
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
    ):
        self._registry = registry

        self._structured_output_registry = structured_output_registry

        self._validation_service = validation_service

        self._prompt_service = prompt_service

    # ==========================================================
    # Public
    # ==========================================================

    async def generate(
        self,
        *,
        provider: GenerationProvider,
        request: GenerationRequest,
    ) -> GenerationResult:

        self._validate(
            request,
        )

        generation_provider = self._registry.get(
            provider,
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

        return result

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

        try:
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

    @classmethod
    def _needs_regeneration(
        cls,
        *,
        request: GenerationRequest,
        result: GenerationResult,
    ) -> bool:

        parse_failed = (
            cls._is_structured_request(
                request,
            )
            and result.parsed_output is None
        )

        #
        # Only the output stage gates regeneration: input-stage issues
        # (token budget, missing capability, ...) describe the request
        # itself, and re-calling the provider with the same request
        # (plus a corrective note) wouldn't fix them — it could even
        # make a token-budget overflow worse. Hallucination-stage
        # issues are WARNING-only heuristics (see HallucinationValidator)
        # and never flip `valid` to False on their own.
        #

        validation_failed = (
            result.validation is not None and not result.validation.output_validation.valid
        )

        return parse_failed or validation_failed

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

    @staticmethod
    def _validate(
        request: GenerationRequest,
    ) -> None:

        if not request.user_prompt.strip():
            logger.warning(
                "generation.validation_failed",
                reason="empty_user_prompt",
            )
            raise (GenerationValidationError("Prompt cannot be empty."))

        if not request.prompt_context.context:
            logger.warning(
                "generation.validation_failed",
                reason="empty_prompt_context",
            )
            raise (GenerationValidationError("Prompt context cannot be empty."))
