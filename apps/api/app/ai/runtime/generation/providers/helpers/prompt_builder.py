from __future__ import annotations

import base64
import json

import httpx
from app.ai.runtime.generation.enums import (
    ResponseFormat,
)
from app.ai.runtime.generation.models import (
    GenerationRequest,
)


def build_prompt_text(
    request: GenerationRequest,
) -> str:
    """
    Canonical text prompt.

    Used by:

    - OpenAI Responses API
    - Gemini
    - fallback providers
    """

    parts: list[str] = []

    if request.system_prompt:
        parts.append(
            request.system_prompt,
        )

    if request.prompt_context.context:
        parts.append(
            request.prompt_context.context,
        )

    parts.append(
        request.user_prompt,
    )

    return "\n\n".join(p.strip() for p in parts if p and p.strip())


def build_chat_messages(
    request: GenerationRequest,
) -> list[dict]:
    """
    OpenAI / Groq / Ollama style messages.
    """

    messages = []

    if request.system_prompt:
        messages.append(
            {
                "role": "system",
                "content": request.system_prompt,
            }
        )

    user_content = request.prompt_context.context + "\n\n" + request.user_prompt

    #
    # Providers reached via `build_chat_messages` do not all get native
    # schema-constrained decoding. Groq also retains a forced-tool fallback,
    # so spelling out the schema keeps regeneration prompts self-contained.
    #

    if request.response_format == ResponseFormat.STRUCTURED and request.output_schema:
        user_content += (
            "\n\nRespond with JSON matching exactly this schema (no extra "
            f"or missing keys):\n{json.dumps(request.output_schema)}"
        )

    messages.append(
        {
            "role": "user",
            "content": user_content,
        }
    )

    return messages


def build_claude_messages(
    request: GenerationRequest,
) -> tuple[str | None, list[dict]]:
    """
    Claude separates system prompt.
    """

    return (
        request.system_prompt,
        [
            {
                "role": "user",
                "content": (request.prompt_context.context + "\n\n" + request.user_prompt),
            }
        ],
    )


###############################################################################
# Vision (Wave 4 chat attachments, docs/PRIORITIZED_ROADMAP.md)
#
# Additive-only: each of these is called instead of, never alongside, the
# plain-text builder above -- gated on `request.attachments` at the
# provider call site (openai.py/claude.py/gemini.py). Every caller that
# never sets `attachments` (Deep Research, Research, Voice) is unaffected.
###############################################################################


def build_openai_vision_input(
    request: GenerationRequest,
) -> list[dict]:
    """
    OpenAI Responses API multi-content `input` -- a message list with a
    `content` array of `input_text`/`input_image` parts, replacing the
    plain string `build_prompt_text` normally passes as `input=`.
    """

    text = request.prompt_context.context + "\n\n" + request.user_prompt

    content: list[dict] = [
        {
            "type": "input_text",
            "text": text.strip(),
        },
    ]

    content.extend(
        {
            "type": "input_image",
            "image_url": attachment.url,
        }
        for attachment in request.attachments
    )

    messages: list[dict] = []

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
            "content": content,
        }
    )

    return messages


def build_claude_vision_messages(
    request: GenerationRequest,
) -> tuple[str | None, list[dict]]:
    """
    Claude content-block array -- a `text` block plus one `image` block
    per attachment, sourced by URL (Anthropic fetches it directly, no
    base64 round-trip through this service).
    """

    text = request.prompt_context.context + "\n\n" + request.user_prompt

    content: list[dict] = [
        {
            "type": "text",
            "text": text.strip(),
        },
    ]

    content.extend(
        {
            "type": "image",
            "source": {
                "type": "url",
                "url": attachment.url,
            },
        }
        for attachment in request.attachments
    )

    return (
        request.system_prompt,
        [
            {
                "role": "user",
                "content": content,
            }
        ],
    )


async def build_gemini_vision_contents(
    request: GenerationRequest,
) -> list[dict]:
    """
    Gemini `contents` -- a `parts` array of a text part plus one
    inline-bytes image part per attachment.

    Unlike OpenAI/Claude, the Gemini Developer API's `file_data.file_uri`
    only resolves File-API/Cloud-Storage URIs, not arbitrary external
    URLs -- an S3 presigned URL is rejected. So this fetches each
    attachment's bytes directly (small images, already size-capped by
    `MAX_ATTACHMENT_SIZE_BYTES`) and inlines them as base64
    `inline_data`, the one shape the API accepts for a URL it can't fetch
    itself. This is the one vision builder that's async and does I/O --
    callers must await it.
    """

    parts: list[dict] = []

    if request.system_prompt:
        parts.append({"text": request.system_prompt})

    if request.prompt_context.context:
        parts.append({"text": request.prompt_context.context})

    parts.append({"text": request.user_prompt})

    async with httpx.AsyncClient(timeout=30.0) as client:
        for attachment in request.attachments:
            response = await client.get(attachment.url)
            response.raise_for_status()

            parts.append(
                {
                    "inline_data": {
                        "mime_type": attachment.content_type,
                        "data": base64.b64encode(response.content).decode("ascii"),
                    },
                }
            )

    return [
        {
            "role": "user",
            "parts": parts,
        }
    ]
