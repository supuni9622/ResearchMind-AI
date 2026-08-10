"""
Unit tests for MetadataFilteringBenchmark's pure helper functions.

Covers:
- Queries whose relevant documents all share one owner are evaluable;
  queries spanning multiple owners are skipped (a single equality filter
  cannot select more than one owner at a time)
- The summary reports leakage_rate per candidate. There is no unfiltered
  baseline to diff against: RetrievalQuery.owner_id is a required field
  (PRODUCTION_READINESS_EVALUATION.md item 5), so an unscoped query is no
  longer constructible.
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


def test_build_summary_reports_leakage_rate_per_candidate() -> None:
    candidates = [
        _make_candidate(
            "dense",
            precision_at_5=1.0,
            avg_latency_ms=120.0,
            leakage_rate=0.0,
        ),
        _make_candidate(
            "sparse",
            precision_at_5=0.9,
            avg_latency_ms=80.0,
            leakage_rate=0.0,
        ),
    ]

    summary = _build_summary(candidates, skipped_queries=2)

    assert summary["skipped_queries"] == 2
    assert summary["dense_leakage_rate"] == 0.0
    assert summary["sparse_leakage_rate"] == 0.0


def test_build_summary_with_no_candidates_reports_only_skipped_queries() -> None:
    summary = _build_summary([], skipped_queries=0)

    assert summary == {"skipped_queries": 0}
