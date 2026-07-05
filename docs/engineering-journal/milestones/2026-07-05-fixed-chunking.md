# Engineering Journal — Phase 2.3.3: Fixed Chunking Platform

**Date:** 2026-07-05

**Status:** ✅ Completed

**Milestone:** Phase 2.3.3 — Fixed Chunking Platform

---

# Overview

This milestone introduced the first production-ready implementation of the Chunking Platform.

For the first time, the AI pipeline is capable of transforming a processed document into retrieval-ready knowledge chunks while remaining completely independent from embedding models, vector databases, and retrieval frameworks.

Rather than implementing chunking as an isolated utility, the platform was designed as an extensible AI pipeline component with interchangeable providers, canonical models, artifact persistence, and experiment support.

This milestone establishes the foundation upon which every future AI capability—including embeddings, retrieval, reranking, evaluation, and agentic workflows—will operate.

---

# Goal

Build the first production-grade chunking pipeline that:

- transforms a canonical ProcessedDocument into retrieval-ready chunks
- produces canonical chunk artifacts
- supports future experimentation
- remains loosely coupled from downstream AI platforms
- allows chunking strategies to be replaced without changing orchestration

---

# What Was Built

## Canonical Chunk Domain

Implemented a framework-independent chunk model.

Created:

- Chunk
- ChunkContent
- ChunkStructure
- ChunkStatistics
- ChunkProvenance
- ChunkExperiment

The chunk model is now the canonical knowledge representation used throughout the AI platform.

---

## Chunk Configuration

Introduced strongly typed configuration models.

Implemented:

- BaseChunkingConfig
- FixedChunkingConfig

Configuration fingerprinting was also added to ensure chunk generation is reproducible across experiments.

---

## Chunk Provider Architecture

Designed a provider-based architecture.

Implemented:

- BaseChunkingProvider
- ChunkingRegistry
- ChunkingService

The orchestration layer now has no knowledge of concrete chunking implementations.

Providers are resolved dynamically through the registry.

---

## Fixed Chunking Provider

Implemented the first production provider.

Capabilities:

- configurable chunk size
- configurable overlap
- deterministic chunk generation
- canonical chunk model generation

This provider serves as the experimental baseline for every future chunking strategy.

---

## Chunk Statistics Service

Created a reusable statistics service responsible for calculating:

- character count
- word count
- sentence count
- estimated token count
- average token length

Statistics generation is completely separated from chunk generation.

---

## Chunk Artifact

Introduced the canonical persistence model for chunking.

Created:

- ChunkArtifact
- ChunkArtifactDocument
- ChunkArtifactStrategy
- ChunkArtifactStatistics
- ChunkArtifactEvaluation

The artifact represents a complete chunking execution rather than an individual chunk.

---

## Chunk Artifact Builder

Implemented a pure builder responsible for converting:

```
list[Chunk]
        ↓
ChunkArtifact
```

The builder contains no storage logic.

---

## Chunk Artifact Writer

Implemented S3 persistence.

Artifacts are now written using the application storage abstraction.

Storage layout:

```
documents/

    {owner_id}/

        {document_id}/

            chunking/

                fixed/

                    {artifact_id}/

                        chunks.json
```

---

## Processing Platform Integration

Integrated the Chunking Platform into the Processing Platform.

The ProcessingService now orchestrates:

```
Download

↓

Parse

↓

Metadata

↓

Statistics

↓

Processing Artifacts

↓

Chunking

↓

Chunk Artifact

↓

Return
```

This establishes ProcessingService as the single orchestrator of the AI pipeline.

---

# Final Pipeline

```
Upload

↓

S3 Original Document

↓

Processing Platform

↓

Parser

↓

ProcessedDocument

↓

Metadata Enrichment

↓

Statistics Enrichment

↓

processed_document.json

↓

Chunking Platform

↓

FixedChunkingProvider

↓

Chunk[]

↓

ChunkArtifactBuilder

↓

ChunkArtifact

↓

chunks.json

↓

Embedding Platform (Future)
```

---

# Final S3 Layout

```
documents/

    {owner_id}/

        {document_id}/

            processing/

                processed_document.json

                parsed.md

                parsed.txt

            chunking/

                fixed/

                    {artifact_id}/

                        chunks.json
```

This layout intentionally isolates each chunking strategy.

Future strategies will produce independent artifacts without overwriting previous experiments.

Example:

```
chunking/

    fixed/

    recursive/

    markdown/

    hierarchical/

    semantic/

    llm/

    adaptive/
```

