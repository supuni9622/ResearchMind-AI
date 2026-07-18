"""
Unit tests for PromptService.

Covers:
- render() returns a fully populated PromptRenderResult, with token
  counting delegated to the injected TokenCounter
- render_text() returns just the rendered prompt string
- render_messages() returns the underlying LangChain messages
- Missing required variables raise ValueError before any rendering or
  token counting happens
- Token counting resolves the default provider/model when no override
  is given, and honors request.override_provider when it is
- Template-level examples are used when a render request supplies none
- Request-level examples override the template's own examples

TokenCounter is injected as a fake throughout: the real implementation
dials out to Anthropic/Gemini for some providers and can't even be
constructed without API keys, so these tests never touch it.
"""

from __future__ import annotations

import pytest
from app.ai.runtime.generation.enums import GenerationProvider
from app.ai.runtime.generation.prompts.models import PromptRenderRequest
from app.ai.runtime.generation.prompts.registry import PromptRegistry
from app.ai.runtime.generation.prompts.service import PromptService
from langchain_core.messages import HumanMessage, SystemMessage

from tests.unit.ai.runtime.generation.prompts.factories import make_template, make_token_counter


def _make_service(template, token_counter=None):  # noqa: ANN001, ANN201
    registry = PromptRegistry()
    registry.register(template)
    counter = token_counter or make_token_counter()
    return PromptService(registry, counter), counter


# ---------------------------------------------------------------------------
# Render
# ---------------------------------------------------------------------------


async def test_render() -> None:
    template = make_template(name="research", version="v1")
    service, token_counter = _make_service(template)

    request = PromptRenderRequest(
        template_name="research",
        variables={"context": "the sky is blue", "user_input": "why is the sky blue?"},
    )

    result = await service.render(request)

    assert result.template_name == "research"
    assert result.version == "v1"
    assert "the sky is blue" in result.rendered_prompt
    assert "why is the sky blue?" in result.rendered_prompt
    assert result.estimated_tokens == 100
    assert result.metadata is template.metadata
    token_counter.count.assert_awaited_once()


# ---------------------------------------------------------------------------
# Render text
# ---------------------------------------------------------------------------


async def test_render_text() -> None:
    template = make_template(name="research", version="v1")
    service, _ = _make_service(template)

    request = PromptRenderRequest(
        template_name="research",
        variables={"context": "ctx", "user_input": "question"},
    )

    text = await service.render_text(request)

    assert isinstance(text, str)
    assert "ctx" in text
    assert "question" in text


# ---------------------------------------------------------------------------
# Render messages
# ---------------------------------------------------------------------------


async def test_render_messages() -> None:
    template = make_template(name="research", version="v1")
    service, token_counter = _make_service(template)

    request = PromptRenderRequest(
        template_name="research",
        variables={"context": "ctx", "user_input": "question"},
    )

    messages = await service.render_messages(request)

    assert isinstance(messages[0], SystemMessage)
    assert isinstance(messages[-1], HumanMessage)
    assert messages[-1].content == "question"
    # render_messages() doesn't estimate tokens -- only render() does.
    token_counter.count.assert_not_awaited()


# ---------------------------------------------------------------------------
# Missing variables
# ---------------------------------------------------------------------------


async def test_missing_variables() -> None:
    template = make_template(name="research", version="v1")
    service, token_counter = _make_service(template)

    request = PromptRenderRequest(
        template_name="research",
        variables={"context": "ctx"},
    )

    with pytest.raises(ValueError, match="user_input"):
        await service.render(request)

    token_counter.count.assert_not_awaited()


# ---------------------------------------------------------------------------
# Estimated tokens
# ---------------------------------------------------------------------------


async def test_estimate_tokens() -> None:
    template = make_template(name="research", version="v1")
    service, token_counter = _make_service(template, make_token_counter(return_value=42))

    request = PromptRenderRequest(
        template_name="research",
        variables={"context": "ctx", "user_input": "question"},
    )

    result = await service.render(request)

    assert result.estimated_tokens == 42

    # No override_provider -> defaults to OpenAI's resolved model.
    token_counter.count.assert_awaited_once_with(
        provider=GenerationProvider.OPENAI,
        model="gpt-5-mini",
        text=result.rendered_prompt,
    )


async def test_estimate_tokens_respects_override_provider() -> None:
    template = make_template(name="research", version="v1")
    service, token_counter = _make_service(template)

    request = PromptRenderRequest(
        template_name="research",
        variables={"context": "ctx", "user_input": "question"},
        override_provider=GenerationProvider.CLAUDE,
    )

    result = await service.render(request)

    token_counter.count.assert_awaited_once_with(
        provider=GenerationProvider.CLAUDE,
        model="claude-sonnet-5",
        text=result.rendered_prompt,
    )


async def test_estimate_tokens_respects_override_model() -> None:
    template = make_template(name="research", version="v1")
    service, token_counter = _make_service(template)

    request = PromptRenderRequest(
        template_name="research",
        variables={"context": "ctx", "user_input": "question"},
        override_provider=GenerationProvider.OPENAI,
        override_model="gpt-5-nano",
    )

    result = await service.render(request)

    # override_model wins over the provider's resolved default model.
    token_counter.count.assert_awaited_once_with(
        provider=GenerationProvider.OPENAI,
        model="gpt-5-nano",
        text=result.rendered_prompt,
    )


# ---------------------------------------------------------------------------
# Template examples fallback
# ---------------------------------------------------------------------------


async def test_template_examples_used() -> None:
    template = make_template(
        name="research",
        version="v1",
        examples=[{"input": "template question", "output": "template answer"}],
    )
    service, _ = _make_service(template)

    request = PromptRenderRequest(
        template_name="research",
        variables={"context": "ctx", "user_input": "question"},
    )

    messages = await service.render_messages(request)
    contents = [message.content for message in messages]

    assert "template question" in contents
    assert "template answer" in contents


# ---------------------------------------------------------------------------
# Request examples override
# ---------------------------------------------------------------------------


async def test_request_examples_override() -> None:
    template = make_template(
        name="research",
        version="v1",
        examples=[{"input": "template question", "output": "template answer"}],
    )
    service, _ = _make_service(template)

    request = PromptRenderRequest(
        template_name="research",
        variables={"context": "ctx", "user_input": "question"},
        examples=[{"input": "override question", "output": "override answer"}],
    )

    messages = await service.render_messages(request)
    contents = [message.content for message in messages]

    assert "override question" in contents
    assert "override answer" in contents
    assert "template question" not in contents
    assert "template answer" not in contents
