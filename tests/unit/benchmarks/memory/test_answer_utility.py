from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

from benchmarks.memory.answer_utility import (
    MemoryAnswerPair,
    MemoryAnswerPairs,
    MemoryUtilityJudgment,
    score_answer_pairs,
)
from benchmarks.memory.dataset import MemoryEvaluationDataset, MemoryEvaluationQuery


@pytest.mark.asyncio
async def test_scores_paired_memory_utility_and_harm() -> None:
    dataset = MemoryEvaluationDataset(
        name="test",
        version="1",
        queries=[
            MemoryEvaluationQuery(
                query_id="q",
                query="How should you answer?",
                category="exact_recall",
                relevant_memory_ids=["m"],
                allowed_memory_ids=["m"],
                reference_answer="A concise answer.",
                answer_rubric="Honor the user's concise-answer preference.",
            )
        ],
    )
    pairs = MemoryAnswerPairs(
        candidate="policy",
        version="sha",
        dataset_version="1",
        pairs=[
            MemoryAnswerPair(
                query_id="q",
                answer_without_memory="A long generic answer.",
                answer_with_memory="A concise answer.",
            )
        ],
    )
    judge = AsyncMock()
    judge.evaluate.return_value = MemoryUtilityJudgment(
        reason="Memory improved personalization without harming correctness.",
        correctness_without=0.8,
        correctness_with=0.9,
        personalization_without=0.2,
        personalization_with=1.0,
        evidence_quality_without=0.8,
        evidence_quality_with=0.8,
        irrelevant_memory_harm=0,
    )

    report = await score_answer_pairs(dataset=dataset, pairs=pairs, judge=judge)

    assert report.candidates[0].metrics["memory_utility"] == 0.3
    assert report.candidates[0].metrics["irrelevant_memory_harm"] == 0
    assert report.candidates[0].notes["per_query"]["q"]["reason"].startswith("Memory improved")
    judge.evaluate.assert_awaited_once()


@pytest.mark.asyncio
async def test_answer_pair_ids_must_match_dataset() -> None:
    dataset = MemoryEvaluationDataset(
        name="test",
        version="1",
        queries=[
            MemoryEvaluationQuery(
                query_id="q",
                query="query",
                category="none",
                relevant_memory_ids=[],
                allowed_memory_ids=[],
            )
        ],
    )
    pairs = MemoryAnswerPairs(candidate="policy", version="sha", dataset_version="1", pairs=[])

    with pytest.raises(ValueError, match="must match"):
        await score_answer_pairs(dataset=dataset, pairs=pairs, judge=AsyncMock())
