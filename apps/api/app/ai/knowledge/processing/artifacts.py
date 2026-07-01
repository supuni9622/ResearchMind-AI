"""
Processing artifacts produced by the document processing pipeline.

These artifacts are generated from a ProcessedDocument and are
persisted for downstream AI workflows.

Artifacts are consumed by:

- Chunking Platform
- Embedding Platform
- Retrieval Platform
- Evaluation
- Debugging
- Reprocessing

This module contains only artifact models.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class ProcessingArtifact(BaseModel):
    """
    Represents a single processing artifact.
    """

    model_config = ConfigDict(extra="forbid")

    filename: str

    content_type: str

    content: str


class ProcessingArtifacts(BaseModel):
    """
    Collection of artifacts produced during document processing.

    Each artifact is persisted independently.
    """

    model_config = ConfigDict(extra="forbid")

    markdown: ProcessingArtifact

    text: ProcessingArtifact

    json_blocks: ProcessingArtifact | None = None
