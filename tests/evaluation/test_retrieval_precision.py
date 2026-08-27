"""
Retrieval metric completeness contract (EVALUATION_PLAN.md §5, §18 Level 1).

Unlike `tests/unit/benchmarks/retrieval/test_metrics.py` (isolated,
hand-constructed inputs per function), this exercises the full metric
set -- Recall@K, Precision@K, NDCG@K, Hit Rate@K, MRR -- against the real
benchmark query dataset
(`benchmarks/datasets/research-papers/retrieval_queries.json`), checking
the set is complete and internally consistent. This is the "did we wire
every metric up correctly, on real data" check; the unit tests are the
"is each formula correct in isolation" check.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from benchmarks.retrieval.dataset import load_retrieval_queries
from benchmarks.retrieval.metrics import (
    hit_rate_at_k,
    ndcg_at_k,
    precision_at_k,
    recall_at_k,
    reciprocal_rank,
)

QUERY_DATASET_PATH = (
    Path(__file__).resolve().parents[2]
    / "benchmarks"
    / "datasets"
    / "research-papers"
    / "retrieval_queries.json"
)


@pytest.fixture(scope="module")
def golden_queries() -> list[tuple[str, set[str]]]:
    """
    Every benchmark query paired with its ground-truth relevant document
    set, loaded from the real dataset rather than a hand-built fixture.
    """

    dataset = load_retrieval_queries(QUERY_DATASET_PATH)

    return [(query.query, set(query.relevant_documents)) for query in dataset.queries]


def test_query_dataset_is_non_empty(golden_queries: list[tuple[str, set[str]]]) -> None:
    assert len(golden_queries) > 0


def test_every_query_has_at_least_one_relevant_document(
    golden_queries: list[tuple[str, set[str]]],
) -> None:
    for query, relevant in golden_queries:
        assert relevant, f"query has no relevant documents: {query!r}"


@pytest.mark.parametrize("k", [5, 10])
def test_metric_set_is_complete_and_bounded(
    golden_queries: list[tuple[str, set[str]]],
    k: int,
) -> None:
    """
    Every metric in EVALUATION_PLAN.md §5's table is computable against
    real query data and stays within its valid [0, 1] range -- a
    regression here (e.g. a metric raising on real data, or drifting
    outside bounds) means the metric set is no longer complete/correct,
    which is exactly what this file is the named home for catching.
    """

    for _, relevant in golden_queries:
        # A perfect retrieval (every relevant document ranked first)
        # exercises the metrics against real relevance-judgment shapes
        # without depending on a live retrieval stack.
        retrieved = sorted(relevant)

        for metric_fn in (recall_at_k, precision_at_k, ndcg_at_k, hit_rate_at_k):
            score = metric_fn(retrieved, relevant, k)
            assert 0.0 <= score <= 1.0

        assert 0.0 <= reciprocal_rank(retrieved, relevant) <= 1.0


def test_perfect_retrieval_scores_recall_and_hit_rate_at_one(
    golden_queries: list[tuple[str, set[str]]],
) -> None:
    for _, relevant in golden_queries:
        retrieved = sorted(relevant)

        assert recall_at_k(retrieved, relevant, k=len(retrieved)) == pytest.approx(1.0)
        assert hit_rate_at_k(retrieved, relevant, k=len(retrieved)) == 1.0


def test_hit_rate_is_never_below_recall(
    golden_queries: list[tuple[str, set[str]]],
) -> None:
    """
    Hit Rate@K is the more forgiving, binary sibling of Recall@K's
    fractional score -- for any given retrieval, Hit Rate can never be
    lower than Recall (finding *some* relevant documents always means
    finding *at least one*).
    """

    for _, relevant in golden_queries:
        retrieved = sorted(relevant) + ["distractor.pdf"]

        for k in (5, 10):
            assert hit_rate_at_k(retrieved, relevant, k) >= recall_at_k(retrieved, relevant, k)


def test_empty_retrieval_scores_zero_across_the_metric_set(
    golden_queries: list[tuple[str, set[str]]],
) -> None:
    for _, relevant in golden_queries:
        for metric_fn in (recall_at_k, precision_at_k, ndcg_at_k, hit_rate_at_k):
            assert metric_fn([], relevant, 10) == 0.0

        assert reciprocal_rank([], relevant) == 0.0
