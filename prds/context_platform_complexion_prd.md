# ResearchMind — Context Platform Completion PRD

**Document Version:** 1.0
**Platform:** Context Platform
**Phase:** 3.7
**Status:** Ready for Implementation
**Priority:** High

---

# Overview

The Context Platform is approximately **95% complete**.

All major capabilities have been implemented:

- Deduplication
- Parent Expansion
- Adjacent Merge
- Token Budget Compression (V1)
- Embedding Compression (V2)
- LangChain Compression (V3)
- Context Guardrails
- Citation Platform
- Prompt Formatter

The remaining work consists of:

1. Wiring the existing LangChain Compression Provider into the default pipeline.
2. Implementing the LLM Compression Provider.

After completing these items, Phase 3.7 can be considered complete.

---

# Goals

Complete the Context Platform before moving fully into Research Runtime development.

---

# Non Goals

This milestone will NOT include:

- Additional compression providers
- New guardrail providers
- Inline citations
- Source highlighting
- Citation evaluation
- Observability integration
- Agent runtime integration

---

# Current Pipeline

```text
Retrieved Chunks
        ↓
Deduplicate
        ↓
Parent Expansion
        ↓
Adjacent Merge
        ↓
Ordering
        ↓
Compression
        ↓
Guardrails
        ↓
Citation Building
        ↓
Prompt Formatting
        ↓
Prompt Context
```

---

# Deliverable 1

# LangChain Compression Wiring

## Status

Provider already exists.

Implemented:

```text
LangChainCompressionProvider
        ↓
ContextualCompressionRetriever
        ↓
LLMChainExtractor
```

Current limitation:

```text
ContextBuilderService.build()
```

does not pass the user query into the compression stage.

---

## Goal

Enable query-aware contextual compression inside the default context pipeline.

---

## Target Flow

```text
Retrieved Chunks
        ↓
CompressionService
        ↓
LangChainCompressionProvider
        ↓
Compressed Chunks
```

---

## Required Changes

### ContextBuilderService

Current:

```python
build(chunks)
```

Target:

```python
build(
    chunks,
    query: str | None = None,
)
```

---

### CompressionRequest

Ensure query is always propagated.

```python
CompressionRequest(
    chunks=chunks,
    query=query,
)
```

---

### Configuration

Introduce:

```python
CompressionStrategy.LANGCHAIN_CONTEXTUAL
```

Optional configuration:

```python
enable_langchain_compression: bool
```

---

## Acceptance Criteria

- Query passed into compression pipeline
- LangChain provider executable through ContextBuilderService
- Metadata and citations preserved
- Compression failures fallback to original chunks
- Existing tests continue passing

---

# Deliverable 2

# LLM Compression Provider (V4)

---

# Goal

Reduce token usage while preserving important information.

---

## Workflow

```text
Chunk
      ↓
LLM
      ↓
Relevant Summary
      ↓
Compressed Chunk
```

---

# Responsibilities

- Extract relevant information
- Preserve meaning
- Reduce context size
- Preserve citations
- Preserve provenance

---

# Architecture

```text
LLMCompressionProvider
        ↓
GenerationService
        ↓
Compressed ContextChunk
```

The provider should reuse the Generation Platform.

No direct provider calls.

---

# Compression Prompt

Example:

```text
Given the user question and context chunk,
return a concise summary containing only
information relevant to answering the question.
```

---

# Configuration

```python
LLMCompressionConfig(
    provider=GenerationProvider.GROQ,
    max_tokens=300,
    temperature=0,
)
```

---

# Compression Result

Each compressed chunk should contain:

- Original chunk id
- Original document id
- Citations
- Page numbers
- Heading metadata
- Compressed content

---

# Failure Policy

Compression failures should never break generation.

Fallback:

```text
Original Chunk
```

---

# Updated Context Pipeline

```text
Retrieved Chunks
        ↓
Deduplicate
        ↓
Parent Expansion
        ↓
Adjacent Merge
        ↓
Ordering
        ↓
Compression
            ├── Token Budget
            ├── Embedding
            ├── LangChain
            └── LLM
        ↓
Guardrails
        ↓
Citation Building
        ↓
Prompt Formatting
        ↓
Prompt Context
```

---

# Exit Criteria

Phase 3.7 is complete when:

- LangChain compression is integrated into the default pipeline.
- LLM compression provider is implemented.
- Compression failures safely fallback.
- Context artifacts remain unchanged.
- PromptContext generation works end-to-end.

---

# Definition of Done

```text
Retrieved Chunks
        ↓
Deduplicate
        ↓
Parent Expansion
        ↓
Adjacent Merge
        ↓
Ordering
        ↓
Compression (V1-V4)
        ↓
Guardrails
        ↓
Citation Building
        ↓
Prompt Formatting
        ↓
PromptContext
```

---

# Completion Status

```text
Context Platform

████████████████████████████ 100%
```

After completion, the next milestone becomes:

```text
Phase 3.8
Generation Integration Platform
```
