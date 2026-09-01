"""
Unit tests for QdrantRetrievalProvider._build_filter.

Covers:
- owner_id is always required and always produces a must-condition, even
  when no additional filters are supplied (PRODUCTION_READINESS_EVALUATION.md
  item 5: an unscoped, cross-tenant query must be structurally impossible)
- project_id is always present too (omitted -> an IsNullCondition
  restricting to personal/non-project documents, not "every project" --
  same omit=personal-only contract as the rest of the Project workspace
  feature; set -> an exact-match FieldCondition)
- Additional recognized filter keys each produce their own must-condition
- document_id values are coerced to str before being matched
- Unrecognized filter keys are ignored and contribute no conditions
- Falsy additional filter values (e.g. empty string) are treated as absent,
  matching the provider's `if value:` guard -- this does not apply to
  owner_id, which is always included regardless
"""

from __future__ import annotations

import uuid
from typing import cast
from unittest.mock import AsyncMock

from app.ai.knowledge.retrieval.config import QdrantRetrievalConfig
from app.ai.knowledge.retrieval.providers.qdrant import QdrantRetrievalProvider
from qdrant_client.models import FieldCondition, Filter, IsNullCondition, MatchValue


def create_provider() -> QdrantRetrievalProvider:
    return QdrantRetrievalProvider(
        client=AsyncMock(),
        config=QdrantRetrievalConfig(),
    )


def _field_conditions(result: Filter) -> list[FieldCondition]:
    """Narrow `Filter.must` down to just the `FieldCondition` entries,
    ignoring the mandatory project_id `IsNullCondition` present whenever
    `project_id` isn't explicitly set."""

    assert isinstance(result.must, list)

    return cast(
        list[FieldCondition],
        [condition for condition in result.must if isinstance(condition, FieldCondition)],
    )


def _match_value(condition: FieldCondition) -> object:
    assert isinstance(condition.match, MatchValue)

    return condition.match.value


def _has_project_id_is_null(result: Filter) -> bool:
    assert isinstance(result.must, list)

    return any(
        isinstance(condition, IsNullCondition) and condition.is_null.key == "project_id"
        for condition in result.must
    )


def test_owner_id_alone_produces_a_single_field_condition() -> None:
    provider = create_provider()

    result = provider._build_filter(owner_id="abc", filters={})

    conditions = _field_conditions(result)
    assert len(conditions) == 1
    assert conditions[0].key == "owner_id"
    assert _match_value(conditions[0]) == "abc"


def test_omitted_project_id_produces_an_is_null_condition() -> None:
    """The omit=personal-only contract: no `project_id` arg means "match
    documents with no project_id in their payload", not "any project"."""

    provider = create_provider()

    result = provider._build_filter(owner_id="abc", filters={})

    assert _has_project_id_is_null(result)


def test_explicit_project_id_produces_an_exact_match_field_condition() -> None:
    provider = create_provider()
    project_id = str(uuid.uuid4())

    result = provider._build_filter(owner_id="abc", project_id=project_id, filters={})

    conditions = _field_conditions(result)
    assert {condition.key for condition in conditions} == {"owner_id", "project_id"}
    project_condition = next(c for c in conditions if c.key == "project_id")
    assert _match_value(project_condition) == project_id
    assert not _has_project_id_is_null(result)


def test_multiple_filters_alongside_owner_id() -> None:
    provider = create_provider()

    result = provider._build_filter(
        owner_id="abc",
        filters={
            "language": "en",
        },
    )

    conditions = _field_conditions(result)
    assert len(conditions) == 2
    assert {condition.key for condition in conditions} == {"owner_id", "language"}


def test_document_id_filter_is_coerced_to_string() -> None:
    provider = create_provider()
    document_id = uuid.uuid4()

    result = provider._build_filter(
        owner_id="abc",
        filters={
            "document_id": document_id,
        },
    )

    conditions = _field_conditions(result)
    assert {condition.key for condition in conditions} == {"owner_id", "document_id"}
    document_condition = next(c for c in conditions if c.key == "document_id")
    assert _match_value(document_condition) == str(document_id)


def test_unsupported_filter_key_is_ignored() -> None:
    provider = create_provider()

    result = provider._build_filter(
        owner_id="abc",
        filters={
            "unsupported_key": "value",
        },
    )

    conditions = _field_conditions(result)
    assert len(conditions) == 1
    assert conditions[0].key == "owner_id"


def test_falsy_additional_filter_value_is_treated_as_absent() -> None:
    provider = create_provider()

    result = provider._build_filter(
        owner_id="abc",
        filters={
            "filename": "",
        },
    )

    conditions = _field_conditions(result)
    assert len(conditions) == 1
    assert conditions[0].key == "owner_id"
