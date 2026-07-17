from __future__ import annotations


class RoutingError(Exception):
    pass


class NoEligibleModelsError(
    RoutingError,
):
    """
    Raised when capability and policy filtering leave no candidate
    models for a strategy to score.
    """

    pass
