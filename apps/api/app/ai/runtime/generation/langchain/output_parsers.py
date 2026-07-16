"""
LangChain-backed structured output generation.

Uses each provider's LangChain chat model integration with
`with_structured_output()` to combine provider formatting, parsing, and
Pydantic validation into a single call. This is a lighter-weight
alternative to `GenerationService` (`generation/service.py`) for callers
that want LangChain's automatic handling and don't need routing, retries,
cost tracking, or the uniform `GenerationResult` contract.

Only providers with a LangChain chat model integration installed are
supported: OpenAI, Claude, Gemini, Ollama. Groq is not — `langchain-groq`
has no release compatible with `groq>=1.5.0` (the SDK version the native
`GroqProvider` requires), so adding it would mean downgrading the `groq`
package and risking the native integration.
"""

from __future__ import annotations

from typing import cast

import structlog
from app.ai.runtime.generation.enums import (
    GenerationProvider,
)
from app.ai.runtime.generation.models import (
    GenerationRequest,
)
from app.core.settings import settings
from langchain_anthropic import ChatAnthropic
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_ollama import ChatOllama
from langchain_openai import ChatOpenAI
from pydantic import BaseModel, SecretStr

logger = structlog.get_logger()

_UNSUPPORTED_PROVIDERS = {
    GenerationProvider.GROQ: (
        "langchain-groq has no release compatible with groq>=1.5.0 "
        "(the native GroqProvider's SDK floor); adding it would require "
        "downgrading the groq package. Use GenerationService for Groq "
        "structured output instead."
    ),
}


###############################################################################
# Chat Model Construction
###############################################################################


def _secret(
    value: str | None,
) -> SecretStr | None:

    return SecretStr(value) if value is not None else None


def _build_chat_model(
    provider: GenerationProvider,
    model_name: str,
) -> BaseChatModel:

    if provider == GenerationProvider.OPENAI:
        return ChatOpenAI(
            model=model_name,
            api_key=_secret(
                settings.openai_api_key,
            ),
        )

    if provider == GenerationProvider.CLAUDE:
        # `model` is the pydantic field name (alias "model_name",
        # populate_by_name=True); mypy's pydantic plugin resolves this
        # correctly, but pyright — which has no pydantic plugin — only
        # recognizes the alias here and misreports this call. Verified
        # correct at runtime and clean under mypy.
        return ChatAnthropic(
            model=model_name,  # pyright: ignore[reportCallIssue]
            api_key=_secret(
                settings.anthropic_api_key,
            ),
        )

    if provider == GenerationProvider.GEMINI:
        # ChatGoogleGenerativeAI defines `__init__(self, **kwargs: Any)`
        # (for arg-name validation against aliases) rather than a plain
        # pydantic-generated signature, which confuses pyright's overload
        # resolution into reporting unrelated params as missing. Verified
        # correct at runtime and clean under mypy (this project's type
        # checker); this only silences the pyright/Pylance false positive.
        return ChatGoogleGenerativeAI(  # pyright: ignore[reportCallIssue]
            model=model_name,
            api_key=_secret(
                settings.gemini_api_key,
            ),
        )

    if provider == GenerationProvider.OLLAMA:
        return ChatOllama(
            model=model_name,
            base_url=getattr(
                settings,
                "ollama_host",
                None,
            ),
        )

    if provider in _UNSUPPORTED_PROVIDERS:
        raise NotImplementedError(
            f"LangChain with_structured_output is not available for provider "
            f"'{provider.value}': {_UNSUPPORTED_PROVIDERS[provider]}"
        )

    raise NotImplementedError(
        f"LangChain with_structured_output is not available for provider '{provider.value}'."
    )


###############################################################################
# Structured Generation
###############################################################################


async def generate_structured[SchemaT: BaseModel](
    *,
    provider: GenerationProvider,
    model_name: str,
    schema: type[SchemaT],
    user_prompt: str,
    system_prompt: str | None = None,
) -> SchemaT:
    """
    Generates structured output via LangChain's `with_structured_output()`.

    LangChain handles the provider-specific structured output mechanism
    internally (OpenAI json_schema, Claude tool calling, Gemini
    response_schema, Ollama format) and validates the result against
    `schema`, returning an instance of it directly.
    """

    llm = _build_chat_model(
        provider,
        model_name,
    )

    structured_llm = llm.with_structured_output(
        schema,
    )

    messages: list[tuple[str, str]] = []

    if system_prompt:
        messages.append(
            (
                "system",
                system_prompt,
            )
        )

    messages.append(
        (
            "user",
            user_prompt,
        )
    )

    logger.info(
        "generation.langchain.structured_output.started",
        provider=provider.value,
        model=model_name,
        schema=schema.__name__,
    )

    result = await structured_llm.ainvoke(
        messages,
    )

    logger.info(
        "generation.langchain.structured_output.completed",
        provider=provider.value,
        model=model_name,
        schema=schema.__name__,
    )

    #
    # with_structured_output()'s return type is `dict | BaseModel` since
    # it also accepts non-Pydantic schemas; `schema` here is always a
    # Pydantic class, so the result is always a `SchemaT` instance.
    #

    return cast(
        SchemaT,
        result,
    )


async def generate_structured_from_request(
    *,
    provider: GenerationProvider,
    model_name: str,
    request: GenerationRequest,
) -> BaseModel:
    """
    Convenience wrapper over `generate_structured()` that pulls the schema
    and prompts from an existing `GenerationRequest` (reuses
    `request.output_model` — see `generation/models.py`).
    """

    if request.output_model is None:
        raise ValueError("request.output_model is required for LangChain structured output.")

    return await generate_structured(
        provider=provider,
        model_name=model_name,
        schema=request.output_model,
        system_prompt=request.system_prompt,
        user_prompt=(f"{request.prompt_context.context}\n\n{request.user_prompt}"),
    )
