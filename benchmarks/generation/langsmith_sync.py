"""
Sync `rag_answer_gold` (E1's golden dataset) to LangSmith as a Dataset,
per EVALUATION_IMPLEMENTATION_TRACKER.md E19.

Source-of-truth decision (E19's own subtask list, resolved here rather
than left implicit): `datasets/golden/rag_answer_gold.json` stays
canonical -- this module only ever pushes to LangSmith, never reads it
back into the JSON file. Keeps the dataset reviewable in PRs like every
other dataset file in this repo (`retrieval_queries.json`/
`generation_queries.json`/etc. are all version-controlled JSON), rather
than making a third-party UI the source of truth for something this
project's own commit history needs to track.

Idempotent by design: each `GoldenExample.example_id` (e.g. "g42") maps
to a deterministic LangSmith example `id` via `uuid5`, so re-running this
after editing or growing the dataset upserts existing examples in place
instead of creating duplicates -- required per E19's own acceptance
criteria.
"""

from __future__ import annotations

import uuid
from pathlib import Path
from typing import Any

import structlog
from app.ai.observability.providers.langsmith.client import get_langsmith_client

from benchmarks.generation.golden_dataset import (
    GoldenDataset,
    GoldenExample,
    load_golden_dataset,
)

logger = structlog.get_logger()

GOLDEN_DATASET_PATH = (
    Path(__file__).resolve().parents[2] / "datasets" / "golden" / "rag_answer_gold.json"
)

DATASET_NAME = "rag_answer_gold"

# Fixed, arbitrary namespace UUID for deriving deterministic per-example
# LangSmith IDs from `example_id` -- must never change once real syncs
# have run, or every example would get a new ID and duplicate rather
# than upsert.
_ID_NAMESPACE = uuid.UUID("6f6e6570-6465-6e73-6974-792d6578616d")


class LangSmithNotConfiguredError(RuntimeError):
    pass


def example_id_to_langsmith_id(example_id: str) -> uuid.UUID:
    """Deterministic mapping from `GoldenExample.example_id` to a stable UUID."""

    return uuid.uuid5(_ID_NAMESPACE, example_id)


def to_langsmith_example(example: GoldenExample) -> dict[str, Any]:
    """
    Map one `GoldenExample` onto LangSmith's `inputs`/`outputs`/`metadata`
    example shape. Everything not naturally an input (the question) or an
    output (what a correct response looks like) goes into `metadata`, so
    LangSmith's own UI can filter/slice by `query_type`/`difficulty`/
    `workflow` -- the exact reporting need EVALUATION_PLAN.md §3 designed
    the per-example schema around.
    """

    return {
        "id": example_id_to_langsmith_id(example.example_id),
        "inputs": {
            "question": example.question,
            "contexts": example.contexts,
        },
        "outputs": {
            "reference_answer": example.reference_answer,
            "expected_behavior": example.expected_behavior.value,
            "expected_citation_ids": example.expected_citation_ids,
            "required_claims": example.required_claims,
            "forbidden_claims": example.forbidden_claims,
        },
        "metadata": {
            "example_id": example.example_id,
            "query_type": example.query_type.value,
            "difficulty": example.difficulty.value,
            "workflow": example.workflow.value,
            "reference_context_ids": example.reference_context_ids,
            "metadata_filters": example.metadata_filters,
            "rubric": example.rubric,
            "expected_tool": example.expected_tool,
            "expected_route": example.expected_route,
            "failure_category": example.failure_category,
        },
    }


def sync_golden_dataset(
    *,
    dataset: GoldenDataset | None = None,
    dataset_name: str = DATASET_NAME,
) -> int:
    """
    Push every example in `dataset` (default: load `rag_answer_gold.json`
    from disk) to LangSmith as Dataset `dataset_name`, creating the
    dataset if it doesn't exist yet.

    Returns the number of examples upserted.

    Raises:
        LangSmithNotConfiguredError: no `LANGSMITH_API_KEY` configured --
            callers should treat this the same as any other "LangSmith
            isn't wired up in this environment" case, not a hard failure.
    """

    client = get_langsmith_client()
    if client is None:
        raise LangSmithNotConfiguredError(
            f"LangSmith is not configured (LANGSMITH_API_KEY unset) -- cannot sync {dataset_name}."
        )

    if dataset is None:
        dataset = load_golden_dataset(GOLDEN_DATASET_PATH)

    if not client.has_dataset(dataset_name=dataset_name):
        client.create_dataset(
            dataset_name,
            description=(
                "ResearchMind's rag_answer_gold golden dataset (EVALUATION_PLAN.md §3). "
                "Canonical source is datasets/golden/rag_answer_gold.json in the "
                "ResearchMind-AI repo -- this LangSmith dataset is a synced mirror kept "
                "up to date by benchmarks/generation/langsmith_sync.py, not independently "
                "editable here."
            ),
        )
        logger.info("langsmith_sync.dataset_created", dataset_name=dataset_name)

    examples = [to_langsmith_example(example) for example in dataset.examples]
    client.create_examples(dataset_name=dataset_name, examples=examples)

    logger.info(
        "langsmith_sync.completed",
        dataset_name=dataset_name,
        example_count=len(examples),
    )
    return len(examples)


if __name__ == "__main__":
    synced_count = sync_golden_dataset()
    print(f"Synced {synced_count} examples to LangSmith dataset '{DATASET_NAME}'.")
