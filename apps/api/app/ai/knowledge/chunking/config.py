"""
Chunking configuration models.

These configuration models define the behavior of chunking providers.

The Chunking Platform intentionally separates provider configuration
from provider implementation to support experimentation, reproducibility,
and future provider versioning.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field, model_validator


class FixedChunkingConfig(BaseModel):
    """
    Configuration for the Fixed Chunking provider.
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
    def validate_overlap(self) -> FixedChunkingConfig:
        """
        Ensure overlap is smaller than the chunk size.
        """

        if self.chunk_overlap >= self.chunk_size:
            raise ValueError(
                "chunk_overlap must be smaller than chunk_size.",
            )

        return self
