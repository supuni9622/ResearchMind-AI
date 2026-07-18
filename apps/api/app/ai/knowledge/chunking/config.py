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


class MarkdownChunkingConfig(BaseModel):
    """
    Configuration for the Markdown Chunking provider.
    """

    model_config = ConfigDict(
        extra="forbid",
        frozen=True,
    )

    headers_to_split_on: tuple[tuple[str, str], ...] = (
        ("#", "h1"),
        ("##", "h2"),
        ("###", "h3"),
        ("####", "h4"),
        ("#####", "h5"),
        ("######", "h6"),
    )

    strip_headers: bool = Field(
        default=False,
        description="Whether Markdown headers should be removed from chunks.",
    )

    return_each_line: bool = Field(
        default=False,
        description="Whether every line should become an individual document.",
    )

    chunk_size: int = Field(
        default=500,
        ge=1,
        description="Maximum recursive chunk size.",
    )

    chunk_overlap: int = Field(
        default=100,
        ge=0,
        description="Chunk overlap after Markdown section splitting.",
    )

    @model_validator(mode="after")
    def validate_overlap(self) -> MarkdownChunkingConfig:
        if self.chunk_overlap >= self.chunk_size:
            raise ValueError(
                "chunk_overlap must be smaller than chunk_size.",
            )

        return self


class HierarchicalChunkingConfig(BaseModel):
    """
    Configuration for the Hierarchical (Parent/Child) Chunking provider.

    Documents are first split into large "parent" sections and each
    parent is then split into small "child" chunks. Children are what
    gets embedded and retrieved; parents are persisted so a retrieved
    child can be expanded back into its full parent section.
    """

    model_config = ConfigDict(
        extra="forbid",
        frozen=True,
    )

    parent_chunk_size: int = Field(
        default=2000,
        ge=1,
        description="Maximum number of characters per parent chunk.",
    )

    parent_chunk_overlap: int = Field(
        default=200,
        ge=0,
        description="Number of overlapping characters between adjacent parent chunks.",
    )

    child_chunk_size: int = Field(
        default=400,
        ge=1,
        description="Maximum number of characters per child chunk.",
    )

    child_chunk_overlap: int = Field(
        default=50,
        ge=0,
        description="Number of overlapping characters between adjacent child chunks.",
    )

    @model_validator(mode="after")
    def validate_sizes(self) -> HierarchicalChunkingConfig:
        if self.parent_chunk_overlap >= self.parent_chunk_size:
            raise ValueError(
                "parent_chunk_overlap must be smaller than parent_chunk_size.",
            )

        if self.child_chunk_overlap >= self.child_chunk_size:
            raise ValueError(
                "child_chunk_overlap must be smaller than child_chunk_size.",
            )

        if self.child_chunk_size >= self.parent_chunk_size:
            raise ValueError(
                "child_chunk_size must be smaller than parent_chunk_size.",
            )

        return self
