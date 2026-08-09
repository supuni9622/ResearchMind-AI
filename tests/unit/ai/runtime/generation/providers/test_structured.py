"""
Unit tests for `app.ai.runtime.generation.providers.helpers.structured`.

Covers:
- `_strip_unsupported_claude_schema_keywords()` removes every JSON Schema
  validation keyword Claude's `output_config.format` rejects (array
  bounds, numeric bounds, string bounds/pattern/format, object bounds) at
  every nesting depth (`properties`, `items`, `$defs`, `anyOf`/`oneOf`/
  `allOf`), while leaving structural/descriptive keywords (`type`,
  `title`, `description`, `default`, `enum`, `required`,
  `additionalProperties`) untouched.
- `build_claude_output_config()` only builds a schema-constrained config
  for STRUCTURED requests with an `output_schema`, and never mutates the
  caller's `request.output_schema` in place.
- `_require_every_property()` forces every object schema's `required` to
  list every key in its own `properties` (OpenAI's `text.format:
  json_schema` strict mode requires this even for pydantic fields that
  have a default), at every nesting depth, without mutating the caller's
  schema.
- `build_openai_text_config()` applies that same requirement, and still
  handles JSON mode / no-schema the same as before.
"""

from __future__ import annotations

from app.ai.knowledge.context.models import PromptContext
from app.ai.runtime.generation.enums import ResponseFormat
from app.ai.runtime.generation.models import GenerationRequest
from app.ai.runtime.generation.providers.helpers.structured import (
    _require_every_property,
    _strip_unsupported_claude_schema_keywords,
    build_claude_output_config,
    build_ollama_format,
    build_openai_text_config,
)


def _make_request(
    *,
    response_format: ResponseFormat = ResponseFormat.TEXT,
    output_schema: dict | None = None,
) -> GenerationRequest:
    return GenerationRequest(
        prompt_context=PromptContext(context="retrieved context", chunks=[]),
        user_prompt="hello",
        response_format=response_format,
        output_schema=output_schema,
    )


def test_build_ollama_format_uses_json_mode_for_complex_structured_schema() -> None:
    schema = {
        "$defs": {"Task": {"type": "object"}},
        "properties": {
            "task": {"$ref": "#/$defs/Task"},
            "note": {"anyOf": [{"type": "string"}, {"type": "null"}]},
        },
        "type": "object",
    }
    request = _make_request(
        response_format=ResponseFormat.STRUCTURED,
        output_schema=schema,
    )

    assert build_ollama_format(request) == "json"
    assert request.output_schema == schema


def test_build_ollama_format_returns_none_for_text() -> None:
    request = _make_request(response_format=ResponseFormat.TEXT)

    assert build_ollama_format(request) is None


def test_strip_removes_min_and_max_items_from_a_top_level_array() -> None:
    schema = {"type": "array", "items": {"type": "string"}, "minItems": 1, "maxItems": 8}

    cleaned = _strip_unsupported_claude_schema_keywords(schema)

    assert cleaned == {"type": "array", "items": {"type": "string"}}


def test_strip_recurses_into_defs_properties_and_nested_items() -> None:
    schema = {
        "$defs": {
            "Task": {
                "type": "object",
                "properties": {
                    "dependencies": {
                        "type": "array",
                        "items": {"type": "string"},
                        "maxItems": 8,
                    }
                },
            }
        },
        "properties": {
            "tasks": {
                "type": "array",
                "items": {"$ref": "#/$defs/Task"},
                "minItems": 1,
                "maxItems": 8,
            }
        },
    }

    cleaned = _strip_unsupported_claude_schema_keywords(schema)

    assert "maxItems" not in cleaned["properties"]["tasks"]
    assert "minItems" not in cleaned["properties"]["tasks"]
    assert "maxItems" not in cleaned["$defs"]["Task"]["properties"]["dependencies"]
    assert cleaned["properties"]["tasks"]["items"] == {"$ref": "#/$defs/Task"}


def test_strip_recurses_into_any_of_one_of_all_of() -> None:
    schema = {
        "anyOf": [
            {"type": "array", "items": {"type": "string"}, "maxItems": 3},
            {"type": "null"},
        ]
    }

    cleaned = _strip_unsupported_claude_schema_keywords(schema)

    assert cleaned["anyOf"][0] == {"type": "array", "items": {"type": "string"}}
    assert cleaned["anyOf"][1] == {"type": "null"}


def test_strip_removes_numeric_bounds() -> None:
    """Regression: production hit this exact rejection ("properties maximum,
    minimum are not supported") right after the maxItems fix shipped --
    `ResearchPlanTask.priority` uses `Field(ge=1, le=5)`."""

    schema = {
        "type": "integer",
        "minimum": 1,
        "maximum": 5,
        "exclusiveMinimum": 0,
        "exclusiveMaximum": 6,
        "multipleOf": 1,
    }

    cleaned = _strip_unsupported_claude_schema_keywords(schema)

    assert cleaned == {"type": "integer"}