---

# Engineering Decisions

## 1. Canonical Models First

Every AI platform consumes canonical models.

Instead of exposing parser-specific objects, Processing produces a parser-independent ProcessedDocument.

Similarly, Chunking produces canonical Chunk objects.

This minimizes coupling between AI stages.

---

## 2. Artifact-First Architecture

Every AI stage produces an immutable artifact.

Processing:

```
processed_document.json
```

Chunking:

```
chunks.json
```

Future stages will follow the same principle.

Embeddings:

```
embeddings.json
```

Evaluation:

```
evaluation.json
```

This allows every AI stage to be replayed independently.

---

## 3. Provider-Based Architecture

Chunk generation algorithms are isolated behind providers.

Current:

```
FixedChunkingProvider
```

Future:

- Recursive
- Markdown
- Hierarchical
- Semantic
- LLM
- Adaptive

ProcessingService never changes when new providers are introduced.

---

## 4. Processing Owns Orchestration

The orchestration layer belongs exclusively to ProcessingService.

Providers contain algorithms.

ProcessingService coordinates AI stages.

This creates a clear separation between orchestration and implementation.

---

## 5. Chunking Never Re-parses Documents

Chunking consumes only:

```
ProcessedDocument
```

It never reads PDFs directly.

This prevents duplicated parsing logic and ensures every downstream platform consumes the exact same document representation.

---

## 6. Immutable AI Pipeline

Each stage produces a new canonical representation.

```
Raw PDF

↓

ProcessedDocument

↓

ChunkArtifact

↓

EmbeddingArtifact

↓

Vector Index
```

Stages do not modify previous artifacts.

This enables reproducibility and experiment comparison.

---

# Challenges Encountered

## Missing document_id and filename

Initially the chunk model required document metadata that was unavailable after parsing.

The solution was to enrich the ProcessedDocument immediately after parsing:

```
Parser

↓

ProcessedDocument

↓

ProcessingService injects

document_id

filename
```

This keeps parser implementations focused solely on parsing.

---

## Worker Cache

After updating Pydantic models, Celery workers continued using old model definitions.

Restarting the worker resolved the issue.

This reinforced the importance of restarting long-running workers after schema changes.

---

## Artifact Responsibility

Initially artifact persistence logic was embedded directly inside ProcessingService.

It was later extracted into dedicated private methods, making the orchestration pipeline significantly easier to understand.

---

# Lessons Learned

- Canonical models greatly simplify downstream AI platforms.
- Builders should remain pure functions.
- Writers should contain only storage logic.
- Provider architectures dramatically reduce coupling.
- AI stages should communicate only through canonical artifacts.
- Orchestration belongs in ProcessingService rather than individual providers.
- Experiment metadata should be designed before experimentation begins.

---

# Validation

Successfully verified:

✅ ProcessedDocument generation

✅ Processing artifacts

- processed_document.json
- parsed.md
- parsed.txt

✅ Fixed chunk generation

✅ Chunk statistics

✅ Chunk artifact generation

✅ Chunk artifact persistence

✅ End-to-end pipeline execution

---

# Current AI Pipeline

```
Upload

↓

Storage

↓

Processing Platform

↓

Chunking Platform

↓

Embedding Platform (Next)

↓

Vector Store

↓

Retrieval

↓

Reranking

↓

Evaluation

↓

Agentic AI
```

---

# Technical Debt / Future Improvements

- Make chunking strategy configurable instead of temporarily fixed to `FIXED`.
- Populate evaluation metadata within `ChunkArtifact`.
- Benchmark chunk generation latency.
- Add retrieval quality benchmarks.
- Add Recursive Chunking provider.
- Add Markdown-aware Chunking provider.
- Add Hierarchical Chunking provider.
- Add Semantic Chunking provider.
- Add LLM-guided Chunking provider.
- Add Adaptive Hybrid Chunking provider.
- Compare chunking strategies using identical evaluation datasets.

---

# Next Milestone

## Phase 2.3.4 — Recursive Chunking

Objectives:

- Implement Recursive Chunking Provider.
- Compare against Fixed Chunking.
- Evaluate retrieval quality.
- Measure chunk statistics.
- Benchmark latency.
- Document trade-offs.
- Determine whether Recursive Chunking should become the production default.

This milestone begins the experimental phase of the Chunking Platform, where multiple strategies will be evaluated against identical documents before selecting the most suitable approach for the ResearchMind knowledge platform.
