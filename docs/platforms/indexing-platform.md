# Indexing Platform

**Status:** Planned

**Version:** 1.0

---

# Purpose

The Indexing Platform is responsible for transforming processed knowledge into one or more searchable indexes.

It acts as the bridge between the **Embedding Platform** and the **Retrieval Platform**.

The platform owns the lifecycle of search indexes but **does not perform retrieval**.

---

# Goals

The Indexing Platform exists to:

- Create searchable indexes from processed knowledge
- Support multiple indexing technologies
- Provide a provider-independent indexing architecture
- Generate indexing artifacts
- Maintain index metadata and statistics
- Prepare knowledge for efficient retrieval

---

# Non-Goals

The Indexing Platform does **not**:

- Retrieve documents
- Rank search results
- Generate embeddings
- Generate LLM responses
- Execute AI workflows

These responsibilities belong to other platforms.

---

# Position in the Knowledge Pipeline

```
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
Indexing
    │
    ▼
Retrieval
    │
    ▼
Reranking
    │
    ▼
LLM
```

---

# Responsibilities

The Indexing Platform owns:

- Index orchestration
- Index creation
- Index updates
- Index deletion
- Index statistics
- Index artifacts
- Index lifecycle management

---

# Platform Architecture

```
                Embedding Artifact
                        │
                        ▼
               Indexing Platform
                        │
        ┌───────────────┼────────────────┐
        ▼               ▼                ▼
 Vector Store      BM25 Index      Future Graph Index
                        │
                        ▼
               Index Statistics
                        │
                        ▼
               Index Artifacts
```

---

# Components

## 1. Indexing Service

The orchestration layer.

Responsibilities:

- Coordinate indexing
- Build index records
- Invoke indexing providers
- Produce indexing statistics
- Generate artifacts

---

## 2. Vector Store Platform

Responsible for semantic vector indexes.

Initial implementation:

- Qdrant

Future providers:

- Pinecone
- Weaviate
- Milvus
- pgvector

Responsibilities:

- Collection management
- Vector insertion
- Vector deletion
- Collection metadata

---

## 3. BM25 Platform

Responsible for keyword search indexes.

Responsibilities:

- Build keyword indexes
- Update indexes
- Remove documents
- Maintain term statistics

Initial implementation:

- PostgreSQL Full Text Search or Tantivy (TBD)

---

## 4. Index Artifacts

Every indexing operation generates an artifact.

Example

```
vector_store.json

bm25.json

index_statistics.json
```

Artifacts provide:

- Reproducibility
- Auditing
- Debugging
- Evaluation

---

# Canonical Workflow

```
Embedding Artifact
        │
        ▼
Validate
        │
        ▼
Prepare Index Records
        │
        ▼
Vector Index
        │
        ▼
BM25 Index
        │
        ▼
Generate Statistics
        │
        ▼
Generate Artifacts
```

---

# Folder Structure

```
indexing/

    models.py

    enums.py

    interfaces.py

    exceptions.py

    service.py

    artifacts/

        models.py

        builder.py

        writer.py

    vectorstores/

        service.py

        registry.py

        create.py

        config.py

        providers/

            qdrant.py

    bm25/

        service.py

        config.py

        providers/
```

---

# Canonical Domain Models

The platform communicates using canonical models.

Examples:

- IndexDefinition
- IndexStatistics
- IndexRecord
- IndexArtifact

Provider SDK models never leave provider implementations.

---

# Provider Architecture

```
Indexing Service
        │
        ▼
Provider Interface
        │
        ▼
Provider Implementation
```

Each indexing technology implements its own provider.

---

# Index Lifecycle

```
Create

↓

Update

↓

Validate

↓

Statistics

↓

Artifact

↓

Delete
```

Every indexing operation follows the same lifecycle.

---

# Index Types

## Vector Index

Purpose

Semantic retrieval.

Primary implementation:

- Qdrant

---

## BM25 Index

Purpose

Exact keyword retrieval.

Examples

- API names
- Error messages
- RFC numbers
- Function names
- Technical identifiers

---

## Knowledge Graph Index (Future)

Purpose

Relationship traversal.

Deferred until after MVP.

---

# MVP Scope

The MVP includes:

## Vector Index

- Qdrant
- Collection management
- Batch upsert
- Delete
- Statistics

---

## BM25 Index

- Keyword indexing
- Updates
- Statistics

---

## Index Artifacts

- Vector artifacts
- BM25 artifacts
- Statistics

---

## Evaluation Support

Expose metrics required by the Retrieval Platform.

---

# Deferred Features

The following capabilities are intentionally postponed:

- Knowledge Graph indexing
- Graph embeddings
- Incremental graph updates
- Distributed indexing
- Multi-region indexing
- Online index rebuilding

---

# Future Roadmap

## Phase 1

- Vector Index

---

## Phase 2

- BM25 Index

---

## Phase 3

- Unified Indexing Service

---

## Phase 4

- Knowledge Graph Index

---

## Phase 5

- Distributed Index Management

---

# Design Principles

The Indexing Platform follows these principles.

## Separation of Concerns

Indexing prepares searchable knowledge.

Retrieval consumes searchable knowledge.

---

## Provider Independence

Indexing providers are replaceable.

Business logic never depends on provider SDKs.

---

## Canonical Models

Communication between platforms uses canonical models.

Provider-specific models never leave provider implementations.

---

## Artifact Driven

Every indexing operation produces immutable artifacts.

Artifacts become the contract between indexing and downstream platforms.

---

## Production First

Every component should support:

- Reliability
- Observability
- Scalability
- Cost efficiency

---

# Relationship to Other Platforms

```
Embedding Platform

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

The Indexing Platform is responsible only for preparing searchable indexes.

Searching those indexes is the responsibility of the Retrieval Platform.
