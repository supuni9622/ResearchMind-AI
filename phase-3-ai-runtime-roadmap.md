# ResearchMind AI — Roadmap
## Retrieval, Context, Generation & Research Runtime

**Status:** Frozen (v2.0)

**Last Updated:** 2026-07-16

---

# ResearchMind Maturity Vision

```text
NotebookLM++
      ↓
Perplexity v1
      ↓
Open Deep Research
      ↓
Manus / Glean
```

Current State:

```text
NotebookLM++
    +
Perplexity Foundation
```

Hybrid Retrieval, Reranking, Parent Expansion, Compression, Context Guardrails, and strategy-based Prompt Formatting are all implemented — beyond a plain NotebookLM clone and closing in on Perplexity v1. A standalone, platform-wide Guardrails Platform (Milestone 3.13 below — input/retrieval/generation/runtime stages, Source Trust, policies, scoring, artifacts) is now complete as an MVP foundation.

Current Focus:

```text
Phase 3.7
Context Building Platform (~90% complete — closing out)
    ↓
Phase 3.8
Generation Platform (~65% complete — structured output, input/output/
hallucination validation + scoring, regeneration, prompt bridge done;
runtime validators/contracts, routing/caching/artifacts remain)
```

---

# Purpose

The Knowledge Ingestion Platform is now complete.

```text
Upload
↓
Processing
↓
Chunking
↓
Embeddings
↓
Indexing
↓
Vector Store
```

ResearchMind now transitions into an AI Research Platform.

The next stages focus on consuming, enriching, reasoning over, and generating knowledge.

---

# Engineering Principles

- Build complete vertical slices.
- Every platform owns one business capability.
- Canonical domain models only.
- Provider independence.
- Production-first engineering.
- Evaluation-driven development.
- Documentation-first.
- Freeze architecture after validation.
- Frameworks remain implementation details.

# Overall AI Pipeline

```text
                    Upload Platform
                          │
                          ▼
                 Processing Platform
                          │
                          ▼
                 Chunking Platform
                          │
                          ▼
                Embedding Platform
                          │
                          ▼
               Vector Store Platform
                          │
                          ▼
                Retrieval Platform
                          │
                          ▼
               Reranking Platform
                          │
                          ▼
             Context Building Platform
                          │
                          ▼
                Generation Platform
                          │
                          ▼
                Evaluation Platform
                          │
                          ▼
                Research Runtime
                          │
                          ▼
                 Long-Term Platform
```

# Phase 3.4 — Retrieval Strategies

**Status:** 🟡 In Progress

---

## Parallel Retrieval

### Status: ✅ Complete

Implemented:

```python
asyncio.gather(
    dense_search(),
    sparse_search(),
)
```

Current workflow:

```text
Dense Retrieval
        │
Sparse Retrieval
        │
        ▼
Parallel Execution
        │
        ▼
Fusion
```

Future:

```python
asyncio.gather(
    dense,
    sparse,
    metadata,
)
```

---

## Parent / Child Retrieval

### Status: 🔄 Reclassified

Originally planned under Retrieval.

After architecture validation, Parent/Child retrieval has been moved into the Context Platform.

Reason:

ResearchMind persists canonical chunk artifacts.

Retrieval should find knowledge.

Context Building should enrich knowledge.

Workflow:

```text
Retriever
      ↓
Retrieved Child Chunks
      ↓
Parent Expansion
      ↓
Prompt Context
```

Implemented Foundations:

- ChunkArtifactReader
- ParentExpansionService
- AdjacentMergeService

---

## Query Decomposition

### Status: ❌ Not Started

Moved to:

### Research Runtime Platform

Workflow:

```text
Question
      ↓
Planner
      ↓
Sub Questions
      ↓
Parallel Retrieval
      ↓
Merge
```

Likely Framework:

- LangGraph

---

## Deliverables

### Complete

- ✅ Parallel Retrieval

### Context Platform

- 🔄 Parent Expansion

### Runtime Platform

- ❌ Query Decomposition

# Phase 3.7 — Context Building Platform

**Status:** 🟡 ~90% Complete

---

## Goal

Prepare retrieved knowledge for LLM consumption.

---

## Architectural Decision

Retrieval finds knowledge.

Context Building prepares knowledge.

---

## Responsibilities

### Implemented

- ✅ Deduplication
- ✅ Parent Expansion
- ✅ Adjacent Chunk Merge
- ✅ Compression Platform Foundation
- ✅ Token Budget Compression (V1)
- ✅ Embedding Redundancy Compression (V2)
- ✅ Context Guardrails (V1) — provider architecture, `RuleBasedGuardrailProvider`, risk scoring, statistics
- ✅ Citation Platform — citation IDs, pages, headings, chunk IDs
- ✅ Prompt Formatter — strategy-based (`DEFAULT`, `NOTEBOOKLM`, `PERPLEXITY`, `RESEARCH`, `AGENT`)

