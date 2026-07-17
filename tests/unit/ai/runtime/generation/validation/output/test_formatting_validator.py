"""
Unit tests for FormattingValidator.

Covers:
- Plain text responses are not checked (nothing to violate)
- Markdown with balanced code fences passes
- Markdown with an unbalanced code fence count is an ERROR
- Well-formed XML passes
- XML with multiple sibling root elements (no single root) still passes
  via the wrap-and-retry fallback
- Malformed XML is an ERROR
- JSON/STRUCTURED formats are left alone (JsonValidator's job)
"""

from __future__ import annotations

from app.ai.runtime.generation.enums import ResponseFormat
from app.ai.runtime.generation.validation.models import ValidationSeverity
from app.ai.runtime.generation.validation.output.formatting_validator import (
    FormattingValidator,
)

from tests.unit.ai.runtime.generation.validation.factories import make_request, make_result

validator = FormattingValidator()


async def test_text_format_is_not_checked() -> None:
    result = make_result(
        request=make_request(response_format=ResponseFormat.TEXT),
        content="anything ``` at all",
    )

    outcome = await validator.validate(result)

    assert outcome.issues == []
    assert outcome.score is None


async def test_balanced_markdown_fences_pass() -> None:
    result = make_result(
        request=make_request(response_format=ResponseFormat.MARKDOWN),
        content="# Title\n\n```python\nprint('hi')\n```\n",
    )

    outcome = await validator.validate(result)

    assert outcome.issues == []
    assert outcome.score == 1.0


async def test_unbalanced_markdown_fences_are_an_error() -> None:
    result = make_result(
        request=make_request(response_format=ResponseFormat.MARKDOWN),
        content="```python\nprint('hi')\n",
    )

    outcome = await validator.validate(result)

    assert len(outcome.issues) == 1
    assert outcome.issues[0].severity == ValidationSeverity.ERROR
    assert outcome.score == 0.0


async def test_well_formed_xml_passes() -> None:
    result = make_result(
        request=make_request(response_format=ResponseFormat.XML),
        content="<report><summary>hi</summary></report>",
    )

    outcome = await validator.validate(result)

    assert outcome.issues == []


async def test_multiple_root_elements_pass_via_wrap_fallback() -> None:
    result = make_result(
        request=make_request(response_format=ResponseFormat.XML),
        content="<section>one</section><section>two</section>",
    )

    outcome = await validator.validate(result)

    assert outcome.issues == []


async def test_malformed_xml_is_an_error() -> None:
    result = make_result(
        request=make_request(response_format=ResponseFormat.XML),
        content="<report><summary>unclosed",
    )

    outcome = await validator.validate(result)

    assert len(outcome.issues) == 1
    assert outcome.issues[0].severity == ValidationSeverity.ERROR


async def test_json_format_is_left_to_json_validator() -> None:
    result = make_result(
        request=make_request(response_format=ResponseFormat.JSON),
        content="not even json",
    )

    outcome = await validator.validate(result)

    assert outcome.issues == []
    assert outcome.score is None
