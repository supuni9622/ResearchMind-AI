"""
Unit tests for RerankingBenchmark's pure helper functions.

Covers:
- _build_candidate aggregates recall/MRR/NDCG/latency correctly and
  only attaches an "error" note when one occurred
- _build_summary reports each reranker's delta over the hybrid_only
  baseline, and is skipped for candidates with zero evaluated queries
  (e.g. Voyage AI not configured)
"""

from __future__ import annotations

from benchmarks.reranking.benchmark import (
    FINAL_K,
    NDCG_K,
    POOL_SIZE,
    RECALL_K,
    _build_candidate,
    _build_summary,
)


def test_build_candidate_aggregates_metrics() -> None:
    candidate = _build_candidate(
        name="hybrid_only",
        recall_scores=[1.0, 0.0],
        reciprocal_ranks=[1.0, 0.5],
        ndcg_scores=[1.0, 0.5],
        latencies_ms=[10.0, 20.0],
        cost_model="free",
        error=None,
    )

    assert candidate.name == "hybrid_only"
    assert candidate.metrics["queries_evaluated"] == 2
    assert candidate.metrics[f"recall_at_{RECALL_K}"] == 0.5
    assert candidate.metrics["mrr"] == 0.75
    assert candidate.metrics[f"ndcg_at_{NDCG_K}"] == 0.75
    assert candidate.metrics["avg_latency_ms"] == 15.0
    assert candidate.notes["final_k"] == FINAL_K
    assert candidate.notes["pool_size"] == POOL_SIZE
    assert "error" not in candidate.notes


def test_build_candidate_attaches_error_note_when_provided() -> None:
    candidate = _build_candidate(
        name="hybrid_voyage",
        recall_scores=[1.0],
        reciprocal_ranks=[1.0],
        ndcg_scores=[1.0],
        latencies_ms=[10.0],
        cost_model="paid",
        error="rate limited",
    )

    assert candidate.notes["error"] == "rate limited"


def test_build_summary_reports_deltas_over_baseline() -> None:
    baseline = _build_candidate(
        name="hybrid_only",
        recall_scores=[1.0],
        reciprocal_ranks=[0.5],
        ndcg_scores=[0.5],
        latencies_ms=[100.0],
        cost_model="free",
        error=None,
    )
    reranked = _build_candidate(
        name="hybrid_cross_encoder",
        recall_scores=[1.0],
        reciprocal_ranks=[1.0],
        ndcg_scores=[1.0],
        latencies_ms=[120.0],
        cost_model="free",
        error=None,
    )

    summary = _build_summary([baseline, reranked])

    assert summary[f"hybrid_cross_encoder_recall_at_{RECALL_K}_delta"] == 0.0
    assert summary["hybrid_cross_encoder_mrr_delta"] == 0.5
    assert summary[f"hybrid_cross_encoder_ndcg_at_{NDCG_K}_delta"] == 0.5
    assert summary["hybrid_cross_encoder_latency_overhead_ms"] == 20.0


def test_build_summary_skips_candidates_with_no_evaluated_queries() -> None:
    baseline = _build_candidate(
        name="hybrid_only",
        recall_scores=[1.0],
        reciprocal_ranks=[1.0],
        ndcg_scores=[1.0],
        latencies_ms=[100.0],
        cost_model="free",
        error=None,
    )
    skipped_voyage = _build_candidate(
        name="hybrid_voyage",
        recall_scores=[],
        reciprocal_ranks=[],
        ndcg_scores=[],
        latencies_ms=[],
        cost_model="paid",
        error=None,
    )

    summary = _build_summary([baseline, skipped_voyage])

    assert "hybrid_voyage_mrr_delta" not in summary


def test_build_summary_returns_empty_without_a_baseline() -> None:
    reranked = _build_candidate(
        name="hybrid_cross_encoder",
        recall_scores=[1.0],
        reciprocal_ranks=[1.0],
        ndcg_scores=[1.0],
        latencies_ms=[100.0],
        cost_model="free",
        error=None,
    )

    assert _build_summary([reranked]) == {}
