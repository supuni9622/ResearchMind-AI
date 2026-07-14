# Engineering Journal
Date: 2026-07-14

---

# Objective

Continue ResearchMind after completion of Retrieval Platform and begin implementation of Context Platform.

---

# Major Architectural Realizations

## 1. Parent Retrieval Reclassification

Original roadmap:

Retrieval
    ↓
ParentDocumentRetriever
    ↓
Generation

New decision:

Retrieval
    ↓
Context Builder
    ↓
Parent Expansion
    ↓
Generation

Reasoning:

ResearchMind already persists canonical chunk artifacts.

Chunk artifacts become the source of truth.

Parent retrieval is therefore a context enrichment concern rather than a retrieval concern.

Decision:

Move Parent / Child Retrieval from Retrieval Platform to Context Platform.

Status:

ADR Candidate.

---

## 2. Artifact-First Architecture Confirmed

ResearchMind ownership:

Artifacts
Metadata
Document Lifecycle
Knowledge Services

Indexes remain acceleration mechanisms only.

Source of truth:

chunks.json
embeddings.json
indexing.json

Qdrant is not the source of truth.

This decision greatly simplifies future migrations.

---

## 3. Metadata Additions

Added to vector payload:

chunk_artifact_id
chunking_strategy
parent_chunk_id

Reason:

Allow Context Platform to resolve parent chunks without requiring S3 object listing.

Flow:

Retriever
      ↓
metadata
      ↓
ChunkArtifactReader
      ↓
Parent Expansion

---

# Implemented Today

---

## Parallel Retrieval

Implemented:

asyncio.gather(
    dense,
    sparse,
)

Status:

✅ Complete

Future:

metadata retrieval may also become parallel.

---

## Context Platform Foundation

Implemented:

ContextChunk

Added:

retrieval_strategy
parent_chunk_id
parent_content
citation_id
heading
heading_path
page_numbers
merged_chunk_ids

Purpose:

Avoid future schema changes.

---

## ChunkArtifactReader

Implemented.

Purpose:

Load persisted chunk artifacts from storage.

Status:

✅ Complete

---

## ParentExpansionService

Implemented.

Flow:

Retrieved child chunks
        ↓
parent_chunk_id
        ↓
load chunk artifact
        ↓
resolve parent chunk
        ↓
enrich context

Status:

✅ Complete

---

## AdjacentMergeService

Implemented.

Flow:

chunk15
chunk16
chunk17

↓

merged context block

Reason:

NotebookLM-style richer context construction.

Status:

✅ Complete

---

## Compression Platform

Implemented:

context/compression/

interfaces.py
models.py
enums.py
service.py
registry.py
create.py

providers/

token_budget.py
embedding.py
langchain.py
llm.py

Status:

Foundation complete.

---

## Token Budget Compression

Implemented.

Strategy:

Sort by score
Fit into token budget

Status:

✅ V1 Complete

Future:

Embedding redundancy compression.

---

# Context Platform Pipeline

Current:

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
Token Budget Compression
        ↓
Citation Building
        ↓
Prompt Formatting
        ↓
Prompt Context

---

# Updated Roadmap

Phase 3 Retrieval

✅ Dense Retrieval
✅ Sparse Retrieval
✅ Hybrid Retrieval
✅ Metadata Filtering
✅ Reranking
✅ Parallel Retrieval

---

Phase 4 Context Platform

✅ ChunkArtifactReader
✅ ParentExpansionService
✅ AdjacentMergeService
✅ Compression Platform
✅ Token Budget Compression

⏳ Citation Platform
⏳ Prompt Formatter

---

Phase 5 Generation Platform

Not Started.

Planned providers:

Groq
OpenAI
Claude
Gemini
Ollama

Generation architecture:

generation/

models.py
interfaces.py
service.py
registry.py
create.py

providers/

groq.py
openai.py
claude.py
gemini.py
ollama.py

---

# Future Compression Roadmap

V1

Token Budget Compression

Status:

✅

---

V2

Embedding Redundancy Compression

Chunk similarity > 0.95
↓
drop chunk

---

V3

LangChain

ContextualCompressionRetriever

---

V4

LLM Compression

Chunk
↓
Summarize relevant information
↓
Compressed chunk

---

# Important Decisions

1.

Parent retrieval belongs to Context Platform.

2.

Artifacts remain source of truth.

3.

Frameworks remain implementation details.

4.

Generation Platform should only begin after Context Platform completion.

---

# Next Steps

1.

Citation Platform

2.

Prompt Formatter

3.

Generation Platform

4.

Research API

5.

Streaming Chat

6.

Evaluation Platform

7.

Research Runtime
