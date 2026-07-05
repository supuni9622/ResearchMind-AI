"""
Base chunking provider.

Provides common functionality shared by all chunking implementations.
"""

from __future__ import annotations

import hashlib
from abc import ABC
from typing import Generic, TypeVar
from uuid import UUID, uuid4

from pydantic import BaseModel

from app.ai.knowledge.chunking.interfaces import ChunkingProvider
from app.ai.knowledge.chunking.models import (
    Chunk,
    ChunkContent,
    ChunkExperiment,
    ChunkProvenance,
    ChunkStructure,
)
from app.ai.knowledge.chunking.statistics.service import ChunkStatisticsService
from app.ai.knowledge.processing.models import ProcessedDocument

ConfigT = TypeVar("ConfigT", bound=BaseModel)


class BaseChunkingProvider(
    ChunkingProvider,
    Generic[ConfigT],
    ABC,
):
    """
    Base class for all chunking providers.

    Concrete providers are responsible only for determining chunk
    boundaries. The base class centralizes construction of the canonical
    Chunk model and shared metadata generation.
    """

    def __init__(
        self,
        config: ConfigT,
    ) -> None:
        self._config = config

        self._configuration_fingerprint = hashlib.sha256(
            self._config.model_dump_json().encode("utf-8")
        ).hexdigest()

    @property
    def version(self) -> str:
        """
        Provider implementation version.
        """

        return "1.0"

    @property
    def config(self) -> ConfigT:
        """
        Provider configuration.
        """

        return self._config

    @property
    def configuration_fingerprint(self) -> str:
        """
        Stable fingerprint representing the provider configuration.
        """

        return self._configuration_fingerprint

    def _build_chunk(
        self,
        *,
        document: ProcessedDocument,
        text: str,
        index: int,
        total_chunks: int,
        markdown: str | None = None,
        page_numbers: list[int] | None = None,
        heading: str | None = None,
        heading_path: list[str] | None = None,
        hierarchy_level: int | None = None,
        parent_chunk_id: UUID | None = None,
    ) -> Chunk:
        """
        Build the canonical Chunk object.
        """

        return Chunk(
            id=uuid4(),
            index=index,
            total_chunks=total_chunks,
            content=ChunkContent(
                text=text,
                markdown=markdown,
                content_type=self._resolve_content_type(markdown),
            ),
            structure=ChunkStructure(
                heading=heading,
                heading_path=heading_path or [],
                page_numbers=page_numbers or [],
                hierarchy_level=hierarchy_level,
                parent_chunk_id=parent_chunk_id,
            ),
            statistics=ChunkStatisticsService.build(text),
            provenance=self._build_provenance(document),
            experiment=self._build_experiment(),
        )

    @staticmethod
    def _build_provenance(
        document: ProcessedDocument,
    ) -> ChunkProvenance:
        """
        Build chunk provenance.
        """

        return ChunkProvenance(
            document_id=document.document_id,
            filename=document.filename,
            parser=document.parser.value,
            parser_version=None,
        )

    def _build_experiment(
        self,
    ) -> ChunkExperiment:
        """
        Build experiment metadata.
        """

        return ChunkExperiment(
            strategy=self.strategy,
            strategy_version=self.version,
            configuration_fingerprint=self.configuration_fingerprint,
        )

    @staticmethod
    def _resolve_content_type(
        markdown: str | None,
    ):
        """
        Resolve the logical content type.
        """

        from app.ai.knowledge.chunking.enums import ChunkContentType

        if markdown:
            return ChunkContentType.MARKDOWN

        return ChunkContentType.TEXT
