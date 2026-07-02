"""
Interfaces for the metadata enrichment platform.

Metadata providers enrich the canonical ProcessedDocument with
additional metadata extracted from various sources such as PDF
metadata, language detection, or external services.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path

from app.ai.knowledge.processing.enums import DocumentFormat
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

    @property
    @abstractmethod
    def supported_formats(self) -> set[DocumentFormat]:
        """
        Document formats this provider knows how to enrich.
        """

    def supports(
        self,
        document_format: DocumentFormat,
    ) -> bool:
        """
        Returns whether the provider supports the supplied format.
        """

        return document_format in self.supported_formats

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
