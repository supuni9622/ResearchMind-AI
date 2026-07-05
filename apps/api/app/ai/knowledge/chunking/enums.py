"""
Chunking domain enumerations.

These enums define the supported chunking strategies and chunk content
types used throughout the Knowledge Platform.

The Chunking Platform transforms processed documents into retrieval-ready
knowledge units while remaining independent from downstream AI frameworks.
"""

from __future__ import annotations

from enum import StrEnum


class ChunkingStrategy(StrEnum):
    """
    Supported chunking strategies.

    The strategy identifies the provider implementation registered in the
    ChunkingRegistry.
    """

    FIXED = "fixed"

    RECURSIVE = "recursive"

    MARKDOWN = "markdown"

    HIERARCHICAL = "hierarchical"

    SEMANTIC = "semantic"

    LLM = "llm"

    ADAPTIVE = "adaptive"


class ChunkContentType(StrEnum):
    """
    Logical content represented by a chunk.

    These values originate from the processed document structure and may
    be used by future adaptive chunking strategies.
    """

    TEXT = "text"

    MARKDOWN = "markdown"

    HEADING = "heading"

    PARAGRAPH = "paragraph"

    TABLE = "table"

    LIST = "list"

    CODE = "code"

    REFERENCE = "reference"

    FIGURE = "figure"

    IMAGE_CAPTION = "image_caption"
