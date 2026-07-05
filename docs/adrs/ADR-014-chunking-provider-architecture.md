# ADR-00X: Chunking Provider Architecture

**Status:** Accepted

**Date:** 2026-07-05

---

# Context

ResearchMind is designed to experiment with multiple chunking strategies.

Current roadmap includes:

- Fixed Chunking
- Recursive Chunking
- Markdown Chunking
- Hierarchical Chunking
- Semantic Chunking
- LLM Chunking
- Adaptive Hybrid Chunking

The architecture must allow new providers to be introduced without
modifying application logic.

---

# Decision

ResearchMind adopts the Strategy Pattern.

Every chunking implementation must implement the ChunkingProvider
interface.

```
ChunkingService

↓

ChunkingRegistry

↓

ChunkingProvider

↓

Concrete Provider
```

Shared functionality is centralized within BaseChunkingProvider.

---

# Responsibilities

## ChunkingService

Responsible for:

- orchestration
- provider selection

It does not implement chunking algorithms.

---

## ChunkingRegistry

Responsible for:

- provider registration
- provider lookup

The registry knows which provider implements each strategy.

---

## BaseChunkingProvider

Provides reusable functionality.

Examples:

- chunk construction
- provenance generation
- experiment metadata
- configuration fingerprint
- statistics integration

Concrete providers focus only on determining chunk boundaries.

---

## ChunkStatisticsService

Responsible for reusable chunk statistics.

Providers reuse this service rather than implementing their own
statistics logic.

---

# Rationale

This architecture separates algorithm-specific logic from shared
platform behaviour.

Each provider implements only its unique chunking strategy while the
platform handles common concerns consistently.

This minimizes duplication and keeps providers small.

---

# Provider Lifecycle

```
ProcessedDocument

↓

ChunkingService

↓

ChunkingRegistry

↓

Concrete Provider

↓

BaseChunkingProvider

↓

Chunk
```

---

# Why Strategy Pattern?

The Strategy Pattern enables:

- interchangeable providers
- experimentation
- benchmarking
- independent evolution
- easy testing

Adding a new provider requires only:

1. Implement the provider.
2. Register the provider.

No other application code changes.

---

# Alternatives Considered

## Large switch statement

Example

```
if strategy == FIXED:
    ...

elif strategy == RECURSIVE:
    ...

elif strategy == SEMANTIC:
    ...
```

Rejected.

This approach violates the Open/Closed Principle and requires modifying
existing code whenever a new strategy is introduced.

---

## Separate services for every provider

Rejected.

Would duplicate shared logic such as:

- chunk construction
- provenance
- statistics
- experiment metadata

---

## Dynamic plugin discovery

Rejected.

ResearchMind has a small, known set of providers.

Explicit registration is simpler, easier to debug, and more predictable.

---

# Consequences

Positive

- extensible
- maintainable
- reusable
- easy to benchmark
- consistent provider behaviour

Negative

- introduces one additional abstraction layer

This trade-off is considered worthwhile because the number of providers
will continue to grow.

---

# Decision Summary

ResearchMind adopts a provider-based chunking architecture using the
Strategy Pattern.

Common behaviour is centralized within BaseChunkingProvider.

Concrete providers are responsible only for determining chunk
boundaries.