### Future

- LangChain contextual compression (V3)
- LLM compression (V4)
- Inline citations, source highlighting, citation evaluation
- LlamaGuard, NeMo Guardrails, Lakera (Guardrails V2)

---

## Workflow

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
Compression (Token Budget + Embedding)
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

## Compression Roadmap

### V1

```text
Top 20
↓
Sort by score
↓
Fit token budget
↓
Top 5-10
```

Status:

✅ Complete

---

### V2

```text
Chunk similarity > 0.95
↓
Drop duplicate chunks
```

Status:

✅ Complete

---

### V3

LangChain

```text
ContextualCompressionRetriever
```

---

### V4

LLM Compression

```text
Chunk
↓
Relevant Summary
↓
Compressed Chunk
```

---

## Deliverables

### Complete

- ✅ Context Models
- ✅ ChunkArtifactReader
- ✅ ParentExpansionService
- ✅ AdjacentMergeService
- ✅ Compression Platform (Token Budget + Embedding, V1/V2)
- ✅ Context Guardrails (V1)
- ✅ Citation Platform
- ✅ Prompt Formatter

### Remaining

- ❌ LangChain Compression Provider (V3)
- ❌ LLM Compression Provider (V4)

# Phase 3.8 — Generation Platform

**Status:** 🟡 ~65% Complete — structured output, a multi-stage
Validation Platform integration (input/output/hallucination validators,
registry, scoring, `ValidationReport`), regeneration, and
prompt-template integration are done; per-runtime Validation
Contracts/Runtime Validators, capability-based routing, caching, and
artifacts remain. Generation-level guardrails are no longer part of
this gap — see Milestone 3.13 (Guardrails Platform) below, now complete
as a standalone MVP foundation not yet wired into this service.

---

## Goal

Generate answers from prepared context.

---

## Responsibilities

- ✅ Prompt templates — `generation/prompts/` (pre-existing, substantial:
  disk-loaded templates, variable rendering, few-shot examples,
  versioning) now bridged into Generation via
  `GenerationService.generate_from_template()`
- ✅ Prompt registry — `PromptRegistry` (pre-existing)
- ✅ LLM provider abstraction — all five providers implemented
- ✅ Streaming — per-provider `stream()`
- ✅ Structured output — native decoding (all 5 providers) + parser/repair
  fallback + Markdown/XML registry + optional LangChain
  `with_structured_output()` path (4/5 providers) + regenerate-on-invalid
  loop with corrective feedback
- 🟡 Validation Platform integration — input validators (empty prompt,
  token budget, provider limits, context quality), output validators
  (schema via `jsonschema`, JSON parseability, fabricated-citation
  detection), a lightweight no-LLM hallucination/groundedness validator,
  a `ValidationRegistry`, weighted scoring, and a multi-stage
  `ValidationReport` all implemented; per-runtime Contracts/Runtime
  Validators and a few PRD output checks (completeness/consistency/
  formatting/response-size) remain — see `validation_platform_prd.md`
- ❌ Research chains — not started

---

## Supported Providers

- Groq
- OpenAI
- Claude
- Gemini
- Ollama

---

## Architecture

```text
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

    structured_output/      # registry, parsers, repair — connected end-to-end
    validation/              # ValidationRegistry, ValidationService, scoring, input/output/hallucination validators
    langchain/                # with_structured_output() bridge (4/5 providers)
    prompts/                  # pre-existing template platform, now bridged in
```

---

## Workflow

```text
Prompt Context (+ optional PromptService template rendering)
        ↓
Generation Service
        ↓
LLM Provider — native structured output → parser fallback
        ↓
Validation (input + output + hallucination stages → ValidationReport)
        ↓
Regeneration (opt-in, corrective feedback) if parsing failed or the output stage is invalid
        ↓
Generated Answer
```

See `docs/architecture/structured-output-platform.md` for the detailed,
continuously-updated breakdown of this subsystem.

---

## LangChain Usage (Implemented)

- `with_structured_output()` — `generation/langchain/output_parsers.py`,
  a standalone alternative to the native-SDK path for OpenAI, Claude,
  Gemini, and Ollama (not Groq — `langchain-groq` has no release
  compatible with the pinned `groq>=1.5.0` SDK floor)
- `PydanticOutputParser` / `JsonOutputParser` — power the Structured
  Output Platform's `PydanticParser`/`JsonParser` and the
  `generate_from_template()` format-instructions step
- `ChatPromptTemplate` / few-shot prompt templates — power the
  pre-existing Prompt Platform

Still potential future usage: LCEL composition.

Frameworks remain implementation details.

---

## Deliverables

- ✅ Generation service
- ✅ Provider abstraction
- ✅ Prompt platform (bridged in)
- ✅ Streaming support
- ✅ Structured output (native + fallback + registry + LangChain + regeneration)
- 🟡 Validation Platform integration (input/output/hallucination validators, registry, scoring, `ValidationReport` done; runtime validators/contracts, completeness/consistency/formatting/response-size remain)
- ❌ Capability-based routing engine
- ❌ Caching
- ❌ Artifacts

