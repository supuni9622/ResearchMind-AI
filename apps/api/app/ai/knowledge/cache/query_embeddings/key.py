"""
Query embedding cache key generation.
"""

from __future__ import annotations

import hashlib

from app.ai.knowledge.embeddings.enums import (
    EmbeddingProvider,
)


def build_query_embedding_cache_key(
    *,
    provider: EmbeddingProvider,
    model: str,
    configuration_fingerprint: str,
    query: str,
) -> str:
    """
    Build stable cache key.
    """

    payload = "|".join(
        [
            provider.value,
            model,
            configuration_fingerprint,
            query.strip(),
        ]
    )

    return hashlib.sha256(
        payload.encode(
            "utf-8",
        )
    ).hexdigest()
