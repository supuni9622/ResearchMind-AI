"""
Unit tests for benchmarks/generation/langsmith_sync.py (E19).

No live LangSmith calls -- `get_langsmith_client` is monkeypatched to
return a `MagicMock`/`None`, matching this repo's established
`get_langsmith_client` test pattern (see
tests/unit/ai/observability/providers/langsmith/test_client.py).
"""

from __future__ import annotations

import uuid
from unittest.mock import MagicMock

import pytest

from benchmarks.generation import langsmith_sync
from benchmarks.generation.golden_dataset import (
    Difficulty,
    ExpectedBehavior,
    GoldenDataset,
    GoldenExample,
    QueryType,
    Workflow,
)


def _make_example(**overrides: object) -> GoldenExample:
    defaults: dict[str, object] = {
        "example_id": "g1",
        "question": "What is X?",
        "reference_answer": "X is Y.",
        "reference_context_ids": ["paper.pdf"],
        "expected_citation_ids": ["paper.pdf"],
        "expected_behavior": ExpectedBehavior.ANSWER,
        "query_type": QueryType.FACTUAL,
        "difficulty": Difficulty.EASY,
        "workflow": Workflow.LINEAR_RESEARCH,
        "contexts": ["X is Y, according to the paper."],
    }
    defaults.update(overrides)
    return GoldenExample(**defaults)


def test_example_id_to_langsmith_id_is_deterministic() -> None:
    first = langsmith_sync.example_id_to_langsmith_id("g42")
    second = langsmith_sync.example_id_to_langsmith_id("g42")

    assert first == second
    assert isinstance(first, uuid.UUID)


def test_example_id_to_langsmith_id_differs_across_examples() -> None:
    assert langsmith_sync.example_id_to_langsmith_id(
        "g1"
    ) != langsmith_sync.example_id_to_langsmith_id("g2")


def test_to_langsmith_example_maps_answerable_example() -> None:
    example = _make_example()

    mapped = langsmith_sync.to_langsmith_example(example)

    assert mapped["id"] == langsmith_sync.example_id_to_langsmith_id("g1")
    assert mapped["inputs"] == {
        "question": "What is X?",
        "contexts": ["X is Y, according to the paper."],
    }
    assert mapped["outputs"]["reference_answer"] == "X is Y."
    assert mapped["outputs"]["expected_behavior"] == "answer"
    assert mapped["metadata"]["query_type"] == "factual"
    assert mapped["metadata"]["difficulty"] == "easy"
    assert mapped["metadata"]["workflow"] == "linear_research"
    assert mapped["metadata"]["example_id"] == "g1"


def test_to_langsmith_example_maps_unanswerable_example_with_no_context() -> None:
    example = _make_example(
        example_id="u1",
        question="What is the GDP of Japan?",
        reference_answer=None,
        reference_context_ids=[],
        expected_citation_ids=[],
        expected_behavior=ExpectedBehavior.ABSTAIN,
        query_type=QueryType.UNANSWERABLE,
        workflow=Workflow.CHAT,
        contexts=[],
    )

    mapped = langsmith_sync.to_langsmith_example(example)

    assert mapped["inputs"]["contexts"] == []
    assert mapped["outputs"]["reference_answer"] is None
    assert mapped["outputs"]["expected_behavior"] == "abstain"


async def test_sync_raises_when_langsmith_not_configured(monkeypatch) -> None:
    monkeypatch.setattr(langsmith_sync, "get_langsmith_client", lambda: None)

    with pytest.raises(langsmith_sync.LangSmithNotConfiguredError):
        langsmith_sync.sync_golden_dataset(
            dataset=GoldenDataset(version="1.0", examples=[_make_example()])
        )


async def test_sync_creates_dataset_when_it_does_not_exist_yet(monkeypatch) -> None:
    client = MagicMock()
    client.has_dataset.return_value = False
    monkeypatch.setattr(langsmith_sync, "get_langsmith_client", lambda: client)

    dataset = GoldenDataset(version="1.0", examples=[_make_example()])
    count = langsmith_sync.sync_golden_dataset(dataset=dataset)

    assert count == 1
    client.create_dataset.assert_called_once()
    assert client.create_dataset.call_args.args[0] == langsmith_sync.DATASET_NAME
    client.create_examples.assert_called_once()
    assert client.create_examples.call_args.kwargs["dataset_name"] == langsmith_sync.DATASET_NAME
    assert len(client.create_examples.call_args.kwargs["examples"]) == 1


async def test_sync_skips_dataset_creation_when_it_already_exists(monkeypatch) -> None:
    client = MagicMock()
    client.has_dataset.return_value = True
    monkeypatch.setattr(langsmith_sync, "get_langsmith_client", lambda: client)

    dataset = GoldenDataset(version="1.0", examples=[_make_example()])
    langsmith_sync.sync_golden_dataset(dataset=dataset)

    client.create_dataset.assert_not_called()
    client.create_examples.assert_called_once()


async def test_sync_is_idempotent_across_repeated_runs(monkeypatch) -> None:
    """
    Running the sync twice must produce identical example IDs both times
    -- this is what makes create_examples() an upsert rather than an
    append, per E19's own idempotency requirement.
    """

    client = MagicMock()
    client.has_dataset.return_value = True
    monkeypatch.setattr(langsmith_sync, "get_langsmith_client", lambda: client)

    dataset = GoldenDataset(
        version="1.0", examples=[_make_example(), _make_example(example_id="g2")]
    )

    langsmith_sync.sync_golden_dataset(dataset=dataset)
    first_ids = [e["id"] for e in client.create_examples.call_args.kwargs["examples"]]

    langsmith_sync.sync_golden_dataset(dataset=dataset)
    second_ids = [e["id"] for e in client.create_examples.call_args.kwargs["examples"]]

    assert first_ids == second_ids


async def test_sync_defaults_to_loading_dataset_from_disk(monkeypatch) -> None:
    client = MagicMock()
    client.has_dataset.return_value = True
    monkeypatch.setattr(langsmith_sync, "get_langsmith_client", lambda: client)

    count = langsmith_sync.sync_golden_dataset()

    assert count >= 50  # rag_answer_gold.json has 115 examples as of E1's growth pass
