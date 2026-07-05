# Chunking Platform Architecture

**Status:** Frozen (Phase 2.3 Foundation)

**Phase:** 2.3 — Chunking Platform

---

# Overview

The Chunking Platform is the first major AI Engineering component of the ResearchMind Knowledge Platform.

Its responsibility is to transform a canonical processed document into semantically meaningful chunks that can later be embedded, indexed, retrieved, reranked, and used by downstream AI systems.

Chunking is intentionally designed as an independent platform rather than being tightly coupled to parsing, embeddings, or vector databases.

This allows ResearchMind to:

- experiment with multiple chunking strategies
- compare retrieval quality
- benchmark chunking algorithms
- rerun chunking without reparsing documents
- evolve AI pipelines independently

---

# Why Chunking Exists

Large Language Models cannot consume entire documents.

Modern LLMs have context window limitations.

Instead of embedding or retrieving entire documents, documents are divided into smaller knowledge units called **chunks**.

Those chunks become the fundamental units for:

- Embeddings
- Vector Search
- Retrieval
- Reranking
- Context Building
- Citation
- Agent Memory

Without chunking:

- retrieval quality decreases
- embeddings become less meaningful
- latency increases
- hallucinations become more likely

Chunking is therefore the foundation of every modern Retrieval-Augmented Generation (RAG) system.

---

# Position Within the AI Pipeline

```
                Upload Platform
                       │
                       ▼
                Original Document
                     (S3)
                       │
                       ▼
               Document Processing
                       │
                       ▼
              ProcessedDocument
          (Canonical Processing Model)
                       │
         ┌─────────────┴─────────────┐
         │                           │
         ▼                           ▼
 Processing Artifacts          Chunking Platform
(processed_document.json)            │
(parsed.md)                          ▼
(parsed.txt)                   list[Chunk]
                                    │
                                    ▼
                            Chunk Artifacts
                             (chunks.json)
                                    │
                                    ▼
                           Embedding Platform
                                    │
                                    ▼
                               Vector Store
                                    │
                                    ▼
                                Retrieval
                                    │
                                    ▼
                                Reranking
                                    │
                                    ▼
                              LLM Generation
                                    │
                                    ▼
                                Evaluation
```

---

# Canonical Input

The Chunking Platform consumes exactly one model:

```
ProcessedDocument
```

It never consumes:

- original PDF
- parsed.txt
- parsed.md

Those files are artifacts.

The canonical processing model is always:

```
ProcessedDocument
```

---

# Document Representations

The canonical ProcessedDocument contains multiple representations.

```
ProcessedDocument

├── raw_text

├── markdown

└── blocks
```

Different chunking strategies operate on different representations.

| Strategy | Input Representation |
|-----------|----------------------|
| Fixed | raw_text |
| Recursive | raw_text |
| Markdown | markdown |
| Hierarchical | blocks |
| Semantic | blocks / raw_text |
| LLM | markdown |

This allows every strategy to use the representation most appropriate for its algorithm while keeping a single canonical processing model.

---

# Canonical Output

Every provider produces exactly one canonical output.

```
Chunk
```

No provider returns provider-specific models.

Every downstream AI platform consumes the same Chunk model.

```
ProcessedDocument

↓

Chunk

↓

Embedding

↓

Retrieval

↓

Evaluation
```

---

# Chunking Architecture

```
                     ChunkingService
                            │
                            ▼
                    ChunkingRegistry
                            │
                ┌───────────┼───────────┐
                ▼           ▼           ▼
             Fixed     Recursive   Markdown
             Provider    Provider    Provider
                │           │           │
                └───────────┼───────────┘
                            ▼
                 BaseChunkingProvider
                            │
                            ▼
               ChunkStatisticsService
                            │
                            ▼
                         Chunk
```

---

# Responsibilities

## ChunkingService

High-level application service.

Responsible for:

- selecting providers
- orchestration

Not responsible for chunking algorithms.

---

## ChunkingRegistry

Responsible for:

- provider registration
- provider lookup

The registry knows which provider implements each strategy.

---

## BaseChunkingProvider

Provides shared functionality:

- chunk construction
- provenance generation
- experiment metadata
- statistics integration

Concrete providers only determine chunk boundaries.

---

## ChunkStatisticsService

Shared service responsible for:

- character count
- word count
- sentence count
- estimated token count
- average token length

