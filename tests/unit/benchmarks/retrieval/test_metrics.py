"""
Unit tests for retrieval benchmark metrics.

Covers:
- Recall@K counts each relevant document once even if multiple retrieved
  chunks come from the same document
- Recall@K only credits documents found within the top-k window
- Precision@K uses k (not the number of unique documents retrieved) as
  the denominator
- Reciprocal rank finds the first relevant document by rank, and returns
  0.0 when nothing relevant was retrieved
- Empty inputs do not raise (no relevant documents, no retrieved chunks)
"""

from __future__ import annotations

from benchmarks.retrieval.metrics import (
    precision_at_k,
    recall_at_k,
    reciprocal_rank,
)


def test_recall_at_k_counts_a_document_once_despite_duplicate_chunks() -> None:
    retrieved = ["a.pdf", "a.pdf", "a.pdf"]
    relevant = {"a.pdf"}

    assert recall_at_k(retrieved, relevant, k=5) == 1.0


def test_recall_at_k_only_credits_documents_within_the_window() -> None:
    retrieved = ["b.pdf", "c.pdf", "d.pdf", "e.pdf", "a.pdf"]
    relevant = {"a.pdf"}

    assert recall_at_k(retrieved, relevant, k=4) == 0.0
    assert recall_at_k(retrieved, relevant, k=5) == 1.0


def test_recall_at_k_averages_across_multiple_relevant_documents() -> None:
    retrieved = ["a.pdf", "x.pdf", "x.pdf"]
    relevant = {"a.pdf", "b.pdf"}

    assert recall_at_k(retrieved, relevant, k=3) == 0.5


def test_recall_at_k_with_no_relevant_documents_is_zero() -> None:
    assert recall_at_k(["a.pdf"], set(), k=5) == 0.0


def test_precision_at_k_uses_k_as_denominator_not_unique_hit_count() -> None:
    # Only 1 of 5 unique retrieved documents is relevant.
    retrieved = ["a.pdf", "b.pdf", "c.pdf", "d.pdf", "e.pdf"]
    relevant = {"a.pdf"}

    assert precision_at_k(retrieved, relevant, k=5) == 1 / 5


def test_precision_at_k_deduplicates_repeated_documents() -> None:
    # Same document repeated should not inflate precision.
    retrieved = ["a.pdf", "a.pdf", "a.pdf", "a.pdf", "a.pdf"]
    relevant = {"a.pdf"}

    assert precision_at_k(retrieved, relevant, k=5) == 1 / 5


def test_precision_at_k_with_zero_k_is_zero() -> None:
    assert precision_at_k(["a.pdf"], {"a.pdf"}, k=0) == 0.0


def test_reciprocal_rank_finds_first_relevant_document() -> None:
    retrieved = ["x.pdf", "y.pdf", "a.pdf", "a.pdf", "b.pdf"]
    relevant = {"a.pdf", "b.pdf"}

    # "a.pdf" first appears at unique-document rank 3.
    assert reciprocal_rank(retrieved, relevant) == 1 / 3


def test_reciprocal_rank_when_first_result_is_relevant() -> None:
    retrieved = ["a.pdf", "b.pdf"]
    relevant = {"a.pdf"}

    assert reciprocal_rank(retrieved, relevant) == 1.0


def test_reciprocal_rank_returns_zero_when_nothing_relevant_retrieved() -> None:
    retrieved = ["x.pdf", "y.pdf"]
    relevant = {"a.pdf"}

    assert reciprocal_rank(retrieved, relevant) == 0.0


def test_reciprocal_rank_with_no_retrieved_documents_is_zero() -> None:
    assert reciprocal_rank([], {"a.pdf"}) == 0.0
