# ADR-018: Knowledge Indexing and Retrieval Architecture

**Status:** Accepted

**Date:** 2026-07-08

**Decision Makers:** ResearchMind Engineering

---

# Context

ResearchMind aims to become a production-grade AI Research Platform rather than a simple Retrieval-Augmented Generation (RAG) application.

As the Knowledge Platform evolved, it became clear that document indexing and document retrieval are two distinct responsibilities with different lifecycles, different concerns, and different opportunities for future extension.

Initially, the roadmap assumed a Vector Store Platform followed directly by a Retrieval Platform.

During implementation, we evaluated the architecture against real production search systems and identified several improvements that would produce a cleaner, more scalable, and more maintainable design.

This ADR documents those decisions.

---

# Decision

ResearchMind will separate **Indexing** from **Retrieval** as two independent platforms within the Knowledge Platform.

The Knowledge Platform architecture becomes:

```text
Upload
    │
    ▼
Processing
    │
    ▼
Chunking
    │
    ▼
Embedding
    │
    ▼
Indexing Platform
    │
    ▼
Retrieval Platform
    │
    ▼
Reranking Platform
```

Each platform owns a single business capability.

---

# Decision 1 — Indexing is a Separate Platform

## Decision

Indexing will become its own platform.

Its responsibility is to transform processed knowledge into searchable indexes.

It is **not** responsible for searching those indexes.

---

## Responsibilities

The Indexing Platform owns:

- Index orchestration
- Vector indexing
- BM25 indexing
- Index statistics
- Index artifacts
- Index lifecycle

Future responsibilities include:

- Knowledge Graph indexing

---

## Initial Architecture

```text
Embedding Artifact
        │
        ▼
Indexing Platform
        │
        ├── Vector Index
        ├── BM25 Index
        └── (Future) Knowledge Graph Index
```

---

## Rationale

Different index types have different storage models and indexing strategies.

A dedicated platform allows ResearchMind to support multiple index types without coupling them together.

---

# Decision 2 — Retrieval is a Separate Platform

## Decision

Retrieval will become its own platform.

Its responsibility is to retrieve the best knowledge from available indexes.

Retrieval never creates indexes.

---

## Responsibilities

The Retrieval Platform owns:

- Query processing
- Search execution
- Retrieval strategies
- Result fusion
- Metadata filtering
- Retrieval evaluation
- Retrieval caching

It does **not** own indexing.

---

## Architecture

```text
User Query
      │
      ▼
Query Processing
      │
      ▼
Retrieval Strategy
      │
      ▼
Search Engines
      │
      ▼
Result Processing
      │
      ▼
Retrieved Context
```

---

# Decision 3 — Hybrid Retrieval is MVP

## Decision

Hybrid Retrieval is part of the initial MVP.

It is **not** considered a future enhancement.

---

## Architecture

```text
Query
      │
      ▼
Semantic Search

+

Keyword Search

      │
      ▼
Result Fusion
      │
      ▼
Metadata Filtering
      │
      ▼
Reranking
```

---

## Rationale

ResearchMind is a research platform.

Research workloads frequently require exact keyword matching in addition to semantic similarity.

Examples include:

- RFC numbers
- Error messages
- API names
- Function names
- Version numbers
- Paper identifiers

Hybrid Retrieval provides better recall and better practical usability than semantic search alone.

---

# Decision 4 — Retrieval Strategies are MVP

ResearchMind will support multiple retrieval strategies in the MVP.

These strategies are considered first-class capabilities of the Retrieval Platform.

---

## Strategy 1

Standard Semantic Retrieval

Purpose

Baseline semantic retrieval.

---

## Strategy 2

Hybrid Retrieval

Purpose

Combine semantic similarity with keyword search.

---

## Strategy 3

Parent / Child Retrieval

Purpose

Retrieve using fine-grained chunks while returning larger parent context to the LLM.

This improves answer quality without sacrificing retrieval precision.

---

## Strategy 4

Query Decomposition

Purpose

Break complex research questions into multiple smaller queries.

Retrieve evidence for each sub-question before synthesizing the final answer.

This strategy is especially valuable for research-oriented workflows.

---

# Decision 5 — Knowledge Graph is Deferred

Knowledge Graph indexing will **not** be included in the MVP.

---

## Reason

