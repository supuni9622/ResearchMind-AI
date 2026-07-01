"""
Document parser registry.

The registry is responsible for registering parser implementations and
resolving the appropriate parser for a document format.

The processing pipeline depends on this registry rather than concrete
parser implementations.
"""

from __future__ import annotations

from collections.abc import Iterable

import structlog

from app.ai.knowledge.processing.enums import DocumentFormat
from app.ai.knowledge.processing.exceptions import ParserNotFoundError
from app.ai.knowledge.processing.interfaces import DocumentParser

logger = structlog.get_logger()


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
            previous = self._parsers.get(document_format)
            if previous is not None and previous is not parser:
                logger.warning(
                    "registry.parser_replaced",
                    document_format=document_format.value,
                    previous_parser=previous.parser_name,
                    new_parser=parser.parser_name,
                )
            self._parsers[document_format] = parser

        logger.debug(
            "registry.parser_registered",
            parser=parser.parser_name,
            formats=[f.value for f in parser.supported_formats],
        )

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
            logger.warning(
                "registry.parser_not_found",
                document_format=document_format.value,
                registered_formats=[f.value for f in self._parsers],
            )
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
