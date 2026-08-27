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


def _make_client(*, has_dataset: bool, existing_ids: list[uuid.UUID] | None = None) -> MagicMock:
    client = MagicMock()
    client.has_dataset.return_value = has_dataset
    client.list_examples.return_value = [
        MagicMock(id=example_id) for example_id in (existing_ids or [])
    ]
    return client


async def test_sync_raises_when_langsmith_not_configured(monkeypatch) -> None:
    monkeypatch.setattr(langsmith_sync, "get_langsmith_client", lambda: None)

    with pytest.raises(langsmith_sync.LangSmithNotConfiguredError):
        langsmith_sync.sync_golden_dataset(
            dataset=GoldenDataset(version="1.0", examples=[_make_example()])
        )


async def test_sync_creates_dataset_when_it_does_not_exist_yet(monkeypatch) -> None:
    client = _make_client(has_dataset=False)
    monkeypatch.setattr(langsmith_sync, "get_langsmith_client", lambda: client)

    dataset = GoldenDataset(version="1.0", examples=[_make_example()])
    count = langsmith_sync.sync_golden_dataset(dataset=dataset)

    assert count == 1
    client.create_dataset.assert_called_once()
    assert client.create_dataset.call_args.args[0] == langsmith_sync.DATASET_NAME


async def test_sync_skips_dataset_creation_when_it_already_exists(monkeypatch) -> None:
    client = _make_client(has_dataset=True)
    monkeypatch.setattr(langsmith_sync, "get_langsmith_client", lambda: client)

    dataset = GoldenDataset(version="1.0", examples=[_make_example()])
    langsmith_sync.sync_golden_dataset(dataset=dataset)

    client.create_dataset.assert_not_called()


async def test_sync_calls_create_examples_for_ids_not_already_in_the_dataset(monkeypatch) -> None:
    client = _make_client(has_dataset=True, existing_ids=[])
    monkeypatch.setattr(langsmith_sync, "get_langsmith_client", lambda: client)

    dataset = GoldenDataset(version="1.0", examples=[_make_example()])
    langsmith_sync.sync_golden_dataset(dataset=dataset)

    client.create_examples.assert_called_once()
    assert client.create_examples.call_args.kwargs["dataset_name"] == langsmith_sync.DATASET_NAME
    assert len(client.create_examples.call_args.kwargs["examples"]) == 1
    client.update_examples.assert_not_called()


async def test_sync_calls_update_examples_for_ids_already_in_the_dataset(monkeypatch) -> None:
    """
    Regression test: a real live run against LangSmith found that
    `create_examples()` 409s (does not silently upsert) when an `id`
    already exists in the dataset -- confirmed by actually re-running the
    sync twice against a real account, not assumed from the SDK's
    `UpsertExamplesResponse` return-type name (misleading -- that shape
    is shared with a different, deprecated method). Real idempotency on
    this SDK version requires routing already-present ids through
    `update_examples()` instead.
    """

    existing_id = langsmith_sync.example_id_to_langsmith_id("g1")
    client = _make_client(has_dataset=True, existing_ids=[existing_id])
    monkeypatch.setattr(langsmith_sync, "get_langsmith_client", lambda: client)

    dataset = GoldenDataset(version="1.0", examples=[_make_example()])
    langsmith_sync.sync_golden_dataset(dataset=dataset)

    client.create_examples.assert_not_called()
    client.update_examples.assert_called_once()
    assert client.update_examples.call_args.kwargs["dataset_name"] == langsmith_sync.DATASET_NAME
    updates = client.update_examples.call_args.kwargs["updates"]
    assert len(updates) == 1
    assert updates[0]["id"] == existing_id


async def test_sync_splits_mixed_new_and_existing_ids_correctly(monkeypatch) -> None:
    existing_id = langsmith_sync.example_id_to_langsmith_id("g1")
    client = _make_client(has_dataset=True, existing_ids=[existing_id])
    monkeypatch.setattr(langsmith_sync, "get_langsmith_client", lambda: client)

    dataset = GoldenDataset(
        version="1.0", examples=[_make_example(), _make_example(example_id="g2")]
    )
    langsmith_sync.sync_golden_dataset(dataset=dataset)

    assert len(client.create_examples.call_args.kwargs["examples"]) == 1
    assert client.create_examples.call_args.kwargs["examples"][0][
        "id"
    ] == langsmith_sync.example_id_to_langsmith_id("g2")
    assert len(client.update_examples.call_args.kwargs["updates"]) == 1
    assert client.update_examples.call_args.kwargs["updates"][0]["id"] == existing_id


async def test_sync_is_idempotent_across_repeated_runs(monkeypatch) -> None:
    """
    Running the sync twice must not raise and must route the second run's
    examples through update_examples (not create_examples again) -- this
    is what makes re-running the sync after editing/growing the dataset
    safe, per E19's own idempotency requirement. Uses a stateful fake
    that tracks which ids exist, mirroring what a real dataset does.
    """

    stored_ids: set[uuid.UUID] = set()
    client = MagicMock()
    client.has_dataset.return_value = True
    client.list_examples.side_effect = lambda **_: [MagicMock(id=i) for i in stored_ids]

    def _record_created(*, dataset_name: str, examples: list[dict]) -> None:
        stored_ids.update(example["id"] for example in examples)

    client.create_examples.side_effect = _record_created
    monkeypatch.setattr(langsmith_sync, "get_langsmith_client", lambda: client)

    dataset = GoldenDataset(
        version="1.0", examples=[_make_example(), _make_example(example_id="g2")]
    )

    langsmith_sync.sync_golden_dataset(dataset=dataset)
    assert client.create_examples.call_count == 1
    assert client.update_examples.call_count == 0

    langsmith_sync.sync_golden_dataset(dataset=dataset)
    assert client.create_examples.call_count == 1  # not called again
    assert client.update_examples.call_count == 1  # both ids now routed here
    assert len(client.update_examples.call_args.kwargs["updates"]) == 2


async def test_sync_defaults_to_loading_dataset_from_disk(monkeypatch) -> None:
    client = _make_client(has_dataset=True, existing_ids=[])
    monkeypatch.setattr(langsmith_sync, "get_langsmith_client", lambda: client)

    count = langsmith_sync.sync_golden_dataset()

    assert count >= 50  # rag_answer_gold.json has 115 examples as of E1's growth pass