Knowledge Graphs introduce significant additional complexity including:

- Entity extraction
- Relationship extraction
- Graph storage
- Graph traversal
- Graph retrieval

Although valuable for research systems, they are intentionally deferred until the core retrieval system reaches production quality.

---

# Decision 6 — Reranking is Part of MVP

Reranking is considered a core component of the retrieval pipeline.

ResearchMind will use Voyage AI Reranking as the primary reranking provider.

Reranking occurs after retrieval and before context construction.

---

# Decision 7 — Metadata Filtering is Part of MVP

Retrieval must support metadata filtering.

Examples include:

- owner_id
- workspace_id
- project_id
- document_id
- filename
- language
- tags

Metadata filtering is considered a production requirement rather than an optional feature.

---

# Decision 8 — Retrieval Caching is Part of MVP

ResearchMind will implement retrieval caching.

The primary objectives are:

- Reduce retrieval latency
- Reduce repeated computation
- Improve user experience

Caching strategies remain implementation details and may evolve over time.

---

# Decision 9 — Evaluation is Built Into Retrieval

Every retrieval strategy must be measurable.

ResearchMind will evaluate retrieval using metrics such as:

- Recall@K
- Precision@K
- MRR
- NDCG
- Latency
- Cost

Evaluation is considered a core capability rather than a separate optional process.

---

# Knowledge Platform Architecture

```text
                    Upload
                       │
                       ▼
                 Document Processing
                       │
                       ▼
                    Chunking
                       │
                       ▼
                   Embeddings
                       │
                       ▼
                Indexing Platform
         ┌─────────────┴─────────────┐
         ▼                           ▼
   Vector Index                BM25 Index
         └─────────────┬─────────────┘
                       ▼
               Retrieval Platform
                       │
              Query Processing
                       │
              Retrieval Strategy
                       │
         ┌─────────────┼─────────────┐
         ▼             ▼             ▼
    Semantic      Hybrid        Parent/Child
    Retrieval     Retrieval     Retrieval
                       │
                       ▼
              Query Decomposition
                       │
                       ▼
                 Result Processing
                       │
             ├── Result Fusion
             ├── Metadata Filtering
             ├── Reranking
             └── Top-K Selection
                       │
                       ▼
                 Context Builder
                       │
                       ▼
                      LLM
```

---

# Consequences

## Benefits

- Clear separation of responsibilities.
- Cleaner platform boundaries.
- Easier future extension.
- Better alignment with production search architectures.
- Supports experimentation with multiple retrieval strategies.
- Enables continuous evaluation of retrieval quality.

---

## Trade-offs

- Additional implementation effort compared to a vector-only system.
- Hybrid Retrieval requires maintaining multiple indexes.
- Retrieval orchestration becomes more sophisticated.

These trade-offs are considered acceptable because ResearchMind is intended to become a production-grade AI Research Platform.

---

# Alternatives Considered

## Vector Search Only

Rejected.

Reason:

Insufficient for research workloads requiring exact keyword matching.

---

## Hybrid Retrieval as a Future Enhancement

Rejected.

Reason:

Hybrid Retrieval significantly improves retrieval quality for technical and research documents and is considered fundamental rather than optional.

---

## Knowledge Graph in MVP

Rejected.

Reason:

Introduces substantial complexity without providing proportional value for the initial release.

---

## Combined Indexing and Retrieval Platform

Rejected.

Reason:

Indexing and Retrieval represent different business responsibilities and evolve independently.

Separating them produces a cleaner architecture.

---

# Implementation Roadmap

The implementation order becomes:

1. Complete Vector Indexing
2. Implement BM25 Indexing
3. Build Indexing Platform
4. Build Retrieval Platform
5. Implement Hybrid Retrieval
6. Add Metadata Filtering
7. Implement Result Fusion
8. Implement Voyage Reranking
9. Add Retrieval Cache
10. Build Retrieval Evaluation
11. Compare Retrieval Strategies
12. Integrate with AI Runtime

Knowledge Graph support will be introduced in a future milestone after the MVP is complete.

---

# Status

Accepted.

This ADR supersedes previous assumptions that:

- Vector Store directly owns indexing orchestration.
- Semantic Retrieval alone is sufficient for the MVP.

ResearchMind will adopt the architecture described in this document moving forward.
