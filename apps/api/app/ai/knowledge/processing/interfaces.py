"""
Interfaces for the document processing module.

The processing pipeline depends only on these abstractions.
Concrete parser implementations (Docling, Unstructured, etc.)
must implement these contracts.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path
from uuid import UUID

from pydantic import BaseModel

from app.ai.knowledge.processing.enums import DocumentFormat
from app.ai.knowledge.processing.models import ProcessedDocument


class ParseRequest(BaseModel):
    """
    Request passed to every parser implementation.
    """

    document_id: UUID

    file_path: Path

    document_format: DocumentFormat


class DocumentParser(ABC):
    """
    Contract implemented by every parser.
    """

    @property
    @abstractmethod
    def parser_name(self) -> str:
        """
        Human-readable parser name.
        """

    @property
    @abstractmethod
    def supported_formats(self) -> set[DocumentFormat]:
        """
        Formats supported by this parser.
        """

    def supports(self, document_format: DocumentFormat) -> bool:
        """
        Returns whether the parser supports the supplied format.
        """
        return document_format in self.supported_formats

    @abstractmethod
    async def parse(
        self,
        request: ParseRequest,
    ) -> ProcessedDocument:
        """
        Parse a document into the canonical ProcessedDocument model.
        """
