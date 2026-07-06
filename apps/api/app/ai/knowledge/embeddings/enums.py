"""
Embedding domain enumerations.

These enums define the supported embedding providers used throughout
the Knowledge Platform.

The Embedding Platform transforms canonical Chunks into canonical
Embeddings while remaining independent from downstream AI frameworks
and vendor SDKs.
"""

from __future__ import annotations

from enum import StrEnum


class EmbeddingProvider(StrEnum):
    """
    Supported embedding providers.

    The provider identifies the implementation registered in the
    EmbeddingRegistry.
    """

    SENTENCE_TRANSFORMERS = "sentence_transformers"

    VOYAGE_AI = "voyage_ai"

    OPENAI = "openai"

    BGE = "bge"

    INSTRUCTOR = "instructor"

    NOMIC = "nomic"
