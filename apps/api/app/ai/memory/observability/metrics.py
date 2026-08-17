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
MEMORY_SUPERSEDED = "memory.superseded"
MEMORY_MUTATION_ACCEPTED = "memory.mutation_accepted"
MEMORY_MUTATION_REJECTED = "memory.mutation_rejected"
MEMORY_MUTATION_FAILED = "memory.mutation_failed"
EXTRACTION_RATE_LIMITED = "memory.extraction_rate_limited"
LIFECYCLE_EXAMINED = "memory.lifecycle_examined"
LIFECYCLE_DELETED = "memory.lifecycle_deleted"
LIFECYCLE_FAILED = "memory.lifecycle_failed"
LIFECYCLE_DURATION = "memory.lifecycle_duration"
LIFECYCLE_LAST_SUCCESS = "memory.lifecycle_last_success_timestamp"
LIFECYCLE_OLDEST_CANDIDATE_AGE = "memory.lifecycle_oldest_candidate_age_seconds"
CONSOLIDATION_EXAMINED = "memory.consolidation_examined"
CONSOLIDATION_CANDIDATES = "memory.consolidation_candidates"
CONSOLIDATION_OUTCOMES = "memory.consolidation_outcomes"
CONSOLIDATION_DURATION = "memory.consolidation_duration"
CONTEXT_TOKENS_SELECTED = "memory.context_tokens_selected"
CONTEXT_TOKENS_DROPPED = "memory.context_tokens_dropped"
CONTEXT_ITEMS_OMITTED = "memory.context_items_omitted"
CONTEXT_TOKEN_SHARE = "memory.context_token_share"
STORAGE_ROWS = "memory.storage_rows"
STORAGE_BYTES = "memory.storage_bytes"
STORAGE_OLDEST_AGE = "memory.storage_oldest_age_seconds"
STORAGE_DISTRIBUTION = "memory.storage_distribution"
VECTOR_POINTS = "memory.vector_points"
VECTOR_DRIFT = "memory.vector_drift"
INVENTORY_LAST_SUCCESS = "memory.inventory_last_success_timestamp"
