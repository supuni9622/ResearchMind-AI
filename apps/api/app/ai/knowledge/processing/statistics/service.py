"""
Statistics enrichment service.

Coordinates statistics providers and enriches the canonical
DocumentStatistics.

Each provider contributes additional statistics without modifying
statistics owned by another provider.
"""

from __future__ import annotations

from pathlib import Path

import structlog

from app.ai.knowledge.processing.models import (
    ProcessedDocument,
)
from app.ai.knowledge.processing.statistics.models import (
    StatisticsUpdate,
)
from app.ai.knowledge.processing.statistics.registry import (
    StatisticsRegistry,
)

logger = structlog.get_logger()


class StatisticsEnrichmentService:
    """
    Coordinates statistics providers.

    Providers execute sequentially and contribute statistics to the
    canonical ProcessedDocument.
    """

    def __init__(
        self,
        registry: StatisticsRegistry,
    ) -> None:
        self._registry = registry

    async def enrich(
        self,
        *,
        document: ProcessedDocument,
        file_path: Path,
    ) -> ProcessedDocument:
        """
        Enrich a processed document using all registered statistics
        providers.
        """

        enriched_document = document.model_copy(deep=True)

        for provider in self._registry:
            logger.debug(
                "statistics.provider_started",
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
                "statistics.provider_completed",
                provider=provider.provider_name,
            )

        return enriched_document

    def _apply_update(
        self,
        *,
        document: ProcessedDocument,
        update: StatisticsUpdate,
    ) -> None:
        """
        Merge statistics extracted by a provider into the canonical
        DocumentStatistics.
        """

        statistics = document.statistics

        if update.page_count is not None:
            statistics.page_count = update.page_count

        if update.heading_count is not None:
            statistics.heading_count = update.heading_count

        if update.paragraph_count is not None:
            statistics.paragraph_count = update.paragraph_count

        if update.table_count is not None:
            statistics.table_count = update.table_count

        if update.figure_count is not None:
            statistics.figure_count = update.figure_count

        if update.code_block_count is not None:
            statistics.code_block_count = update.code_block_count

        if update.list_count is not None:
            statistics.list_count = update.list_count

        if update.reference_count is not None:
            statistics.reference_count = update.reference_count
