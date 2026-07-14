"""
Unit tests for QdrantRetrievalProvider._build_filter.

Covers:
- No filters supplied returns None (Qdrant treats this as "no filter")
- A single recognized filter key produces exactly one must-condition
- Multiple recognized filter keys each produce their own must-condition
- document_id values are coerced to str before being matched
- Unrecognized filter keys are ignored and contribute no conditions
- Falsy filter values (e.g. empty string) are treated as absent, matching
  the provider's `if value:` guard
"""

from __future__ import annotations

import uuid
from typing import cast
from unittest.mock import AsyncMock

from app.ai.knowledge.retrieval.config import QdrantRetrievalConfig
from app.ai.knowledge.retrieval.providers.qdrant import QdrantRetrievalProvider
from qdrant_client.models import FieldCondition, Filter, MatchValue


def create_provider() -> QdrantRetrievalProvider:
    return QdrantRetrievalProvider(
        client=AsyncMock(),
        config=QdrantRetrievalConfig(),
    )


def _must_conditions(result: Filter | None) -> list[FieldCondition]:
    """
    Narrow `Filter.must` (a broad condition union) down to the plain
    FieldCondition list that `_build_filter` is documented to produce.
    """

    assert result is not None
    assert isinstance(result.must, list)

    for condition in result.must:
        assert isinstance(condition, FieldCondition)

    return cast(list[FieldCondition], result.must)


def _match_value(condition: FieldCondition) -> object:
    assert isinstance(condition.match, MatchValue)

    return condition.match.value


def test_empty_filters() -> None:
    provider = create_provider()

    result = provider._build_filter({})

    assert result is None


def test_owner_filter() -> None:
    provider = create_provider()

    result = provider._build_filter(
        {
            "owner_id": "abc",
        }
    )

    conditions = _must_conditions(result)
    assert len(conditions) == 1
    assert conditions[0].key == "owner_id"
    assert _match_value(conditions[0]) == "abc"


def test_multiple_filters() -> None:
    provider = create_provider()

    result = provider._build_filter(
        {
            "owner_id": "abc",
            "language": "en",
        }
    )

    conditions = _must_conditions(result)
    assert len(conditions) == 2
    assert {condition.key for condition in conditions} == {"owner_id", "language"}


def test_document_id_filter_is_coerced_to_string() -> None:
    provider = create_provider()
    document_id = uuid.uuid4()

    result = provider._build_filter(
        {
            "document_id": document_id,
        }
    )

    conditions = _must_conditions(result)
    assert len(conditions) == 1
    assert conditions[0].key == "document_id"
    assert _match_value(conditions[0]) == str(document_id)


def test_unsupported_filter_key_is_ignored() -> None:
    provider = create_provider()

    result = provider._build_filter(
        {
            "unsupported_key": "value",
        }
    )

    assert result is None


def test_falsy_filter_value_is_treated_as_absent() -> None:
    provider = create_provider()

    result = provider._build_filter(
        {
            "owner_id": "",
        }
    )

    assert result is None
