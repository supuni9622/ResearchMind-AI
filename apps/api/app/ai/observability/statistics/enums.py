from __future__ import annotations

from enum import StrEnum


class TimeWindow(StrEnum):
    """
    Aggregation window a `StatisticsSnapshot` was computed over (PRD §6
    "Time Windows"). Purely descriptive -- bucketing snapshots into a
    window is the caller's responsibility (there is no persistent metrics
    store to query in this phase, see the Statistics Platform module
    docstring), this just labels the result.
    """

    HOURLY = "hourly"

    DAILY = "daily"

    WEEKLY = "weekly"

    MONTHLY = "monthly"
