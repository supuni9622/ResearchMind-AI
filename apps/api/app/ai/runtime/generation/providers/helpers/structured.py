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

    #
    # Structured Outputs (schema-constrained decoding)
    #

    if request.response_format == ResponseFormat.STRUCTURED and request.output_schema:
        return {
            "type": "json_schema",
            "json_schema": {
                "name": "response",
                "schema": request.output_schema,
                "strict": True,
            },
        }

    #
    # JSON Mode
    #

    if request.response_format == ResponseFormat.JSON:
        return {
            "type": "json_object",
        }

    return None


###############################################################################
# Gemini
###############################################################################


def build_gemini_generation_config(
    request: GenerationRequest,
) -> dict[str, Any]:

    config: dict[str, Any] = {}

    if request.output_schema:
        config["response_mime_type"] = "application/json"

        #
        # `response_schema` expects Gemini's restricted OpenAPI-subset
        # Schema type. `response_json_schema` accepts standard JSON
        # Schema (the shape produced by pydantic's `model_json_schema()`
        # and stored on `request.output_schema`), so it is the correct
        # field for a raw schema dict.
        #

        config["response_json_schema"] = request.output_schema

    return config


###############################################################################
# Ollama
###############################################################################


def build_ollama_format(
    request: GenerationRequest,
) -> Literal["json"] | dict[str, Any] | None:

    #
    # Structured Outputs (schema-constrained decoding)
    #

    if request.response_format == ResponseFormat.STRUCTURED and request.output_schema:
        return request.output_schema

    #
    # JSON Mode
    #

    if request.response_format in (
        ResponseFormat.JSON,
        ResponseFormat.STRUCTURED,
    ):
        return "json"

    return None


###############################################################################
# Claude
###############################################################################


def build_claude_output_config(
    request: GenerationRequest,
) -> dict[str, Any] | None:
    """
    Native structured output via `output_config.format`.

    Guarantees the response text is valid JSON matching the schema,
    so this is preferred over the prompt-based instruction fallback
    whenever a schema is available.
    """

    if request.response_format != ResponseFormat.STRUCTURED or not request.output_schema:
        return None

    return {
        "format": {
            "type": "json_schema",
            "schema": request.output_schema,
        }
    }


def build_claude_json_instruction(
    request: GenerationRequest,
) -> str:
    """
    Prompt-enforced JSON fallback.

    Used when no schema is available to drive native
    `output_config.format` (e.g. plain JSON mode).
    """

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
