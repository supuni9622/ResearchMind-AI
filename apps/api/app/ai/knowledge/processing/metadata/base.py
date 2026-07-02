"""
Base implementation for metadata providers.

Concrete metadata providers should inherit from this class instead of
implementing the MetadataProvider interface directly.
"""

from __future__ import annotations

from abc import ABC

from app.ai.knowledge.processing.metadata.interfaces import MetadataProvider


class BaseMetadataProvider(
    MetadataProvider,
    ABC,
):
    """
    Base class for metadata providers.

    Provides a common inheritance point for all metadata providers.
    """

    pass
