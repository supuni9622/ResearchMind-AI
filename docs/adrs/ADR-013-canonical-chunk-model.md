# ADR-00X: Canonical Chunk Model

**Status:** Accepted

**Date:** 2026-07-05

---

# Context

The Chunking Platform transforms processed documents into knowledge units
that are consumed by every downstream AI platform.

These downstream platforms include:

- Embedding Platform
- Vector Store
- Retrieval
- Reranking
- Context Builder
- Citation Engine
- Evaluation
- Future Agentic AI workflows

Several implementation approaches were considered.

Option 1

Each chunking provider returns its own model.

Example:

- FixedChunk
- RecursiveChunk
- SemanticChunk

Option 2

Return framework-specific models.

Examples:

- LangChain Document
- LlamaIndex Node
- Haystack Document

Option 3

Define a single canonical Chunk model owned by ResearchMind.

---

# Decision

ResearchMind adopts a single canonical Chunk model.

Every chunking provider must produce exactly the same Chunk model.

```
ProcessedDocument

↓

Chunk

↓

Embedding

↓

Vector Store

↓

Retrieval

↓

Evaluation
```

Framework-specific objects are created only at integration boundaries.

The Chunk model remains framework independent.

---

# Rationale

A canonical Chunk model provides several advantages.

## Loose Coupling

The AI pipeline is independent of external frameworks.

Changing LangChain or introducing another framework does not affect the
core domain model.

---

## Consistency

Every downstream platform consumes the same object.

No conversion between provider-specific models is required.

---

## Extensibility

Future platforms progressively enrich the Chunk rather than replacing it.

Examples include:

- embeddings
- retrieval scores
- reranking scores
- citations
- evaluation metadata

---

## Experimentation

Chunking strategies can be compared fairly because they all produce the
same output model.

Only the chunk boundaries differ.

---

## Maintainability

The Chunk model becomes the single source of truth for downstream AI
processing.

---

# Consequences

Positive

- framework independence
- cleaner architecture
- easier testing
- reusable across AI platforms
- supports experimentation

Negative

- adapters are required when integrating with external frameworks

This trade-off is considered acceptable because adapters are isolated to
integration boundaries.

---

# Alternatives Considered

## Provider-specific models

Rejected.

Would tightly couple downstream platforms to individual providers.

---

## Framework-specific models

Rejected.

Would tightly couple the platform to LangChain or another framework.

Frameworks may change while the domain model should remain stable.

---

# Decision Summary

ResearchMind owns its canonical AI domain model.

Every chunking provider produces exactly one Chunk model.

All downstream AI platforms consume this canonical representation.
