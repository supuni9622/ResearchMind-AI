"""
Chunking configuration models.

These configuration models define the behavior of chunking providers.

The Chunking Platform intentionally separates provider configuration
from provider implementation to support experimentation, reproducibility,
and future provider versioning.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field, model_validator


class BaseChunkingConfig(BaseModel):
    """
    Base configuration shared by all chunking providers.
    """

    model_config = ConfigDict(
        extra="forbid",
        frozen=True,
    )

    chunk_size: int = Field(
        default=500,
        ge=1,
        description="Maximum number of characters per chunk.",
    )

    chunk_overlap: int = Field(
        default=100,
        ge=0,
        description="Number of overlapping characters between adjacent chunks.",
    )

    @model_validator(mode="after")
    def validate_overlap(self) -> BaseChunkingConfig:
        """
        Ensure overlap is smaller than the chunk size.
        """

        if self.chunk_overlap >= self.chunk_size:
            raise ValueError(
                "chunk_overlap must be smaller than chunk_size.",
            )

        return self


class FixedChunkingConfig(BaseChunkingConfig):
    """
    Configuration for the Fixed Chunking provider.
    """

    pass


class RecursiveChunkingConfig(BaseChunkingConfig):
    """
    Configuration for the Recursive Chunking provider.

    The provider delegates chunk splitting to LangChain's
    RecursiveCharacterTextSplitter while keeping LangChain
    isolated behind the provider layer.
    """

    separators: list[str] = Field(
        default_factory=lambda: [
            "\n\n",
            "\n",
            ". ",
            " ",
            "",
        ],
        description=(
            "Ordered separators used by the recursive splitter. "
            "The splitter attempts each separator before falling "
            "back to the next."
        ),
    )

    keep_separator: bool = Field(
        default=True,
        description="Whether matched separators should remain in the resulting chunks.",
    )
