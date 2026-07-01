"""
Document parser registry.

The registry is responsible for registering parser implementations and
resolving the appropriate parser for a document format.

The processing pipeline depends on this registry rather than concrete
parser implementations.
"""

from __future__ import annotations

from collections.abc import Iterable

from app.ai.knowledge.processing.enums import DocumentFormat
from app.ai.knowledge.processing.exceptions import ParserNotFoundError
from app.ai.knowledge.processing.interfaces import DocumentParser


class ParserRegistry:
    """
    Registry for document parser implementations.
    """

    def __init__(
        self,
        parsers: Iterable[DocumentParser] | None = None,
    ) -> None:
        self._parsers: dict[DocumentFormat, DocumentParser] = {}

        if parsers:
            for parser in parsers:
                self.register(parser)

    def register(
        self,
        parser: DocumentParser,
    ) -> None:
        """
        Register a parser implementation.

        A parser is registered for every document format it supports.
        """

        for document_format in parser.supported_formats:
            self._parsers[document_format] = parser

    def get_parser(
        self,
        document_format: DocumentFormat,
    ) -> DocumentParser:
        """
        Return the parser responsible for the supplied document format.

        Raises:
            ParserNotFoundError
                If no parser has been registered.
        """

        parser = self._parsers.get(document_format)

        if parser is None:
            raise ParserNotFoundError(
                f"No parser registered for document format '{document_format.value}'."
            )

        return parser

    def supports(
        self,
        document_format: DocumentFormat,
    ) -> bool:
        """
        Returns whether a parser exists for the supplied format.
        """

        return document_format in self._parsers

    @property
    def supported_formats(self) -> set[DocumentFormat]:
        """
        Returns every supported document format.
        """

        return set(self._parsers.keys())

    @property
    def parsers(self) -> tuple[DocumentParser, ...]:
        """
        Returns all unique registered parser instances.
        """

        return tuple({id(parser): parser for parser in self._parsers.values()}.values())

    def __len__(self) -> int:
        """
        Number of supported document formats.
        """

        return len(self._parsers)

    def __contains__(
        self,
        document_format: DocumentFormat,
    ) -> bool:
        """
        Enables:

            if DocumentFormat.PDF in registry:
        """

        return self.supports(document_format)
