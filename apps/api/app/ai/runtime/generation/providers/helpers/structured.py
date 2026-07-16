from __future__ import annotations

from typing import Any, Literal

from app.ai.runtime.generation.enums import (
    ResponseFormat,
)
from app.ai.runtime.generation.models import (
    GenerationRequest,
)

###############################################################################
# OpenAI
###############################################################################


def build_openai_text_config(
    request: GenerationRequest,
) -> dict[str, Any] | None:

    #
    # Structured Outputs
    #

    if request.response_format == ResponseFormat.STRUCTURED and request.output_schema:
        return {
            "format": {
                "type": "json_schema",
                "name": "response",
                "schema": request.output_schema,
            }
        }

    #
    # JSON Mode
    #

    if request.response_format == ResponseFormat.JSON:
        return {
            "format": {
                "type": "json_object",
            }
        }

    return None


###############################################################################
# Groq
###############################################################################


def build_groq_response_format(
    request: GenerationRequest,
) -> dict[str, Any] | None:

    if request.response_format != ResponseFormat.JSON:
        return None

    return {
        "type": "json_object",
    }


###############################################################################
# Gemini
###############################################################################


def build_gemini_generation_config(
    request: GenerationRequest,
) -> dict[str, Any]:

    config: dict[str, Any] = {}

    if request.output_schema:
        config["response_mime_type"] = "application/json"

        config["response_schema"] = request.output_schema

    return config


###############################################################################
# Ollama
###############################################################################


def build_ollama_format(
    request: GenerationRequest,
) -> Literal["json"] | None:

    if request.response_format in (
        ResponseFormat.JSON,
        ResponseFormat.STRUCTURED,
    ):
        return "json"

    return None


###############################################################################
# Claude
###############################################################################


def build_claude_json_instruction(
    request: GenerationRequest,
) -> str:

    if request.response_format not in (
        ResponseFormat.JSON,
        ResponseFormat.STRUCTURED,
    ):
        return ""

    return """

Return ONLY valid JSON.

Do not wrap the response inside markdown.

Do not explain.

Do not add extra text.
"""
