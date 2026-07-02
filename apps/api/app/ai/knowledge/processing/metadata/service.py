"""
Metadata enrichment service.

Coordinates metadata providers and enriches the canonical
ProcessedDocument.

Each provider contributes additional metadata without modifying
existing metadata owned by another provider.
"""

from __future__ import annotations

from pathlib import Path

import structlog

from app.ai.knowledge.processing.metadata.models import MetadataUpdate
from app.ai.knowledge.processing.metadata.registry import MetadataRegistry
from app.ai.knowledge.processing.models import ProcessedDocument

logger = structlog.get_logger()


class MetadataEnrichmentService:
    """
    Coordinates metadata providers.

    Providers execute sequentially and contribute metadata to the
    canonical ProcessedDocument.
    """

    def __init__(
        self,
        registry: MetadataRegistry,
    ) -> None:
        self._registry = registry

    async def enrich(
        self,
        *,
        document: ProcessedDocument,
        file_path: Path,
    ) -> ProcessedDocument:
        """
        Enrich a processed document using all registered metadata
        providers.
        """

        enriched_document = document.model_copy(deep=True)

        for provider in self._registry:
            logger.debug(
                "metadata.provider_started",
                provider=provider.provider_name,
            )

            update = await provider.enrich(
                document=enriched_document,
                file_path=file_path,
            )

            self._apply_update(
                document=enriched_document,
                update=update,
            )

            logger.debug(
                "metadata.provider_completed",
                provider=provider.provider_name,
            )

        return enriched_document

    def _apply_update(
        self,
        *,
        document: ProcessedDocument,
        update: MetadataUpdate,
    ) -> None:
        """
        Merge metadata extracted by a provider into the canonical
        document metadata.
        """

        metadata = document.metadata

        if update.pdf is not None:
            pdf = update.pdf

            if pdf.title:
                metadata.title = pdf.title

            metadata.additional_metadata.update(
                pdf.model_dump(
                    exclude_none=True,
                )
            )

        if update.language is not None:
            metadata.additional_metadata["language"] = update.language.model_dump(
                exclude_none=True,
            )

        metadata.additional_metadata.update(
            update.additional_metadata,
        )
