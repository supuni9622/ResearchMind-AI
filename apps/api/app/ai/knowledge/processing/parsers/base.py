"""
Base parser implementation.
"""

from __future__ import annotations

from abc import ABC

from app.ai.knowledge.processing.interfaces import DocumentParser


class BaseDocumentParser(DocumentParser, ABC):
    """
    Base class shared by all parser implementations.
    """

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(parser='{self.parser_name}')"

    def __str__(self) -> str:
        return self.parser_name
