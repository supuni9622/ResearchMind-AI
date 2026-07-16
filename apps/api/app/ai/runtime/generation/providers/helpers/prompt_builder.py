from __future__ import annotations

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

    messages.append(
        {
            "role": "user",
            "content": (request.prompt_context.context + "\n\n" + request.user_prompt),
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
