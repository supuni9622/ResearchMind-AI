# ADR-015 — Canonical AI Platform Pipeline

**Status:** Accepted

**Date:** 2026-07-06

**Decision Makers:**
- ResearchMind AI Engineering

---

# Context

ResearchMind is designed as a long-term AI Engineering Platform rather than a traditional Retrieval-Augmented Generation (RAG) application.

The Knowledge Platform consists of multiple independent AI platforms:

- Processing
- Chunking
- Embedding
- Vector Store
- Retrieval
- Reranking
- Evaluation
- Experimentation

Each platform performs a distinct responsibility within the AI pipeline.

During implementation of the Chunking and Embedding platforms, an important architectural decision emerged.

Initially, downstream platforms consumed internal models from the previous platform.

For example:

```text
EmbeddingService

↓

list[Chunk]
```

While this worked functionally, it introduced several architectural problems.

- Downstream platforms received only part of the upstream execution context.
- Metadata needed to be reconstructed.
- Platform boundaries became less explicit.
- Future experimentation would require additional parameters.
- Artifact lineage became more difficult to preserve.

As additional AI platforms were planned, this approach became increasingly difficult to scale.

---

# Decision

Every AI platform shall consume the **canonical artifact** produced by the previous platform.

Platforms should no longer consume internal domain models directly when a canonical artifact already exists.

The canonical artifact becomes the public contract between adjacent AI platforms.

The resulting execution pipeline is:

```text
Upload

↓

Processing

↓

ProcessedDocument

↓

Chunking Platform

↓

ChunkArtifact

↓

Embedding Platform

↓

EmbeddingArtifact

↓

Vector Store Platform

↓

VectorStoreArtifact

↓

Retrieval Platform

↓

RetrievalArtifact

↓

Reranking Platform

↓

RerankingArtifact
```

Each platform owns exactly one canonical persistence artifact.

That artifact becomes the input for the next platform.

---

# Rationale

## Stable Platform Boundaries

A platform should expose only one public output.

Instead of exposing internal implementation models, it exposes its canonical artifact.

For example:

```text
Chunking Platform

Output

↓

ChunkArtifact
```

rather than

```text
list[Chunk]
```

This creates a much stronger boundary between platforms.

---

## Complete Execution Context

Artifacts contain significantly more information than internal models.

For example, a ChunkArtifact includes:

- document information
- parser metadata
- chunking strategy
- configuration fingerprint
- chunk statistics
- evaluation metadata
- execution metadata

An Embedding Platform should receive this complete context rather than reconstructing it.

---

## Traceability

Every artifact captures how it was produced.

For example:

```text
EmbeddingArtifact

↓

Chunking Strategy

↓

Parser

↓

Configuration Fingerprints

↓

Provider Metadata
```

This creates an auditable chain across the pipeline.

Future debugging and experimentation become substantially easier.

---

## Reproducibility

Artifacts preserve the complete execution context required to reproduce a platform's output.

This includes information such as:

- provider versions
- model versions
- parser versions
- configuration fingerprints
- execution metadata

Future experimentation can recreate historical outputs without relying on external state.

---

## Reduced Coupling

Downstream platforms no longer depend on internal implementation models.

For example:

Current dependency:

```text
Embedding Platform

↓

Chunk
```

New dependency:

```text
Embedding Platform

↓

ChunkArtifact
```

If Chunk internally evolves, the Embedding Platform remains unaffected provided the artifact contract remains stable.

---

## Platform Independence

Each platform becomes independently evolvable.

A platform can completely change its internal implementation without affecting downstream consumers.

Only the artifact contract must remain stable.

This is consistent with Clean Architecture and bounded context principles.

---

# Consequences

## Positive

### Explicit Contracts

Each platform exposes a single well-defined artifact.

Platform boundaries become clear.

---

### Better Maintainability

Internal implementation details remain private.

Only canonical artifacts are shared.

---

### Improved Extensibility

Adding new platforms becomes straightforward.

Each platform simply consumes the previous artifact and produces a new artifact.

---

### Simplified Experimentation

