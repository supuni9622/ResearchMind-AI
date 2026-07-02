"""
Interfaces for the statistics enrichment platform.

Statistics providers enrich the canonical DocumentStatistics with
additional measurements extracted from various document formats.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path

from app.ai.knowledge.processing.models import ProcessedDocument
from app.ai.knowledge.processing.statistics.models import (
    StatisticsUpdate,
)


class StatisticsProvider(ABC):
    """
    Contract implemented by every statistics provider.
    """

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """
        Human-readable provider name.
        """

    @abstractmethod
    async def enrich(
        self,
        *,
        document: ProcessedDocument,
        file_path: Path,
    ) -> StatisticsUpdate:
        """
        Extract statistics from the supplied document.

        Providers should return only the statistics they are responsible
        for.

        Providers must never mutate the supplied ProcessedDocument.
        """
