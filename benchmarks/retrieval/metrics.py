"""
Retrieval evaluation metrics.

These metrics operate on document-level relevance judgments: a ranked
list of retrieved chunk filenames (duplicates allowed, since multiple
chunks from the same document may be retrieved) is first collapsed to a
ranked list of unique documents by first occurrence, then compared
against the set of filenames judged relevant for the query.

All functions are pure and framework-independent so they can be unit
tested without a running retrieval stack.
"""

from __future__ import annotations

import math


def _ranked_unique_documents(
    retrieved_filenames: list[str],
) -> list[str]:
    """
    Collapse a ranked (possibly duplicate-containing) filename list into
    a ranked list of unique documents, ordered by first occurrence.
    """

    seen: set[str] = set()
    unique: list[str] = []

    for filename in retrieved_filenames:
        if filename not in seen:
            seen.add(filename)
            unique.append(filename)

    return unique


def recall_at_k(
    retrieved_filenames: list[str],
    relevant_filenames: set[str],
    k: int,
) -> float:
    """
    Fraction of relevant documents found within the top-k retrieved
    chunks.
    """

    if not relevant_filenames:
        return 0.0

    retrieved_at_k = set(_ranked_unique_documents(retrieved_filenames)[:k])

    return len(retrieved_at_k & relevant_filenames) / len(relevant_filenames)


def precision_at_k(
    retrieved_filenames: list[str],
    relevant_filenames: set[str],
    k: int,
) -> float:
    """
    Fraction of the top-k retrieved documents that are relevant.
    """

    if k <= 0:
        return 0.0

    retrieved_at_k = set(_ranked_unique_documents(retrieved_filenames)[:k])

    return len(retrieved_at_k & relevant_filenames) / k


def reciprocal_rank(
    retrieved_filenames: list[str],
    relevant_filenames: set[str],
) -> float:
    """
    Reciprocal rank of the first relevant document.

    Returns 0.0 if no relevant document was retrieved.
    """

    for rank, filename in enumerate(
        _ranked_unique_documents(retrieved_filenames),
        start=1,
    ):
        if filename in relevant_filenames:
            return 1.0 / rank

    return 0.0


def ndcg_at_k(
    retrieved_filenames: list[str],
    relevant_filenames: set[str],
    k: int,
) -> float:
    """
    Normalized Discounted Cumulative Gain within the top-k retrieved
    documents, using binary relevance (a document is either relevant or
    it isn't -- this dataset has no graded relevance judgments).

    Unlike recall/precision, NDCG is rank-sensitive: a relevant document
    at rank 1 contributes more than the same document at rank 5. This is
    what makes it (along with MRR) the right metric for measuring a
    reranker's effect on ordering, as opposed to recall, which only
    cares whether a relevant document is present in the top-k at all.
    """

    if not relevant_filenames or k <= 0:
        return 0.0

    ranked = _ranked_unique_documents(retrieved_filenames)[:k]

    dcg = sum(
        1.0 / math.log2(rank + 1)
        for rank, filename in enumerate(ranked, start=1)
        if filename in relevant_filenames
    )

    ideal_hits = min(len(relevant_filenames), k)
    idcg = sum(1.0 / math.log2(rank + 1) for rank in range(1, ideal_hits + 1))

    if idcg == 0:
        return 0.0

    return dcg / idcg
