from __future__ import annotations

import json

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
    # Providers reached via `build_chat_messages` don't all get
    # schema-constrained decoding (e.g. Groq's `llama-3.3-70b-versatile`
    # falls back to plain `json_object` mode -- see
    # `build_groq_response_format`), so the schema must be spelled out
    # in the prompt itself or the model has nothing to conform to.
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
