# Embedding Platform Architecture

**Project:** ResearchMind AI
**Platform:** Knowledge Platform
**Phase:** 2.4 — Embedding Platform
**Status:** ✅ Completed (V1)
**Last Updated:** 2026-07-06

---

# Overview

The Embedding Platform is responsible for transforming canonical document chunks into canonical vector embeddings that can be consumed by downstream AI platforms.

Unlike provider SDKs, the Embedding Platform exposes a stable, provider-independent representation of embeddings. This allows downstream systems to evolve independently from embedding providers such as Sentence Transformers, Voyage AI, or OpenAI.

The platform follows the same architectural principles as every other AI platform in ResearchMind:

- Clean Architecture
- Canonical Models
- Provider Pattern
- Registry Pattern
- Factory Pattern
- Dependency Injection
- Composition Root
- Framework Independence

Embedding providers remain implementation details and are never exposed outside the platform.

---

# Purpose

The Embedding Platform exists to convert canonical chunks into semantic vector representations while preserving a stable contract for every downstream AI capability.

The platform intentionally separates:

- embedding generation
- provider implementation
- orchestration
- persistence
- experimentation

This separation enables new embedding providers to be added without impacting any downstream platform.

---

# Design Goals

The platform was designed with the following goals.

## Provider Independence

No downstream platform depends on Sentence Transformers, OpenAI, Voyage AI, LangChain, or any provider SDK.

Only canonical Embedding models are exposed.

---

## Stable Canonical Models

Every provider produces exactly the same Embedding model regardless of implementation.

Downstream platforms always consume canonical models.

---

## Extensibility

Adding a new embedding provider should require only:

- provider implementation
- provider registration

No service or downstream code should change.

---

## Experimentation Ready

Embedding metadata captures:

- provider
- provider version
- model
- configuration fingerprint

allowing reproducible experiments and future evaluation.

---

## Production First

The platform is designed for production systems rather than demo applications.

Artifacts are versioned.

Providers are replaceable.

Frameworks remain internal implementation details.

---

# Position in the AI Pipeline

The Embedding Platform is the second AI platform within the Knowledge Platform.

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

Retrieval Platform

↓

Reranking Platform
```

Each platform consumes the canonical artifact produced by the previous platform.

---

# High-Level Architecture

```text
ChunkArtifact
        │
        ▼
EmbeddingService
        │
        ▼
EmbeddingRegistry
        │
        ▼
EmbeddingProvider
        │
        ▼
EmbeddingFactory
        │
        ▼
Embedding[]
        │
        ▼
EmbeddingArtifactBuilder
        │
        ▼
EmbeddingArtifact
        │
        ▼
EmbeddingArtifactWriter
        │
        ▼
Amazon S3
```

The provider generates vectors.

The factory creates canonical models.

The builder constructs the persistence artifact.

The writer persists the artifact.

Each component has exactly one responsibility.

---

# Folder Structure

```text
app/

└── ai/

    └── knowledge/

        └── embeddings/

            base.py

            config.py

            create.py

            enums.py

            exceptions.py

            factory.py

            interfaces.py

            models.py

            registry.py

            service.py

            providers/

                sentence_transformers.py

            artifacts/

                models.py

                builder.py

                writer.py
```

---

# Data Flow

The complete execution flow is shown below.

```text
ChunkArtifact

↓

EmbeddingService

↓

EmbeddingRegistry

↓

SentenceTransformerEmbeddingProvider

↓

SentenceTransformer.encode()

↓

EmbeddingFactory

↓

Embedding[]

↓

EmbeddingArtifactBuilder

↓

EmbeddingArtifact

↓

EmbeddingArtifactWriter

↓

documents/

    {owner}

        {document}

            embeddings/

                sentence_transformers/

                    {artifact-id}/

                        embeddings.json
```

---

# Component Responsibilities

## EmbeddingService

Responsibilities

- Orchestrates embedding generation
- Resolves providers from the registry
- Delegates embedding generation

Does NOT

- build artifacts
- persist artifacts
- know provider implementations

---

## EmbeddingRegistry

Responsibilities

- Register providers
- Resolve providers

Does NOT

- create providers
- perform embedding generation

---

## EmbeddingProvider

Responsibilities

- Generate vectors
- Convert provider output into canonical embeddings

Does NOT

- persist artifacts
- build artifacts
- expose SDK-specific models

---

## EmbeddingFactory

Responsibilities

Centralizes creation of canonical Embedding models.

Every provider delegates object construction to the factory.

Benefits

- single construction logic
- schema consistency
- reduced duplication

---

## EmbeddingArtifactBuilder

Responsibilities

Transforms

```text
ChunkArtifact
+
Embedding[]
```

into

```text
EmbeddingArtifact
```

The builder performs no storage operations.

---

## EmbeddingArtifactWriter

Responsibilities

Persists EmbeddingArtifact to storage.

The writer has no knowledge of embedding generation.

---

# Canonical Models

The Embedding Platform exposes only canonical models.

```text
Embedding

