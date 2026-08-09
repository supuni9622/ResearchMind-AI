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


def _require_every_property(schema: Any) -> Any:
    """
    OpenAI's `text.format: json_schema` (Responses API) is strict-mode-only:
    every object schema's `required` must list *every* key in its own
    `properties`, even ones pydantic left optional because they have a
    default (`Field(default=...)`/`Field(default_factory=...)`). Confirmed
    in production: 400 "'required' is required to be supplied and to be an
    array including every key in properties. Missing 'dependencies'." for
    `ResearchPlanTask.dependencies` (`default_factory=list`).

    This doesn't change what's *valid* to send back -- a field with a
    default and no `anyOf: [..., {"type": "null"}]` union still can't be
    omitted, but its type already accepts the value the default implies
    (`[]` for `dependencies`, `1` for `priority`), so requiring it costs
    nothing semantically; pydantic still applies its own defaults/
    validation on `model_validate()` regardless of what's required here.
    Recurses through every place an object schema can appear -- `$defs`
    (pydantic's nested-model location), `properties`, `items`, and
    `anyOf`/`oneOf`/`allOf` -- since `properties`/`required` pairs can sit
    at any nesting depth. Builds a new structure rather than mutating in
    place, so `request.output_schema` itself (used unmodified by output
    validation and other providers) is untouched.
    """

    if isinstance(schema, dict):
        cleaned = {key: _require_every_property(value) for key, value in schema.items()}
        if isinstance(cleaned.get("properties"), dict):
            cleaned["required"] = list(cleaned["properties"].keys())
        return cleaned

    if isinstance(schema, list):
        return [_require_every_property(item) for item in schema]

    return schema


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
                "schema": _require_every_property(request.output_schema),
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
    # Groq only enables `response_format: json_schema` for a narrow,
    # provider-curated allowlist of models (see
    # console.groq.com/docs/structured-outputs#supported-models) --
    # notably NOT `llama-3.3-70b-versatile`, this platform's default/
    # AUTO-routed Groq model, which rejects it with a 400. This config
    # has no per-model capability granularity (`structured_output` is
    # provider-wide), so rather than tracking Groq's allowlist here too,
    # every STRUCTURED request uses plain `json_object` mode instead --
    # `parse_structured_output()`'s repair fallback already exists to
    # handle providers without schema-constrained decoding.
    #

    if request.response_format in (
        ResponseFormat.STRUCTURED,
        ResponseFormat.JSON,
    ):
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
    # JSON-constrained decoding
    #

    # Do not pass the full Pydantic JSON Schema to Ollama. Some local
    # runtimes/models (confirmed with gemma4:12b) fail while compiling
    # schemas containing `$defs`/`$ref`, nullable `anyOf`, and validation
    # bounds into a grammar, returning HTTP 400 before generation starts.
    # The structured request already includes the schema in its prompt, and
    # GenerationService validates the parsed result against `output_model`,
    # including its normal repair/regeneration path. JSON mode therefore
    # preserves correctness without relying on model-specific grammar
    # support.

    if request.response_format in (
        ResponseFormat.JSON,
        ResponseFormat.STRUCTURED,
    ):
        return "json"

    return None


###############################################################################
# Claude
###############################################################################

_CLAUDE_UNSUPPORTED_SCHEMA_KEYWORDS = (
    # Array bounds -- from `Field(min_length=..., max_length=...)` on
    # `list` fields (e.g. `ResearchPlan.tasks`). Confirmed in production:
    # 400 "property 'maxItems' is not supported".
    "minItems",
    "maxItems",
    # Numeric bounds -- from `Field(ge=..., le=...)` (e.g.
    # `ResearchPlanTask.priority`). Confirmed in production: 400
    # "properties maximum, minimum are not supported".
    "minimum",
    "maximum",
    "exclusiveMinimum",
    "exclusiveMaximum",
    "multipleOf",
    # String bounds -- from `Field(min_length=..., max_length=...,
    # pattern=...)` on `str` fields (e.g. `ResearchPlanTask.question`,
    # `.task_id`). Not yet hit in production, but the same restricted-
    # validation-keyword family as the two above -- stripped preemptively
    # rather than waiting for a third live 400 on the next schema that
    # happens to use one.
    "minLength",
    "maxLength",
    "pattern",
    "format",
    # Object/array bounds in the same family, unused today but equally
    # unsupported if a future schema adds them.
    "minProperties",
    "maxProperties",
    "uniqueItems",
)


def _strip_unsupported_claude_schema_keywords(schema: Any) -> Any:
    """
    Claude's native structured-output schema (`output_config.format`) only
    accepts a narrow, structural subset of JSON Schema -- the same
    restricted family OpenAI's "strict" structured outputs enforces.
    Pydantic's `model_json_schema()` emits ordinary JSON Schema validation
    keywords the API rejects outright as soon as it sees one (confirmed
    for array and numeric bounds; see `_CLAUDE_UNSUPPORTED_SCHEMA_KEYWORDS`
    for what's evidenced vs. preemptive), unlike every other provider's
    schema handling here. Recurses through every place a subschema can
    appear -- `properties`, `items`, `$defs` (pydantic's nested-model
    location), and `anyOf`/`oneOf`/`allOf` -- since the offending keys can
    sit at any nesting depth. Builds a new structure rather than mutating
    in place, so `request.output_schema` itself (used unmodified by output
    validation and other providers) is untouched.
    """

    if isinstance(schema, dict):
        cleaned = {
            key: _strip_unsupported_claude_schema_keywords(value)
            for key, value in schema.items()
            if key not in _CLAUDE_UNSUPPORTED_SCHEMA_KEYWORDS
        }
        return cleaned

    if isinstance(schema, list):
        return [_strip_unsupported_claude_schema_keywords(item) for item in schema]

    return schema


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
            "schema": _strip_unsupported_claude_schema_keywords(request.output_schema),
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
