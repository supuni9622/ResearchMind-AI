"""
Reranking Platform enumerations.
"""

from enum import StrEnum


class RerankingProvider(StrEnum):
    """
    Supported reranking providers.
    """

    CROSS_ENCODER = "cross_encoder"

    VOYAGE_AI = "voyage_ai"
