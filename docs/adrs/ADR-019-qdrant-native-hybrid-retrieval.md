# ADR-009: Adopt Qdrant Native Hybrid Retrieval Using Dense and Sparse Vectors

**Status:** Accepted

**Date:** 2026-07-08

**Decision Makers:** ResearchMind Architecture

---

# Context

ResearchMind is a production-oriented AI research platform focused on building a high-performance, scalable, cost-effective, and maintainable Retrieval-Augmented Generation (RAG) system.

The platform has completed the knowledge ingestion pipeline:

Document Upload

↓

Processing

↓

Chunking

↓

Dense Embeddings (Voyage AI)

↓

Indexing

↓

Knowledge Ready

The next architectural decision concerns supporting lexical retrieval and hybrid search.

Historically, this would involve introducing a dedicated BM25 search engine such as Whoosh, Tantivy, Elasticsearch, or OpenSearch alongside the vector database.

However, modern vector databases such as Qdrant now support native hybrid retrieval by storing both dense and sparse vectors within the same collection.

This removes the need to operate multiple indexing systems.

---

# Decision

ResearchMind will use **Qdrant as the single retrieval backend**.

ResearchMind will **not** implement or maintain a separate BM25 indexing platform.

Instead, the platform will generate:

- Dense embeddings using Voyage AI
- Sparse embeddings using FastEmbed SPLADE

Both representations will be indexed into the same Qdrant collection.

Hybrid retrieval will be performed natively by Qdrant.

---

# Architecture

```
                    Chunk
                      │
          ┌───────────┴───────────┐
          │                       │
          ▼                       ▼
Dense Embedding          Sparse Embedding
   (Voyage AI)          (FastEmbed SPLADE)
          │                       │
          └───────────┬───────────┘
                      ▼
              Indexing Platform
                      │
                      ▼
        researchmind_knowledge
             Qdrant Collection
                      │
      ┌───────────────┼───────────────┐
      │               │               │
      ▼               ▼               ▼
 Semantic Search  Sparse Search  Hybrid Search
```

---

# Why This Decision

## 1. Single Source of Truth

All indexed knowledge lives inside one system.

There is no synchronization between:

- Vector database
- Keyword search engine

This greatly simplifies ingestion, deletion, updates, and maintenance.

---

## 2. Simpler Operations

Only one infrastructure component is responsible for retrieval.

Instead of:

```
Qdrant

+

Whoosh
```

ResearchMind operates only:

```
Qdrant
```

This reduces operational complexity and failure points.

---

## 3. Better Hybrid Retrieval

Hybrid retrieval becomes a native capability of the vector database.

Both dense and sparse representations are indexed together.

The retrieval layer can issue:

- Dense search
- Sparse search
- Hybrid search

using a unified API.

---

## 4. Improved Retrieval Quality

FastEmbed SPLADE provides sparse neural representations that generally outperform traditional BM25 on complex search queries.

Advantages include:

- lexical matching
- semantic expansion
- improved recall
- better compatibility with neural embeddings

This aligns well with research paper retrieval.

---

## 5. Lower Maintenance Cost

ResearchMind avoids maintaining:

- Whoosh
- Tantivy
- Elasticsearch
- OpenSearch

No duplicate indexing pipeline is required.

---

# Alternatives Considered

## Option 1 — Dedicated BM25 Platform

Architecture

```
Chunk

↓

BM25 Platform

↓

Whoosh / Tantivy
```

Advantages

- Classic architecture
- Mature technology

Disadvantages

- Separate indexing engine
- Duplicate storage
- Separate deletion logic
- Separate retrieval API
- Increased operational complexity

Decision

Rejected.

---

## Option 2 — Elasticsearch / OpenSearch

Advantages

- Powerful search ecosystem

Disadvantages

- Additional infrastructure
- Additional operational complexity
- Duplicates capabilities already available in Qdrant

Decision

Rejected.

---

## Option 3 — Qdrant Native Hybrid Retrieval

Architecture

```
Dense

+

Sparse

↓

Qdrant
```

Advantages

- Single database
- Single indexing pipeline
- Single deletion path
- Native hybrid retrieval
- Simplified operations
- Production-ready

Decision

Accepted.

---

# Sparse Embedding Model

ResearchMind standardizes on:

**FastEmbed SPLADE**

Reasons:

- Native compatibility with Qdrant
- Strong retrieval quality
- Modern sparse neural retrieval
- Excellent complement to Voyage AI dense embeddings
- Suitable for hybrid retrieval and reranking

---

# Collection Strategy

ResearchMind uses a single collection.

```
researchmind_knowledge
```

The collection represents the platform's knowledge base rather than a specific embedding model.

Embedding model information is stored in artifacts and metadata rather than encoded into collection names.

---

# Impact

The indexing pipeline becomes:

```
Upload

↓

Processing

↓

Chunking

↓

Dense Embedding

↓

Sparse Embedding

↓

Indexing

↓

Qdrant

↓

Knowledge Ready
```

The retrieval pipeline becomes:

```
Query

↓

Dense Retrieval

↓

Sparse Retrieval

↓

Hybrid Search

↓

Metadata Filtering

↓

Voyage Reranker

↓

Context Builder

↓

LLM
```

---

# Future Roadmap

The Retrieval Platform will be implemented in the following order.

1. Semantic Retrieval

2. Sparse Retrieval

3. Hybrid Retrieval

4. Metadata Filtering

5. Voyage Reranker

6. Parent/Child Retrieval

7. Query Decomposition

8. Retrieval Evaluation

Knowledge graphs and GraphRAG remain future enhancements and are intentionally outside the MVP.

---

# Consequences

Positive

- Single retrieval backend
- Lower operational complexity
- Native hybrid retrieval
- Better retrieval quality
- Simplified lifecycle management
- Easier scalability
- Reduced maintenance

Trade-offs

- Sparse embeddings must be generated during ingestion.
- The architecture is optimized for Qdrant.
- Replacing Qdrant in the future would require adapting the indexing implementation, though the higher-level platform abstractions remain unchanged.

---

# Decision

This architecture is **frozen** for the ResearchMind MVP.

No separate BM25 platform will be developed.

ResearchMind will implement hybrid retrieval using:

- Voyage AI dense embeddings
- FastEmbed SPLADE sparse embeddings
- Qdrant native hybrid search

This decision remains in effect unless future benchmarking demonstrates a clear technical need for an alternative retrieval architecture.
