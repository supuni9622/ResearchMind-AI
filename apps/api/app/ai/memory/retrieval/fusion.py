"""
Memory Fusion (Retrieval Pipeline: Merge -> Deduplicate -> Rerank).

`MemoryService.search()` used to combine per-type result lists by
concatenating them and sorting the whole thing by `importance_score`
alone -- which silently discarded Qdrant's own relevance ranking for
SEMANTIC/RESEARCH hits (a highly-relevant-but-low-importance memory
could get pushed below an irrelevant-but-high-importance one). Each
per-type list handed to `reciprocal_rank_fusion()` is already ranked
best-first by its own service (Qdrant similarity for SEMANTIC/
RESEARCH, recency for USER); this combines those rankings by position
rather than by raw, non-comparable scores (vector similarity and
importance_score aren't on the same scale) -- the same Reciprocal Rank
Fusion algorithm the Knowledge Platform's `RetrievalFusionService`
already uses for dense/sparse retrieval (see `retrieval/fusion/rrf.py`),
k=60 for the same reason (Cormack et al.; also Elasticsearch/Azure AI
Search's default).

Keying by `MemoryRecord.id` also gives deduplication for free.
"""

from __future__ import annotations

from collections import defaultdict
from uuid import UUID

from app.ai.memory.models import MemoryRecord

_DEFAULT_K = 60


def reciprocal_rank_fusion(
    result_lists: list[list[MemoryRecord]],
    *,
    k: int = _DEFAULT_K,
) -> list[MemoryRecord]:
    """
    Fuse multiple best-first-ranked `MemoryRecord` lists into one,
    ranked by combined reciprocal rank. Ties (including a record
    appearing in only one list) break on `importance_score` descending.
    """

    scores: dict[UUID, float] = defaultdict(float)
    records: dict[UUID, MemoryRecord] = {}

    for result_list in result_lists:
        for rank, record in enumerate(result_list, start=1):
            scores[record.id] += 1 / (k + rank)
            records[record.id] = record

    ranked_ids = sorted(
        scores,
        key=lambda record_id: (scores[record_id], records[record_id].importance_score),
        reverse=True,
    )

    return [records[record_id] for record_id in ranked_ids]