def test_strip_removes_string_and_object_bounds() -> None:
    schema = {
        "type": "string",
        "minLength": 1,
        "maxLength": 1_000,
        "pattern": "^[a-z]+$",
        "format": "email",
        "minProperties": 1,
        "maxProperties": 5,
        "uniqueItems": True,
        "description": "a field",
    }

    cleaned = _strip_unsupported_claude_schema_keywords(schema)

    assert cleaned == {"type": "string", "description": "a field"}


def test_strip_preserves_structural_and_descriptive_keywords() -> None:
    schema = {
        "type": "object",
        "title": "Widget",
        "description": "a field",
        "default": None,
        "enum": ["a", "b"],
        "required": ["a"],
        "additionalProperties": False,
    }

    cleaned = _strip_unsupported_claude_schema_keywords(schema)

    assert cleaned == schema


def test_build_claude_output_config_returns_none_without_structured_format() -> None:
    request = _make_request(response_format=ResponseFormat.TEXT, output_schema={"type": "object"})

    assert build_claude_output_config(request) is None


def test_build_claude_output_config_returns_none_without_a_schema() -> None:
    request = _make_request(response_format=ResponseFormat.STRUCTURED, output_schema=None)

    assert build_claude_output_config(request) is None


def test_build_claude_output_config_strips_max_items_and_leaves_the_request_schema_untouched() -> (
    None
):
    schema = {
        "type": "object",
        "properties": {
            "tasks": {"type": "array", "items": {"type": "string"}, "maxItems": 8},
        },
    }
    request = _make_request(response_format=ResponseFormat.STRUCTURED, output_schema=schema)

    config = build_claude_output_config(request)

    assert config == {
        "format": {
            "type": "json_schema",
            "schema": {
                "type": "object",
                "properties": {"tasks": {"type": "array", "items": {"type": "string"}}},
            },
        }
    }
    assert request.output_schema is not None
    assert request.output_schema["properties"]["tasks"]["maxItems"] == 8


def test_require_every_property_adds_defaulted_fields_missing_from_required() -> None:
    """Regression: production hit exactly this rejection ("'required' is
    required to be supplied and to be an array including every key in
    properties. Missing 'dependencies'.") -- `ResearchPlanTask.dependencies`
    has `default_factory=list`, so pydantic leaves it out of `required`."""

    schema = {
        "type": "object",
        "properties": {
            "task_id": {"type": "string"},
            "dependencies": {"type": "array", "items": {"type": "string"}},
        },
        "required": ["task_id"],
    }

    cleaned = _require_every_property(schema)

    assert cleaned["required"] == ["task_id", "dependencies"]


def test_require_every_property_recurses_into_defs_and_items() -> None:
    schema = {
        "$defs": {
            "Task": {
                "type": "object",
                "properties": {"task_id": {"type": "string"}, "priority": {"type": "integer"}},
                "required": ["task_id"],
            }
        },
        "type": "object",
        "properties": {
            "tasks": {"type": "array", "items": {"$ref": "#/$defs/Task"}},
            "goal": {"type": "string"},
        },
        "required": ["goal"],
    }

    cleaned = _require_every_property(schema)

    assert cleaned["required"] == ["tasks", "goal"]
    assert cleaned["$defs"]["Task"]["required"] == ["task_id", "priority"]


def test_require_every_property_leaves_non_object_schemas_untouched() -> None:
    schema = {"type": "array", "items": {"type": "string"}}

    assert _require_every_property(schema) == schema


def test_build_openai_text_config_returns_none_without_structured_format() -> None:
    request = _make_request(response_format=ResponseFormat.TEXT, output_schema={"type": "object"})

    assert build_openai_text_config(request) is None


def test_build_openai_text_config_returns_json_object_mode_for_plain_json() -> None:
    request = _make_request(response_format=ResponseFormat.JSON, output_schema=None)

    assert build_openai_text_config(request) == {"format": {"type": "json_object"}}


def test_build_openai_text_config_fills_required_and_leaves_the_request_schema_untouched() -> None:
    schema = {
        "type": "object",
        "properties": {"goal": {"type": "string"}, "limitations": {"type": "array"}},
        "required": ["goal"],
    }
    request = _make_request(response_format=ResponseFormat.STRUCTURED, output_schema=schema)

    config = build_openai_text_config(request)

    assert config == {
        "format": {
            "type": "json_schema",
            "name": "response",
            "schema": {
                "type": "object",
                "properties": {"goal": {"type": "string"}, "limitations": {"type": "array"}},
                "required": ["goal", "limitations"],
            },
        }
    }
    assert request.output_schema is not None
    assert request.output_schema["required"] == ["goal"]
