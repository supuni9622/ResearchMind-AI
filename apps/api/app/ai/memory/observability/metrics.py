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

CONTEXT_REQUESTS = "memory.context_requests"
CONTEXT_DURABLE_AVAILABLE = "memory.context_durable_available"
CONTEXT_DURABLE_EMPTY = "memory.context_durable_empty"
CONTEXT_RETRIEVAL_SKIPPED = "memory.context_retrieval_skipped"
CONTEXT_LATENCY = "memory.context_latency"
DURABLE_SEARCH_LATENCY = "memory.durable_search_latency"
SEMANTIC_SEARCH = "memory.semantic_search"
RESEARCH_SEARCH = "memory.research_search"
PARALLEL_SEARCH = "memory.parallel_search"
SESSION_ITEMS_LOADED = "memory.session_items_loaded"
SESSION_DUPLICATES_REMOVED = "memory.session_duplicates_removed"

EXTRACTION_EVALUATED = "memory.extraction_evaluated"
EXTRACTION_SKIPPED = "memory.extraction_skipped"
EXTRACTION_REQUESTED = "memory.extraction_requested"
EXTRACTION_SUCCEEDED = "memory.extraction_succeeded"
EXTRACTION_FAILED = "memory.extraction_failed"
EXTRACTION_EMPTY = "memory.extraction_empty"
EXTRACTION_LATENCY = "memory.extraction_latency"
MEMORY_CREATED = "memory.created"
MEMORY_UPDATED = "memory.updated"
MEMORY_DUPLICATE = "memory.duplicate"
