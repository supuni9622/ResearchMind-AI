"""
Processing artifact builder.

Transforms a ProcessedDocument into a collection of processing artifacts.

This class contains no infrastructure concerns and performs no I/O.
"""

from __future__ import annotations

from app.ai.knowledge.processing.artifacts import (
    ProcessingArtifact,
    ProcessingArtifacts,
)
from app.ai.knowledge.processing.models import ProcessedDocument


class ArtifactBuilder:
    """
    Builds processing artifacts from a processed document.
    """

    def build(
        self,
        document: ProcessedDocument,
    ) -> ProcessingArtifacts:
        """
        Build all processing artifacts.

        Args:
            document:
                Canonical processed document.

        Returns:
            ProcessingArtifacts
        """

        return ProcessingArtifacts(
            markdown=self._build_markdown(document),
            text=self._build_text(document),
            json_blocks=self._build_json(document),
        )

    def _build_markdown(
        self,
        document: ProcessedDocument,
    ) -> ProcessingArtifact:
        """
        Build the Markdown artifact.
        """

        return ProcessingArtifact(
            filename="parsed.md",
            content_type="text/markdown",
            content=document.markdown,
        )

    def _build_text(
        self,
        document: ProcessedDocument,
    ) -> ProcessingArtifact:
        """
        Build the plain text artifact.
        """

        return ProcessingArtifact(
            filename="parsed.txt",
            content_type="text/plain",
            content=document.raw_text,
        )

    def _build_json(
        self,
        document: ProcessedDocument,
    ) -> ProcessingArtifact:
        """
        Build the canonical JSON artifact.

        This artifact represents the parser-independent document model
        produced by the processing pipeline.
        """

        return ProcessingArtifact(
            filename="processed_document.json",
            content_type="application/json",
            content=document.model_dump_json(
                indent=2,
                exclude_none=True,
            ),
        )
