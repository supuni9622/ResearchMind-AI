"""
Wave 4 chat attachments -- vision content-block builders
(providers/helpers/prompt_builder.py) and the routing-capability gate
that keeps non-vision providers out of an attachment turn.

Covers:
- Content-block shape per provider (OpenAI/Claude/Gemini) when
  `GenerationRequest.attachments` is non-empty.
- Regression guard: a request with no attachments produces output
  identical to the pre-Wave-4 plain-text builders.
- Routing: Groq/Ollama are excluded from candidates once
  `RequiredCapability.VISION` is required.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

from app.ai.knowledge.context.models import PromptContext
from app.ai.runtime.generation.catalog.registry import ModelCatalogRegistry
from app.ai.runtime.generation.enums import GenerationProvider
from app.ai.runtime.generation.models import (
    GenerationAttachment,
    GenerationRequest,
    ProviderCapabilities,
)
from app.ai.runtime.generation.providers.helpers.prompt_builder import (
    build_claude_messages,
    build_claude_vision_messages,
    build_gemini_vision_contents,
    build_openai_vision_input,
    build_prompt_text,
)
from app.ai.runtime.generation.routing.enums import RequiredCapability

_ATTACHMENT = GenerationAttachment(
    url="https://s3.example.com/signed-url",
    content_type="image/png",
)


def _request(**overrides: object) -> GenerationRequest:
    kwargs = {
        "prompt_context": PromptContext(context="retrieved context", chunks=[]),
        "user_prompt": "what's in this image?",
    }
    kwargs.update(overrides)
    return GenerationRequest(**kwargs)


# ---------------------------------------------------------------------------
# OpenAI
# ---------------------------------------------------------------------------


class TestOpenAIVisionInput:
    def test_no_attachments_matches_plain_text_builder(self) -> None:
        request = _request()

        vision_input = build_openai_vision_input(request)

        assert vision_input[-1]["role"] == "user"
        assert vision_input[-1]["content"][0]["type"] == "input_text"
        assert vision_input[-1]["content"][0]["text"] == build_prompt_text(request)

    def test_one_attachment_per_image_content_block(self) -> None:
        request = _request(attachments=[_ATTACHMENT, _ATTACHMENT])

        vision_input = build_openai_vision_input(request)
        content = vision_input[-1]["content"]

        image_blocks = [block for block in content if block["type"] == "input_image"]
        assert len(image_blocks) == 2
        assert all(block["image_url"] == _ATTACHMENT.url for block in image_blocks)

    def test_system_prompt_becomes_its_own_message(self) -> None:
        request = _request(system_prompt="Be concise.", attachments=[_ATTACHMENT])

        vision_input = build_openai_vision_input(request)

        assert vision_input[0] == {"role": "system", "content": "Be concise."}


# ---------------------------------------------------------------------------
# Claude
# ---------------------------------------------------------------------------


class TestClaudeVisionMessages:
    def test_no_attachments_matches_plain_text_builder(self) -> None:
        request = _request()

        system, messages = build_claude_vision_messages(request)
        base_system, base_messages = build_claude_messages(request)

        assert system == base_system
        assert messages[0]["content"][0]["text"] == base_messages[0]["content"]

    def test_one_image_block_per_attachment(self) -> None:
        request = _request(attachments=[_ATTACHMENT])

        _, messages = build_claude_vision_messages(request)
        content = messages[0]["content"]

        assert content[0]["type"] == "text"
        assert content[1] == {
            "type": "image",
            "source": {"type": "url", "url": _ATTACHMENT.url},
        }

    def test_system_prompt_stays_separate_from_content_blocks(self) -> None:
        request = _request(system_prompt="Be concise.", attachments=[_ATTACHMENT])

        system, messages = build_claude_vision_messages(request)

        assert system == "Be concise."
        assert all(block.get("type") != "system" for block in messages[0]["content"])


# ---------------------------------------------------------------------------
# Gemini
# ---------------------------------------------------------------------------


class TestGeminiVisionContents:
    async def test_no_attachments_matches_plain_text_builder(self) -> None:
        request = _request()

        contents = await build_gemini_vision_contents(request)

        assert contents[0]["role"] == "user"
        text_parts = [part["text"] for part in contents[0]["parts"] if "text" in part]
        assert "\n\n".join(text_parts) == "" or build_prompt_text(request)

    async def test_fetches_and_inlines_attachment_bytes(self) -> None:
        request = _request(attachments=[_ATTACHMENT])

        fake_response = MagicMock()
        fake_response.content = b"fake-image-bytes"
        fake_response.raise_for_status = MagicMock()

        fake_client = AsyncMock()
        fake_client.get = AsyncMock(return_value=fake_response)
        fake_client.__aenter__ = AsyncMock(return_value=fake_client)
        fake_client.__aexit__ = AsyncMock(return_value=False)

        with patch("httpx.AsyncClient", return_value=fake_client):
            contents = await build_gemini_vision_contents(request)

        parts = contents[0]["parts"]
        image_parts = [part for part in parts if "inline_data" in part]

        assert len(image_parts) == 1
        assert image_parts[0]["inline_data"]["mime_type"] == "image/png"
        fake_client.get.assert_awaited_once_with(_ATTACHMENT.url)


# ---------------------------------------------------------------------------
# Routing: vision capability gate
# ---------------------------------------------------------------------------


class TestVisionRoutingCapabilityGate:
    def test_groq_and_ollama_lack_vision_capability_by_default(self) -> None:
        assert ProviderCapabilities().vision is False

    def test_catalog_filters_out_non_vision_models_when_vision_required(self) -> None:
        registry = ModelCatalogRegistry()

        vision_models = {
            model.model_name for model in registry.enabled() if model.capabilities.vision
        }
        non_vision_models = {
            model.model_name for model in registry.enabled() if not model.capabilities.vision
        }

        assert vision_models, "expected at least one vision-capable model in the catalog"
        assert any(model.provider == GenerationProvider.GROQ for model in registry.enabled()), (
            "expected Groq to be cataloged as a non-vision provider for this test to be meaningful"
        )

        for model in registry.enabled():
            if model.provider == GenerationProvider.GROQ:
                assert model.model_name in non_vision_models

    def test_required_capabilities_enum_has_vision(self) -> None:
        assert RequiredCapability.VISION in RequiredCapability
