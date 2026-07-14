"""
Reranking exceptions.
"""


class RerankingError(Exception):
    """
    Base reranking exception.
    """


class RerankingProviderNotFoundError(
    RerankingError,
):
    """
    Raised when provider cannot be resolved.
    """


class RerankingValidationError(
    RerankingError,
):
    """
    Raised when request is invalid.
    """