Alternative implementations can be compared using canonical artifacts.

The experimentation platform can operate independently of production implementations.

---

### Improved Observability

Future runtime evaluation can inspect artifacts at every stage.

Performance metrics and quality metrics naturally align with platform boundaries.

---

### Better Versioning

Each artifact maintains its own schema version.

Platform evolution becomes independent.

---

# Negative Consequences

Artifacts contain more information than a minimal API.

This increases artifact size slightly.

However, the additional metadata is valuable for:

- debugging
- reproducibility
- experimentation
- observability

The trade-off is considered worthwhile.

---

# Alternatives Considered

## Alternative 1

Consume internal domain models.

Example:

```text
Embedding Platform

↓

list[Chunk]
```

### Rejected

Reason:

Internal models do not capture sufficient execution context.

---

## Alternative 2

Pass multiple parameters.

Example:

```python
embed(
    chunks,
    parser,
    strategy,
    statistics,
    metadata,
    ...
)
```

### Rejected

Reason:

Method signatures grow over time.

Context becomes fragmented.

Responsibilities become unclear.

---

## Alternative 3

Create a generic pipeline context object.

Example:

```text
PipelineContext
```

### Rejected (for now)

A generic pipeline context was discussed during the Embedding Platform implementation.

At the current stage there is only one production pipeline.

Introducing another orchestration abstraction was considered premature.

ProcessingService continues to orchestrate execution through private platform stages.

The decision may be revisited if multiple pipeline variants emerge in the future.

---

# Relationship to Existing Architecture

This decision complements several existing architectural principles adopted by ResearchMind.

## Canonical Models

Platforms expose canonical models rather than provider SDK objects.

---

## Provider Pattern

Providers remain internal implementation details.

Artifacts remain provider independent.

---

## Factory Pattern

Factories construct canonical models.

Artifacts consume those canonical models.

---

## Builder Pattern

Builders transform canonical models into canonical persistence artifacts.

---

## Clean Architecture

Dependencies flow inward.

Platform boundaries remain explicit.

---

# Future Platforms

This ADR applies to every future AI platform.

Examples include:

```text
Processing

↓

ProcessedDocument

↓

Chunking

↓

ChunkArtifact

↓

Embedding

↓

EmbeddingArtifact

↓

Vector Store

↓

VectorStoreArtifact

↓

Retrieval

↓

RetrievalArtifact

↓

Reranking

↓

RerankingArtifact

↓

Evaluation

↓

PipelineEvaluationArtifact
```

Future platforms should continue following the same principle.

---

# Implementation Status

| Platform | Artifact | Status |
|----------|----------|--------|
| Processing | ProcessedDocument | ✅ Implemented |
| Chunking | ChunkArtifact | ✅ Implemented |
| Embedding | EmbeddingArtifact | ✅ Implemented |
| Vector Store | VectorStoreArtifact | ⏳ Planned |
| Retrieval | RetrievalArtifact | ⏳ Planned |
| Reranking | RerankingArtifact | ⏳ Planned |
| Pipeline Evaluation | PipelineEvaluationArtifact | ⏳ Planned |

---

# Compliance

Future AI platforms should satisfy the following rules.

1. Every platform consumes the canonical artifact produced by the previous platform.
2. Every platform produces exactly one canonical persistence artifact.
3. Internal implementation models must not be exposed outside the platform.
4. Provider SDK objects must never leave provider implementations.
5. Downstream platforms must depend only on canonical artifacts.
6. Artifact schemas should evolve independently through explicit versioning.

---

# Decision Summary

ResearchMind adopts an **artifact-driven AI pipeline**.

Rather than exchanging internal domain models between platforms, every AI platform consumes the canonical artifact produced by the previous platform and produces its own canonical artifact for the next platform.

This decision establishes stable platform boundaries, improves reproducibility and observability, reduces coupling, and provides a scalable foundation for future AI capabilities including Vector Stores, Retrieval, Reranking, Evaluation, and Experimentation.

This ADR is considered a foundational architectural decision for the long-term evolution of the ResearchMind AI platform.
