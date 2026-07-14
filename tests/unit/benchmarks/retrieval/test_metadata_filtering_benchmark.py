"""
Unit tests for MetadataFilteringBenchmark's pure helper functions.

Covers:
- Queries whose relevant documents all share one owner are evaluable;
  queries spanning multiple owners are skipped (a single equality filter
  cannot select more than one owner at a time)
- The unfiltered vs. filtered summary reports precision delta, latency
  overhead, and leakage_rate per strategy
- Strategies missing either their filtered or unfiltered candidate are
  omitted from the summary rather than raising
"""

from __future__ import annotations

from benchmarks.models.report import BenchmarkCandidate
from benchmarks.retrieval.dataset import RetrievalBenchmarkQuery
from benchmarks.retrieval.metadata_filtering_benchmark import (
    _build_summary,
    _partition_by_owner_consistency,
)


def _make_query(query_id: str, relevant_documents: list[str]) -> RetrievalBenchmarkQuery:
    return RetrievalBenchmarkQuery(
        query_id=query_id,
        query="what is rag?",
        category="semantic",
        relevant_documents=relevant_documents,
    )


def test_partition_separates_single_owner_from_mixed_owner_queries() -> None:
    owner_by_filename = {
        "a.pdf": "owner-1",
        "b.pdf": "owner-1",
        "c.pdf": "owner-2",
    }
    single_owner_query = _make_query("q1", ["a.pdf", "b.pdf"])
    mixed_owner_query = _make_query("q2", ["a.pdf", "c.pdf"])

    evaluable, skipped = _partition_by_owner_consistency(
        [single_owner_query, mixed_owner_query],
        owner_by_filename,
    )

    assert evaluable == [single_owner_query]
    assert skipped == [mixed_owner_query]


def test_partition_with_all_single_document_queries_skips_none() -> None:
    owner_by_filename = {"a.pdf": "owner-1", "b.pdf": "owner-2"}
    queries = [_make_query("q1", ["a.pdf"]), _make_query("q2", ["b.pdf"])]

    evaluable, skipped = _partition_by_owner_consistency(queries, owner_by_filename)

    assert evaluable == queries
    assert skipped == []


def _make_candidate(name: str, **metrics: float) -> BenchmarkCandidate:
    return BenchmarkCandidate(name=name, metrics=metrics)


def test_build_summary_reports_deltas_per_strategy() -> None:
    candidates = [
        _make_candidate(
            "dense_unfiltered",
            precision_at_5=0.2,
            avg_latency_ms=100.0,
            leakage_rate=0.0,
        ),
        _make_candidate(
            "dense_filtered",
            precision_at_5=1.0,
            avg_latency_ms=120.0,
            leakage_rate=0.0,
        ),
    ]

    summary = _build_summary(candidates, skipped_queries=2)

    assert summary["skipped_queries"] == 2
    assert summary["dense_precision_at_5_delta"] == 0.8
    assert summary["dense_latency_overhead_ms"] == 20.0
    assert summary["dense_leakage_rate"] == 0.0
    assert "sparse_precision_at_5_delta" not in summary
    assert "hybrid_precision_at_5_delta" not in summary


def test_build_summary_omits_strategy_missing_a_candidate() -> None:
    candidates = [
        _make_candidate(
            "sparse_unfiltered",
            precision_at_5=0.2,
            avg_latency_ms=10.0,
            leakage_rate=0.0,
        ),
    ]

    summary = _build_summary(candidates, skipped_queries=0)

    assert "sparse_precision_at_5_delta" not in summary
    assert summary == {"skipped_queries": 0}
