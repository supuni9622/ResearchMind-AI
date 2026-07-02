"""
Interfaces for the metadata enrichment platform.

Metadata providers enrich the canonical ProcessedDocument with
additional metadata extracted from various sources such as PDF
metadata, language detection, or external services.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path

from app.ai.knowledge.processing.metadata.models import MetadataUpdate
from app.ai.knowledge.processing.models import ProcessedDocument


class MetadataProvider(ABC):
    """
    Contract implemented by every metadata provider.
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
    ) -> MetadataUpdate:
        """
        Enrich a processed document with additional metadata.

        Providers must never mutate the supplied ProcessedDocument.

        The file_path refers to the temporary local file created by the
        processing pipeline.
        """
