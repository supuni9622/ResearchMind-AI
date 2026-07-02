"""
Base implementation for statistics providers.

Concrete statistics providers should inherit from this class instead
of implementing the StatisticsProvider interface directly.
"""

from __future__ import annotations

from abc import ABC

from app.ai.knowledge.processing.statistics.interfaces import (
    StatisticsProvider,
)


class BaseStatisticsProvider(
    StatisticsProvider,
    ABC,
):
    """
    Base class for statistics providers.

    Provides a common inheritance point for all statistics providers.
    """

    pass
