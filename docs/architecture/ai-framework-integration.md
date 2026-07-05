# AI Framework Integration Strategy

## Status

Approved

---

# Overview

ResearchMind is an AI platform that integrates with multiple external AI frameworks and providers.

Examples include:

- LangChain
- LangGraph
- Docling
- Voyage AI
- OpenAI SDK
- Anthropic SDK
- Qdrant
- ChromaDB
- pgvector

These frameworks provide valuable implementations of AI algorithms and infrastructure.

However, they are not part of the application's core domain model.

ResearchMind owns its business models, orchestration, and contracts.

External frameworks remain implementation details.

---

# Design Principle

> Third-party AI frameworks are implementation details.

Every interaction with an external framework must be encapsulated inside a provider or adapter.

The remainder of the application communicates exclusively through canonical ResearchMind models.

---

# Architectural Boundary

```
                ResearchMind

────────────────────────────────────────────

ProcessingService

ChunkingService

EmbeddingService

RetrievalService

ResearchAgent

Canonical Models

────────────────────────────────────────────
             Provider Boundary
────────────────────────────────────────────

DoclingParser

RecursiveChunkingProvider

OpenAIEmbeddingProvider

VoyageEmbeddingProvider

LangGraphAgentProvider

QdrantVectorStoreProvider

────────────────────────────────────────────
          External Libraries
────────────────────────────────────────────

Docling

LangChain

LangGraph

OpenAI SDK

Voyage AI SDK

Qdrant Client

Anthropic SDK
```

---

# Canonical Models

ResearchMind owns every domain model used throughout the AI pipeline.

Examples include:

- ProcessedDocument
- Chunk
- ChunkArtifact
- Embedding
- SearchResult
- Citation
- Evaluation
- ResearchSession

These models are framework-independent.

They must never inherit from or expose framework-specific classes.

---

# Provider Responsibilities

Providers may use any external framework necessary to implement their functionality.

Examples:

```
RecursiveChunkingProvider
```

Internally uses:

```
RecursiveCharacterTextSplitter
```

Returns:

```
list[Chunk]
```

The rest of the application is unaware that LangChain was used.

---

Another example:

```
OpenAIEmbeddingProvider
```

Internally uses:

```
OpenAIEmbeddings
```

Returns:

```
Embedding
```

---

# Orchestration Layer

Services orchestrate business workflows.

They never call framework APIs directly.

Example:

```
ProcessingService

↓

ChunkingService

↓

RecursiveChunkingProvider

↓

LangChain
```

ProcessingService does not import LangChain.

---

# Dependency Direction

Dependencies always point inward.

```
Application

↓

Providers

↓

External Frameworks
```

External frameworks never depend on application code.

Application code never exposes framework types.

---

# Why This Architecture

This approach provides:

- Stable domain models
- Replaceable AI frameworks
- Easier testing
- Clear architectural boundaries
- Reduced vendor lock-in
- Better maintainability

---

# Framework Examples

## Processing Platform

```
ProcessingService

↓

DoclingParser

↓

Docling SDK

↓

ProcessedDocument
```

---

## Chunking Platform

```
ChunkingService

↓

RecursiveChunkingProvider

↓

RecursiveCharacterTextSplitter

↓

Chunk
```

---

## Embedding Platform

```
EmbeddingService

↓

VoyageEmbeddingProvider

↓

Voyage AI SDK

↓

Embedding
```

---

## Retrieval Platform

```
RetrievalService

↓

LangChain Retriever

↓

SearchResult
```

---

## Agent Platform

```
ResearchAgent

↓

LangGraphAgentProvider

↓

StateGraph
```

---

# Testing Strategy

Tests validate ResearchMind contracts.

Tests should never assert framework-specific objects.

Preferred:

```python
assert isinstance(chunk, Chunk)
```

Avoid:

```python
assert isinstance(document, langchain_core.documents.Document)
```

---

# Future Frameworks

This architecture allows the following frameworks to be introduced without changing the application architecture:

- LangChain
- LangGraph
- LlamaIndex
- Haystack
- DSPy
- CrewAI
- AutoGen
- Semantic Kernel
- OpenAI Agents SDK

Each framework should be encapsulated inside a provider or adapter.

---

# Decision

ResearchMind adopts a provider-based integration strategy.

External AI frameworks are implementation details.

The application communicates exclusively through canonical ResearchMind models and interfaces.

This principle applies consistently across all current and future AI platforms.
