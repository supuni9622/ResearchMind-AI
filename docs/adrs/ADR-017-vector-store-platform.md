# ADR-007: Vector Store Platform Architecture

## Status

Accepted

---

## Date

2026-07-07

---

## Context

The Vector Store Platform is responsible for transforming canonical
Embeddings into searchable vector indexes.

Its responsibility is intentionally limited to indexing and collection
management.

Retrieval, reranking, and hybrid search are implemented by downstream
platforms.

This ADR documents the architectural decisions that define the Vector
Store Platform.

---

# Decision

## 1. First Vector Store Provider

ResearchMind will use **Qdrant** as the first and primary vector store.

Reasons:

- Production-ready vector database
- Excellent filtering support
- High performance HNSW implementation
- Simple local development
- Already included in the project infrastructure
- Clean Python SDK

Future providers (ChromaDB, pgvector, Pinecone, Weaviate, etc.) may be
added through the provider architecture without changing business code.

---

## 2. Embedding Model

ResearchMind standardizes on a single embedding model.

Current embedding provider:

- Voyage AI

Current embedding model:

- voyage-3-lite

The system does **not** support simultaneous indexing across multiple
embedding models.

If the embedding model changes in the future, documents will be
re-indexed.

---

## 3. Collection Strategy

ResearchMind maintains a single logical knowledge collection.

Example:

```
knowledge
```

The collection represents the active searchable knowledge base.

The application does **not** create collections based on:

- embedding provider
- embedding model
- user
- document

This keeps retrieval simple while avoiding unnecessary operational
complexity.

---

## 4. Separation of Responsibilities

### Embedding Platform

Responsible for:

- generating embeddings
- embedding provider configuration
- embedding metadata

Not responsible for:

- vector indexing
- collection management
- retrieval

---

### Vector Store Platform

Responsible for:

- collection creation
- collection management
- vector indexing
- vector deletion
- collection statistics

Not responsible for:

- retrieval
- similarity search
- hybrid search
- reranking

---

### Retrieval Platform

Responsible for:

- similarity search
- metadata filtering
- Top-K retrieval
- hybrid retrieval
- parent retrieval
- future retrieval strategies

---

## 5. Provider Architecture

The Vector Store Platform follows a provider-driven architecture.

```
VectorStoreService
        │
        ▼
VectorStoreRegistry
        │
        ▼
VectorStoreProvider
        │
        ▼
Qdrant
```

Business code depends only on canonical interfaces.

Provider SDKs never leak outside provider implementations.

---

## 6. Canonical Domain Models

The Vector Store Platform defines the following canonical models.

### VectorPayload

Metadata stored alongside indexed vectors.

### VectorStoreRecord

Canonical vector ready for indexing.

### CollectionDefinition

Input model used to create collections.

### CollectionMetadata

Runtime metadata describing an existing collection.

### IndexStatistics

Statistics describing a single indexing execution.

---

## 7. Collection Definition

CollectionDefinition describes the desired state of a collection.

It contains:

- collection name
- vector dimensions
- distance metric

CollectionMetadata represents the current runtime state of the
collection.

It contains:

- CollectionDefinition
- vector count

This separation follows Command/Query Separation (CQS) principles.

---

## 8. Distance Metric

The Vector Store Platform owns vector indexing.

The Embedding Platform recommends the appropriate distance metric for the
embedding model.

Current production configuration:

| Embedding Model | Distance Metric |
|-----------------|-----------------|
| voyage-3-lite | Dot Product |

Future embedding models may recommend different metrics without changing
the Vector Store Platform.

---

## 9. Collection Naming

Collection names are business concepts.

Example:

```
knowledge
```

The application does not encode provider names or embedding model names
into collection names.

---

## 10. Factory Pattern

The Embedding Platform uses an EmbeddingFactory because provider output
must be transformed into canonical models.

The Vector Store Platform intentionally does **not** implement a
VectorStoreFactory.

Reason:

The Vector Store Platform indexes already-canonical
VectorStoreRecord objects.

No provider output requires canonical transformation.

---

## 11. Engineering Principles

The platform follows these principles.

### Build only what is currently required.

Avoid speculative abstractions.

---

### Every abstraction must have a clear responsibility.

Abstractions should exist because they simplify the architecture, not
because future requirements are imagined.

---

### Optimize for production.

Primary goals:

- Retrieval quality
- Simplicity
- Reliability
- Maintainability
- Scalability
- Cost effectiveness

---

## Consequences

### Advantages

- Simple retrieval architecture
- Minimal operational complexity
- Provider independence
- Production-oriented design
- Easy future migration
- Clear separation of responsibilities

### Trade-offs

Changing embedding models requires re-indexing the knowledge base.

This trade-off is accepted because embedding model migrations are rare
compared to retrieval operations.

The resulting architecture is significantly simpler than supporting
multiple embedding spaces simultaneously.

---

## Implementation Status

Completed:

- Platform foundation
- Domain models
- Provider contracts
- Registry
- Composition root

Next:

- Qdrant provider
- Artifact platform
- Processing integration
- End-to-end verification
