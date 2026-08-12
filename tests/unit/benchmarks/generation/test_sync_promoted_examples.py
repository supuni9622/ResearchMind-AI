"""
Unit tests for `sync_promoted_examples.py` (E10, EVALUATION_PLAN.md
§3/§15).

Covers:
- build_golden_example() maps a confirmed PromotionReview's fields onto
  GoldenExample directly (no translation)
- sync() appends "good" promotions to rag_answer_gold.json and
  "failure" promotions to production_failures.json, assigning distinct
  p<N>/pf<N> ids
- Already-synced/unconfirmed rows are never touched
- mark_synced() is called for every synced row
"""

from __future__ import annotations

import json
import uuid
from datetime import UTC, datetime
from pathlib import Path
from unittest.mock import AsyncMock

import pytest
from app.models.promotion_review import PromotionReview

from benchmarks.generation.sync_promoted_examples import build_golden_example, sync


def _review(**overrides: object) -> PromotionReview:
    defaults: dict[str, object] = {
        "id": uuid.uuid4(),
        "source": "human_feedback",
        "direction": "good",
        "owner_id": uuid.uuid4(),
        "generation_id": uuid.uuid4(),
        "status": "confirmed",
        "reviewed_by": uuid.uuid4(),
        "reviewed_at": datetime.now(UTC),
        "question": "What is X?",
        "reference_answer": "X is a thing.",
        "contexts": ["X is described here."],
        "reference_context_ids": ["doc.pdf"],
        "expected_citation_ids": ["doc.pdf"],
        "query_type": "factual",
        "difficulty": "easy",
        "workflow": "chat",
        "rubric": None,
        "failure_category": None,
        "synced": False,
        "synced_at": None,
    }
    defaults.update(overrides)
    return PromotionReview(**defaults)


def test_build_golden_example_maps_fields_directly() -> None:
    review = _review(question="What is X?", reference_answer="X is a thing.")

    example = build_golden_example(review, example_id="p1")

    assert example.example_id == "p1"
    assert example.question == "What is X?"
    assert example.reference_answer == "X is a thing."
    assert example.contexts == ["X is described here."]
    assert example.query_type.value == "factual"
    assert example.difficulty.value == "easy"
    assert example.workflow.value == "chat"


def test_build_golden_example_carries_failure_category() -> None:
    review = _review(direction="failure", failure_category="wrong_citation")

    example = build_golden_example(review, example_id="pf1")

    assert example.failure_category == "wrong_citation"


def _write_dataset(path: Path, *, notes: str = "") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"version": "1.0", "notes": notes, "examples": []}))


@pytest.mark.asyncio
async def test_sync_appends_good_promotion_to_golden_dataset(tmp_path: Path) -> None:
    golden_path = tmp_path / "golden" / "rag_answer_gold.json"
    failures_path = tmp_path / "production_failures" / "production_failures.json"
    _write_dataset(golden_path)

    review = _review(direction="good")
    repository = AsyncMock()
    repository.list_confirmed_unsynced.return_value = [review]

    good_count, failure_count = await sync(
        repository=repository,
        golden_dataset_path=golden_path,
        production_failures_path=failures_path,
    )

    assert good_count == 1
    assert failure_count == 0
    repository.mark_synced.assert_awaited_once_with(review.id)

    written = json.loads(golden_path.read_text())
    assert len(written["examples"]) == 1
    assert written["examples"][0]["example_id"] == "p1"
    assert not failures_path.exists()


@pytest.mark.asyncio
async def test_sync_appends_failure_promotion_to_production_failures(tmp_path: Path) -> None:
    golden_path = tmp_path / "golden" / "rag_answer_gold.json"
    failures_path = tmp_path / "production_failures" / "production_failures.json"
    _write_dataset(golden_path)

    review = _review(direction="failure", failure_category="hallucination")
    repository = AsyncMock()
    repository.list_confirmed_unsynced.return_value = [review]

    good_count, failure_count = await sync(
        repository=repository,
        golden_dataset_path=golden_path,
        production_failures_path=failures_path,
    )

    assert good_count == 0
    assert failure_count == 1

    written = json.loads(failures_path.read_text())
    assert len(written["examples"]) == 1
    assert written["examples"][0]["example_id"] == "pf1"
    assert written["examples"][0]["failure_category"] == "hallucination"

    # rag_answer_gold.json itself must be untouched -- no good promotions.
    golden_written = json.loads(golden_path.read_text())
    assert golden_written["examples"] == []


@pytest.mark.asyncio
async def test_sync_assigns_distinct_ids_avoiding_existing_ones(tmp_path: Path) -> None:
    golden_path = tmp_path / "golden" / "rag_answer_gold.json"
    failures_path = tmp_path / "production_failures" / "production_failures.json"
    golden_path.parent.mkdir(parents=True, exist_ok=True)
    golden_path.write_text(
        json.dumps(
            {
                "version": "1.0",
                "notes": "",
                "examples": [
                    {
                        "example_id": "p1",
                        "question": "existing",
                        "query_type": "factual",
                        "difficulty": "easy",
                        "workflow": "chat",
                        "expected_behavior": "answer",
                        "contexts": ["x"],
                    }
                ],
            }
        )
    )

    review = _review(direction="good")
    repository = AsyncMock()
    repository.list_confirmed_unsynced.return_value = [review]

    await sync(
        repository=repository,
        golden_dataset_path=golden_path,
        production_failures_path=failures_path,
    )

    written = json.loads(golden_path.read_text())
    ids = {example["example_id"] for example in written["examples"]}
    assert ids == {"p1", "p2"}


@pytest.mark.asyncio
async def test_sync_is_a_noop_when_nothing_is_confirmed(tmp_path: Path) -> None:
    golden_path = tmp_path / "golden" / "rag_answer_gold.json"
    failures_path = tmp_path / "production_failures" / "production_failures.json"
    _write_dataset(golden_path)

    repository = AsyncMock()
    repository.list_confirmed_unsynced.return_value = []

    good_count, failure_count = await sync(
        repository=repository,
        golden_dataset_path=golden_path,
        production_failures_path=failures_path,
    )

    assert (good_count, failure_count) == (0, 0)
    repository.mark_synced.assert_not_awaited()