All providers reuse this service.

---

# Current Provider

Current implementation:

```
FixedChunkingProvider
```

Algorithm:

```
ProcessedDocument.raw_text

↓

Fixed-size window

↓

Overlap

↓

Chunk
```

This provider acts as the experimental baseline.

All future providers are evaluated relative to it.

---

# Planned Providers

The architecture supports multiple interchangeable providers.

## Fixed Chunking

Baseline implementation.

Purpose:

- establish baseline retrieval quality
- benchmark latency
- compare future algorithms

---

## Recursive Chunking

Splits text while preserving natural language boundaries.

Expected improvement:

- better retrieval quality
- improved semantic coherence

---

## Markdown Chunking

Uses Markdown document structure.

Expected improvement:

- heading preservation
- section-aware retrieval

---

## Hierarchical Chunking

Uses semantic document blocks.

Expected improvement:

- parent-child retrieval
- document hierarchy preservation

---

## Semantic Chunking

Uses semantic similarity.

Expected improvement:

- concept-aware chunk boundaries

---

## LLM Chunking

Uses an LLM to determine chunk boundaries.

Expected improvement:

- highest semantic quality

Trade-off:

- increased latency
- increased cost

---

# Why Multiple Strategies?

There is no universally optimal chunking algorithm.

Different documents require different approaches.

ResearchMind treats chunking as an experiment rather than a fixed implementation.

The platform is therefore designed for:

- experimentation
- benchmarking
- reproducibility

---

# Experiment Metadata

Every generated chunk stores metadata describing how it was produced.

```
strategy

strategy_version

configuration_fingerprint

experiment_tag
```

This enables:

- reproducibility
- benchmarking
- regression testing
- A/B experiments

---

# Chunk Artifacts

The Chunking Platform produces:

```
chunks.json
```

Unlike embeddings, chunks are persisted.

Reasons:

- avoid rerunning Docling
- enable chunk experimentation
- support re-indexing
- support evaluation

Future workflows can regenerate embeddings directly from chunks.json.

---

# Processing Flow

Normal production flow:

```
PDF

↓

Parser

↓

ProcessedDocument (memory)

├──► Processing Artifacts

└──► Chunking

        ↓

      Chunk

        ↓

   chunks.json

        ↓

       S3
```

No S3 read occurs during normal processing.

---

# Reprocessing Flow

ResearchMind also supports offline experimentation.

```
processed_document.json

↓

ProcessedDocument

↓

Chunking

↓

chunks.json
```

This avoids rerunning expensive parsing.

---

# Design Principles

The Chunking Platform follows several core principles.

## Canonical Models

Every stage exposes one canonical model.

Processing:

```
ProcessedDocument
```

Chunking:

```
Chunk
```

No framework-specific models flow between stages.

---

## Loose Coupling

Chunking depends only on:

```
ProcessedDocument
```

It has no knowledge of:

- Docling
- S3
- PostgreSQL
- Embedding Platform
- Vector Store

---

## Strategy Pattern

Every chunking algorithm implements the same interface.

Adding a provider requires only:

- implementing the provider
- registering it

No application code changes.

---

## Shared Services

Cross-cutting logic is centralized.

Examples:

- statistics
- provenance
- experiment metadata

Providers implement algorithms only.

---

## Experimentation First

ResearchMind is designed to compare chunking strategies.

The architecture prioritizes:

- repeatability
- reproducibility
- measurable evaluation

rather than prematurely selecting a single algorithm.

---

# Frozen Phase 2.3 Roadmap

```
2.3.1

Chunking Foundation
✓

↓

2.3.2

Fixed Chunking
✓

↓

2.3.3

Platform Integration
✓

↓

2.3.4

Chunk Artifacts

↓

2.3.5

Recursive Chunking

↓

2.3.6

Markdown Chunking

↓

2.3.7

Chunk Evaluation Platform

↓

2.3.8

Hierarchical Chunking

↓

2.3.9

Semantic Chunking

↓

2.3.10

LLM Chunking

↓

2.3.11

Adaptive Hybrid Chunking
```

---

# Architecture Status

The Chunking Platform architecture is considered **frozen**.

Future work should focus on:

- implementing providers
- experimentation
- benchmarking
- evaluation

rather than redesigning the architecture.

Architecture changes should only occur if implementation reveals a genuine limitation.
