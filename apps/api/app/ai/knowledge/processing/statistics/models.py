"""
Statistics models for the document processing platform.

Statistics providers enrich the canonical DocumentStatistics with
additional measurements extracted from the document.
"""

from __future__ import annotations

from pydantic import BaseModel


class StatisticsUpdate(BaseModel):
    """
    Statistics extracted by one or more statistics providers.

    Providers populate only the fields they are responsible for.
    """

    page_count: int | None = None

    heading_count: int | None = None

    paragraph_count: int | None = None

    table_count: int | None = None

    figure_count: int | None = None

    code_block_count: int | None = None

    list_count: int | None = None

    reference_count: int | None = None
