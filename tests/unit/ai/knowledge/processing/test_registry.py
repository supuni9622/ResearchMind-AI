"""
Unit tests for ParserRegistry.

Covers:
- Empty registry state
- Registering a single-format parser
- Registering a multi-format parser
- Registering two parsers for disjoint formats
- Last-registered-wins for overlapping formats
- get_parser() raises ParserNotFoundError for unknown formats
- supports() / __contains__ / __len__
- supported_formats returns all registered formats
- parsers property deduplicates same instance registered under multiple formats
"""

from __future__ import annotations

import pytest
from app.ai.knowledge.processing.enums import DocumentFormat
from app.ai.knowledge.processing.exceptions import ParserNotFoundError
from app.ai.knowledge.processing.interfaces import DocumentParser, ParseRequest
from app.ai.knowledge.processing.models import ProcessedDocument
from app.ai.knowledge.processing.registry import ParserRegistry

# ---------------------------------------------------------------------------
# Fake parser
# ---------------------------------------------------------------------------


class FakeParser(DocumentParser):
    def __init__(self, name: str, formats: set[DocumentFormat]) -> None:
        self._name = name
        self._formats = formats

    @property
    def parser_name(self) -> str:
        return self._name

    @property
    def supported_formats(self) -> set[DocumentFormat]:
        return self._formats

    async def parse(self, request: ParseRequest) -> ProcessedDocument:  # pragma: no cover
        raise NotImplementedError


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def pdf_parser(name: str = "pdf-parser") -> FakeParser:
    return FakeParser(name, {DocumentFormat.PDF})


def multi_parser(name: str = "multi") -> FakeParser:
    return FakeParser(name, {DocumentFormat.PDF, DocumentFormat.DOCX})


# ---------------------------------------------------------------------------
# Empty registry
# ---------------------------------------------------------------------------


class TestEmptyRegistry:
    def test_len_is_zero(self) -> None:
        assert len(ParserRegistry()) == 0

    def test_supports_returns_false(self) -> None:
        assert not ParserRegistry().supports(DocumentFormat.PDF)

    def test_contains_returns_false(self) -> None:
        assert DocumentFormat.PDF not in ParserRegistry()

    def test_supported_formats_is_empty(self) -> None:
        assert ParserRegistry().supported_formats == set()

    def test_parsers_is_empty_tuple(self) -> None:
        assert ParserRegistry().parsers == ()

    def test_get_parser_raises_parser_not_found(self) -> None:
        with pytest.raises(ParserNotFoundError, match="pdf"):
            ParserRegistry().get_parser(DocumentFormat.PDF)


# ---------------------------------------------------------------------------
# Single-format parser
# ---------------------------------------------------------------------------


class TestSingleFormatParser:
    def setup_method(self) -> None:
        self.parser = pdf_parser()
        self.registry = ParserRegistry()
        self.registry.register(self.parser)

    def test_len_is_one(self) -> None:
        assert len(self.registry) == 1

    def test_supports_registered_format(self) -> None:
        assert self.registry.supports(DocumentFormat.PDF)

    def test_does_not_support_unregistered_format(self) -> None:
        assert not self.registry.supports(DocumentFormat.DOCX)

    def test_contains_registered_format(self) -> None:
        assert DocumentFormat.PDF in self.registry

    def test_get_parser_returns_correct_instance(self) -> None:
        assert self.registry.get_parser(DocumentFormat.PDF) is self.parser

    def test_get_parser_raises_for_unregistered_format(self) -> None:
        with pytest.raises(ParserNotFoundError):
            self.registry.get_parser(DocumentFormat.DOCX)

    def test_supported_formats_contains_pdf(self) -> None:
        assert self.registry.supported_formats == {DocumentFormat.PDF}

    def test_parsers_contains_one_instance(self) -> None:
        assert self.registry.parsers == (self.parser,)


# ---------------------------------------------------------------------------
# Multi-format parser
# ---------------------------------------------------------------------------


class TestMultiFormatParser:
    def setup_method(self) -> None:
        self.parser = multi_parser()
        self.registry = ParserRegistry()
        self.registry.register(self.parser)

    def test_len_equals_format_count(self) -> None:
        assert len(self.registry) == 2

    def test_both_formats_supported(self) -> None:
        assert self.registry.supports(DocumentFormat.PDF)
        assert self.registry.supports(DocumentFormat.DOCX)

    def test_get_parser_returns_same_instance_for_both(self) -> None:
        assert self.registry.get_parser(DocumentFormat.PDF) is self.parser
        assert self.registry.get_parser(DocumentFormat.DOCX) is self.parser

    def test_parsers_property_deduplicates_same_instance(self) -> None:
        # Same parser instance registered for 2 formats → still one unique instance.
        assert len(self.registry.parsers) == 1
        assert self.registry.parsers[0] is self.parser

    def test_supported_formats_returns_all(self) -> None:
        assert self.registry.supported_formats == {DocumentFormat.PDF, DocumentFormat.DOCX}


# ---------------------------------------------------------------------------
# Two disjoint parsers
# ---------------------------------------------------------------------------


class TestTwoDisjointParsers:
    def setup_method(self) -> None:
        self.pdf = FakeParser("pdf-parser", {DocumentFormat.PDF})
        self.txt = FakeParser("txt-parser", {DocumentFormat.TEXT})
        self.registry = ParserRegistry(parsers=[self.pdf, self.txt])

    def test_len_is_two(self) -> None:
        assert len(self.registry) == 2

    def test_each_format_resolves_to_correct_parser(self) -> None:
        assert self.registry.get_parser(DocumentFormat.PDF) is self.pdf
        assert self.registry.get_parser(DocumentFormat.TEXT) is self.txt

    def test_parsers_property_returns_both_instances(self) -> None:
        assert set(self.registry.parsers) == {self.pdf, self.txt}


# ---------------------------------------------------------------------------
# Last-registered-wins for overlapping formats
# ---------------------------------------------------------------------------


class TestOverlappingFormats:
    def test_second_registration_replaces_first(self) -> None:
        first = FakeParser("first", {DocumentFormat.PDF})
        second = FakeParser("second", {DocumentFormat.PDF})

        registry = ParserRegistry()
        registry.register(first)
        registry.register(second)

        assert registry.get_parser(DocumentFormat.PDF) is second

    def test_len_does_not_increase_for_same_format(self) -> None:
        registry = ParserRegistry()
        registry.register(FakeParser("a", {DocumentFormat.PDF}))
        registry.register(FakeParser("b", {DocumentFormat.PDF}))
        assert len(registry) == 1


# ---------------------------------------------------------------------------
# Constructor with parsers iterable
# ---------------------------------------------------------------------------


class TestConstructorWithParsers:
    def test_parsers_registered_at_construction(self) -> None:
        pdf = pdf_parser()
        registry = ParserRegistry(parsers=[pdf])
        assert registry.get_parser(DocumentFormat.PDF) is pdf

    def test_none_parsers_creates_empty_registry(self) -> None:
        registry = ParserRegistry(parsers=None)
        assert len(registry) == 0