# Phase 3.13 — Guardrails Platform

**Status:** ✅ Complete (MVP Foundation, per `guardrails_platform_prd.md`)

---

## Goal

Answer a different question than Validation: not "did the system produce a good output?" but "should the system even perform this operation?"

---

## Responsibilities

- ✅ Input Guardrails — prompt injection/jailbreak detection (P0), scope validation, PII detection (foundation); rate limit/toxicity are foundation interfaces (always-allow)
- ✅ Retrieval Guardrails — Context Sanitization (composes the pre-existing `ContextGuardrailService`, does not duplicate it), a new Source Trust Platform (P1), Citation Integrity; Access Control is a foundation interface (permissive default)
- ✅ Generation Guardrails — Faithfulness Enforcement and Schema Enforcement (both wrap the Validation Platform's validators per the PRD's explicit reuse instruction), PII Leakage; Moderation is a foundation interface (always-allow)
- ✅ Runtime Guardrails — Budget Guardrail (P1, "implement immediately"), Loop Detection (real algorithm); Tool Policy and Approval Gate are foundation interfaces only, deliberately unimplemented (the future LangGraph-interrupt seam)
- ✅ `GuardrailService`, `GuardrailRegistry`, weighted risk scoring, fail/risk/regeneration/runtime policies, `GuardrailArtifactWriter`
- ❌ Wiring into `GenerationService`, the context builder, or a router — the PRD's own "Generation Integration" is a later phase, same posture the Validation Platform shipped with

---

## Deliverables

- ✅ Standalone `apps/api/app/ai/guardrails/` package, 113 new unit tests, full repo suite/ruff/mypy clean
- ✅ Two dead, zero-reference scaffolds removed (`app/ai/guardrails/{policies,scanners}.py`, all of `app/ai/runtime/generation/guardrails/`)
- ❌ LLM-based classifiers (Llama Guard, Lakera, NeMo Guardrails) — explicitly skipped for MVP
- ❌ Wiring into the live generation pipeline

# Final MVP Pipeline

```text
                    User Query
                         │
          ┌──────────────┴──────────────┐
          │                             │
     Sparse Search               Dense Search
          │                             │
       Top 50                        Top 50
          └──────────────┬──────────────┘
                         │
                  Parallel Execution
                         │
                  Reciprocal Rank Fusion
                         │
                     Top 20 Results
                         │
                     Reranker
                         │
                      Top 5 Results
                         │
                  Context Builder
                         │
                  Parent Expansion
                         │
                  Adjacent Merge
                         │
               Token Budget Compression
                         │
                  Citation Builder
                         │
                  Prompt Formatter
                         │
                 Generation Platform
                         │
                    Final Answer
                    + Citations
```

Milestone	Platform	Deliverables	Status
3.1	Retrieval Foundation	Query processing, dense retrieval	✅ Complete
3.2	Sparse Retrieval	SPLADE, sparse search	✅ Complete
3.3	Hybrid Retrieval	Dense + Sparse + RRF	✅ Complete
3.4	Retrieval Strategies	Parallel Retrieval, Runtime Query Decomposition	✅ Parallel Retrieval complete (Query Decomposition moved to 3.11)
3.5	Result Processing	Metadata filtering, Top-K	✅ Complete
3.6	Reranking Platform	Voyage, CrossEncoder	✅ Complete
3.7	Context Building Platform	Parent Expansion, Merge, Compression, Guardrails, Citations, Prompt Formatter	🟡 ~90% Complete (LangChain + LLM compression remain)
3.8	Generation Platform	Multi-provider LLM runtime, structured output, validation, regeneration	🟡 ~65% Complete — runtime validators/contracts, routing/caching/artifacts remain
3.9	Research APIs	/research, streaming, citations	❌ Not Started
3.10	Evaluation Platform	Groundedness, Hallucinations, Citation Accuracy	🟡 Retrieval evaluation complete
3.11	Research Runtime	Planner, Query Decomposition, Agents	❌ Not Started
3.12	Long-Term Platform	Research Sessions, Memory, MCP	❌ Not Started
3.13	Guardrails Platform	Input/Retrieval/Generation/Runtime guardrails, Source Trust, policies, scoring, artifacts	✅ MVP Foundation Complete (standalone, not yet wired into Generation Platform)

# Architecture Principles

- Retrieval is responsible only for finding knowledge.
- Reranking improves ordering.
- Context Building prepares knowledge for LLM consumption.
- Generation owns all LLM interactions.
- Evaluation measures every improvement.
- Runtime owns planning and reasoning.
- Artifacts remain the source of truth.
- Vector databases are acceleration mechanisms only.
- Frameworks remain implementation details.
- Provider SDKs never leak outside provider implementations.