├── Provenance

├── Provider Metadata

├── Statistics

├── Experiment

└── Vector
```

Every provider produces this exact structure.

No provider SDK objects leave the platform.

---

# Provider Pattern

Every embedding implementation satisfies the same interface.

```text
EmbeddingProvider

↓

Sentence Transformers

Voyage AI

OpenAI

BGE

Instructor

Nomic
```

The service depends only on the abstraction.

New providers can be added without modifying application code.

---

# Registry Pattern

Providers are registered during application startup.

```text
EmbeddingRegistry

↓

register()

↓

SentenceTransformerProvider

↓

OpenAIProvider

↓

VoyageProvider
```

The registry resolves providers by provider enum.

---

# Factory Pattern

Providers never construct Embedding objects directly.

Instead

```text
Provider Output

↓

EmbeddingFactory

↓

Canonical Embedding
```

This ensures every embedding shares the same schema regardless of provider.

---

# Artifact Lifecycle

The Embedding Platform produces a single canonical persistence artifact.

```text
Embedding[]

↓

EmbeddingArtifactBuilder

↓

EmbeddingArtifact

↓

EmbeddingArtifactWriter

↓

embeddings.json
```

The artifact becomes the input for downstream AI platforms.

---

# ProcessingService Integration

The Embedding Platform is integrated directly into the production processing pipeline.

Current execution flow

```text
Parse

↓

Metadata

↓

Statistics

↓

Processing Artifact

↓

Chunking Stage

↓

Chunk Artifact

↓

Embedding Stage

↓

Embedding Artifact

↓

Completed
```

ProcessingService acts as the orchestration layer.

Each AI platform contributes a private execution stage.

Example

```text
_execute_chunking_stage()

↓

_execute_embedding_stage()

↓

_execute_vector_store_stage()

↓

_execute_retrieval_stage()
```

This keeps orchestration centralized while allowing every platform to evolve independently.

---

# Storage Layout

Embedding artifacts are stored independently from processing artifacts.

```text
documents/

    {owner_id}/

        {document_id}/

            embeddings/

                sentence_transformers/

                    {artifact_id}/

                        embeddings.json
```

Future providers naturally fit this layout.

```text
embeddings/

    sentence_transformers/

    voyage/

    openai/

    bge/

    instructor/
```

---

# Current Provider

The first implementation is

```text
SentenceTransformerEmbeddingProvider
```

Characteristics

- Lazy model loading
- Cached model instance
- Batch embedding generation
- Canonical output
- Provider-independent architecture

The provider encapsulates all Sentence Transformers logic.

No downstream code depends on the library.

---

# Extension Guide

Adding a new provider requires only four steps.

## Step 1

Create a provider.

Example

```text
providers/

    voyage.py
```

---

## Step 2

Implement

```python
EmbeddingProvider
```

---

## Step 3

Register the provider.

```python
EmbeddingRegistry.register(...)
```

---

## Step 4

Update the composition root.

No other code changes are required.

Neither the service nor downstream platforms require modification.

---

# Runtime Evaluation

Runtime evaluation is intentionally separated from the Embedding Platform.

The platform focuses only on business logic.

Execution metrics are collected by the processing pipeline.

Future metrics include

- execution time
- memory usage
- artifact size
- provider latency
- API cost
- token usage

This follows the separation of business logic and observability.

---

# Future Roadmap

## Completed

- Canonical models
- Provider abstraction
- Registry
- Factory
- Artifact Builder
- Artifact Writer
- Sentence Transformers provider
- ProcessingService integration
- End-to-end pipeline verification

---

## Next

Phase 2.4.4

Observability Platform

- Runtime metrics
- Stage metrics
- Pipeline metrics
- Performance baselines

---

## Upcoming Providers

- Voyage AI
- OpenAI
- BGE
- Instructor
- Nomic

---

## Downstream Platforms

After embeddings, the Knowledge Platform continues with

```text
Embedding Platform

↓

Vector Store Platform

↓

Retrieval Platform

↓

Reranking Platform

↓

Pipeline Evaluation

↓

Experimentation Platform
```

The Embedding Platform serves as the foundation for semantic search and every subsequent AI capability within ResearchMind.

---

# Key Architectural Decisions

The Embedding Platform follows several long-term architectural principles.

- Every platform consumes the canonical artifact produced by the previous platform.
- Providers never expose framework-specific models.
- Services orchestrate behavior but do not implement provider logic.
- Factories own canonical model construction.
- Builders own artifact construction.
- Writers own persistence.
- ProcessingService orchestrates the production AI pipeline through isolated execution stages.
- Runtime evaluation and observability remain separate from business logic.
- New providers should be added through registration rather than modification of existing services.

These principles ensure the platform remains extensible, testable, framework-independent, and suitable for long-term production evolution.
