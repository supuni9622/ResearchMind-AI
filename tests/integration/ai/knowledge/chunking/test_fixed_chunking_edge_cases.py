"""
Edge case integration tests for the Fixed Chunking Provider.

These tests verify that the Fixed Chunking implementation behaves
correctly under unusual or boundary conditions.

Unlike the main pipeline integration test, these tests focus on
correctness, robustness, and deterministic behaviour.
"""

from __future__ import annotations

from uuid import uuid4

import pytest
from app.ai.knowledge.chunking.enums import ChunkingStrategy
from app.ai.knowledge.chunking.exceptions import ChunkingValidationError
from app.ai.knowledge.chunking.factory import create_chunking_service
from app.ai.knowledge.chunking.providers.fixed import FixedChunkingProvider
from app.ai.knowledge.processing.enums import (
    DocumentFormat,
    ParserType,
)
from app.ai.knowledge.processing.models import (
    DocumentMetadata,
    DocumentStatistics,
    ProcessedDocument,
)


def build_document(text: str) -> ProcessedDocument:
    """
    Create a minimal ProcessedDocument for testing.
    """

    return ProcessedDocument(
        document_id=uuid4(),
        filename="test-document.pdf",
        format=DocumentFormat.PDF,
        parser=ParserType.DOCLING,
        metadata=DocumentMetadata(
            title="Chunking Test Document",
            source="test-document.pdf",
        ),
        statistics=DocumentStatistics(),
        raw_text=text,
        markdown="",
        blocks=[],
    )


@pytest.mark.asyncio
async def test_empty_document_raises_validation_error() -> None:
    """
    Empty documents should be rejected before chunking.
    """

    service = create_chunking_service()

    with pytest.raises(ChunkingValidationError):
        await service.chunk(
            document=build_document(""),
            strategy=ChunkingStrategy.FIXED,
        )


@pytest.mark.asyncio
async def test_whitespace_document_raises_validation_error() -> None:
    """
    Whitespace-only documents should be rejected before chunking.
    """

    service = create_chunking_service()

    with pytest.raises(ChunkingValidationError):
        await service.chunk(
            document=build_document("   \n\n\t   "),
            strategy=ChunkingStrategy.FIXED,
        )


@pytest.mark.asyncio
async def test_document_smaller_than_chunk_size_returns_single_chunk() -> None:
    """
    A document smaller than the configured chunk size should
    produce exactly one chunk.
    """

    service = create_chunking_service()

    text = "ResearchMind is awesome."

    chunks = await service.chunk(
        document=build_document(text),
        strategy=ChunkingStrategy.FIXED,
    )

    assert len(chunks) == 1

    chunk = chunks[0]

    assert chunk.index == 0
    assert chunk.total_chunks == 1
    assert chunk.content.text == text


@pytest.mark.asyncio
async def test_unicode_document_is_preserved() -> None:
    """
    Unicode characters should survive chunking.
    """

    service = create_chunking_service()

    text = "සිංහල தமிழ் 日本語 English 😀🚀 " * 100

    chunks = await service.chunk(
        document=build_document(text),
        strategy=ChunkingStrategy.FIXED,
    )

    assert chunks

    reconstructed = "".join(chunk.content.text for chunk in chunks)

    assert "සිංහල" in reconstructed
    assert "தமிழ்" in reconstructed
    assert "日本語" in reconstructed
    assert "😀" in reconstructed


@pytest.mark.asyncio
async def test_markdown_document_chunks_successfully() -> None:
    """
    Fixed chunking should also work for markdown documents.
    """

    service = create_chunking_service()

    markdown = (
        "# ResearchMind\n\n"
        "## Chunking\n\n"
        "This is a paragraph.\n\n"
        "- Item One\n"
        "- Item Two\n\n"
        "```python\n"
        'print("Hello")\n'
        "```\n\n"
    ) * 40

    chunks = await service.chunk(
        document=build_document(markdown),
        strategy=ChunkingStrategy.FIXED,
    )

    assert len(chunks) > 0

    assert chunks[0].content.text


@pytest.mark.asyncio
async def test_large_document_chunks_successfully() -> None:
    """
    Large documents should be chunked successfully.
    """

    service = create_chunking_service()

    text = "Artificial Intelligence " * 5000

    chunks = await service.chunk(
        document=build_document(text),
        strategy=ChunkingStrategy.FIXED,
    )

    assert len(chunks) > 50

    assert chunks[-1].index == len(chunks) - 1


@pytest.mark.asyncio
async def test_chunk_order_is_preserved() -> None:
    """
    Chunk indices should remain sequential.
    """

    service = create_chunking_service()

    text = "ABCDEFGHIJKLMNOPQRSTUVWXYZ " * 300

    chunks = await service.chunk(
        document=build_document(text),
        strategy=ChunkingStrategy.FIXED,
    )

    for index, chunk in enumerate(chunks):
        assert chunk.index == index


@pytest.mark.asyncio
async def test_chunk_ids_are_unique() -> None:
    """
    Every generated chunk should have a unique UUID.
    """

    service = create_chunking_service()

    text = "ResearchMind " * 500

    chunks = await service.chunk(
        document=build_document(text),
        strategy=ChunkingStrategy.FIXED,
    )

    ids = {chunk.id for chunk in chunks}

    assert len(ids) == len(chunks)


@pytest.mark.asyncio
async def test_chunk_statistics_are_generated() -> None:
    """
    Every chunk should contain generated statistics.
    """

    service = create_chunking_service()

    text = "Statistics are important for evaluating chunk quality. " * 300

    chunks = await service.chunk(
        document=build_document(text),
        strategy=ChunkingStrategy.FIXED,
    )

    assert chunks

    for chunk in chunks:
        assert chunk.statistics.character_count > 0
        assert chunk.statistics.word_count > 0
        assert chunk.statistics.estimated_token_count > 0
        assert chunk.statistics.average_token_length > 0


@pytest.mark.asyncio
async def test_overlap_is_preserved() -> None:
    """
    Consecutive chunks should overlap by the configured number of characters.
    """

    service = create_chunking_service()

    provider = service._registry.get(
        ChunkingStrategy.FIXED,
    )

    assert isinstance(provider, FixedChunkingProvider)

    overlap = provider.config.chunk_overlap

    text = "ABCDEFGHIJKLMNOPQRSTUVWXYZ " * 300

    chunks = await service.chunk(
        document=build_document(text),
        strategy=ChunkingStrategy.FIXED,
    )

    assert len(chunks) > 1

    for previous, current in zip(chunks, chunks[1:], strict=False):
        assert previous.content.text[-overlap:] == current.content.text[:overlap]


@pytest.mark.asyncio
async def test_total_chunk_count_is_consistent() -> None:
    """
    Every chunk should report the same total chunk count.
    """

    service = create_chunking_service()

    chunks = await service.chunk(
        document=build_document("ResearchMind " * 1000),
        strategy=ChunkingStrategy.FIXED,
    )

    total_chunks = len(chunks)

    for chunk in chunks:
        assert chunk.total_chunks == total_chunks
