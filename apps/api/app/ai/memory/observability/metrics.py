"""
Memory Platform metric names (PRD §22).

`*_LATENCY` values are `MetricsRecorder.record_duration()` operation
labels; the rest are `MetricsRecorder.increment()` metric names.
"""

from __future__ import annotations

REMEMBER_LATENCY = "memory.remember_latency"

SEARCH_LATENCY = "memory.search_latency"

EMBEDDING_LATENCY = "memory.embedding_latency"

MEMORY_HITS = "memory_hits"

MEMORY_MISSES = "memory_misses"

MEMORY_COUNT = "memory_count"
