"""Paper search cache key generation (mirrors
`app.ai.knowledge.cache.query_embeddings.key`)."""

from __future__ import annotations

import hashlib


def build_paper_search_cache_key(*, query: str, max_results: int) -> str:
    payload = "|".join([query.strip().lower(), str(max_results)])
    digest = hashlib.sha256(payload.encode("utf-8")).hexdigest()
    return f"paper_search:{digest}"
