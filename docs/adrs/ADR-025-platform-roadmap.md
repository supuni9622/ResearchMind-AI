# ADR-025: ResearchMind Platform Roadmap

Status: Accepted

Date: 2026-07-15

Supersedes: None

Related:

- ADR-023 Framework Integration Strategy
- ADR-024 Generation Model Strategy

---

# Context

ResearchMind originally started as a Retrieval-Augmented Generation (RAG)
learning project.

As the platform evolved, several independent subsystems emerged:

- Knowledge Platform
- Context Platform
- Generation Platform
- Evaluation Platform (planned)
- Research Runtime (planned)
- Agent Runtime (planned)
- MCP Integrations (planned)

An architecture audit performed in July 2026 revealed that the platform
is no longer evolving toward a simple chatbot or RAG application.

Instead, the current architecture aligns more closely with a reusable
AI Research Platform capable of supporting:

- RAG applications
- Deep Research workflows
- Agentic systems
- Benchmarking and experimentation
- Model routing
- Multi-provider orchestration
- Future MCP integrations

This ADR formalizes that understanding and freezes the long-term roadmap.

---

# Decision

ResearchMind will be developed as a modular AI Research Platform.

The platform is composed of several independent but connected layers.

---

# Platform Architecture

```text
Knowledge Platform
        ↓
Context Platform
        ↓
Generation Platform
        ↓
Evaluation Platform
        ↓
Research Runtime
        ↓
Agent Runtime
        ↓
MCP Integrations
```

---

# Long-Term Vision

ResearchMind should become:

- Provider independent
- Framework friendly
- Experiment driven
- Evaluation first
- Agent ready
- Production oriented

The platform should support both:

- experimentation environments
- production workloads

without architectural rewrites.

---

# Platform Layers

---

# Phase 1

# Knowledge Platform

Status:

✅ Mature

Purpose:

Document understanding and retrieval.

Responsibilities:

- Upload
- Processing
- Chunking
- Embeddings
- Indexing
- Retrieval
- Reranking
- Compression
- Citations
- Context Assembly

Architecture:

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

Retrieval
↓

Compression
↓

Context
```

Current maturity:

4 / 5

---

# Phase 2

# Context Platform

Status:

✅ Functional

Purpose:

Convert retrieved information into generation-ready context.

Responsibilities:

- Context assembly
- Deduplication
- Parent expansion
- Adjacent merge
- Compression
- Citations
- Guardrails
- Formatting

Output:

```python
PromptContext
```

Current maturity:

3.5 / 5

---

# Phase 3

# Generation Platform

Status:

✅ Complete, per `generation_platform_complexion_prd.md` — structured
output, output validation, regeneration, and prompt-template
integration are complete (see
`docs/architecture/structured-output-platform.md`). Routing (see
`docs/architecture/model-routing-platform.md`,
ADR-026), Caching (see `docs/architecture/runtime-caching-platform.md`,
ADR-027), Streaming (see `docs/architecture/streaming-platform.md`,
ADR-028), Runtime Metrics Integration, and Artifacts (see
`artifacts_platform_prd.md`) are now all complete, along with all five
per-runtime Validation Contracts (Research/Planner/Reviewer/Agent/MCP)
and the Acceptance/Fail-Fast/Runtime Validation policy layer. Only a
`/research` API remains, blocked on a Research Runtime that doesn't
exist yet. Generation-level guardrails are covered separately by the
standalone Guardrails Platform (below), which is complete as an MVP
foundation and wired directly into this service (per
`guardrail_integration_prd.md`).

Purpose:

Provider-independent LLM execution platform.

Responsibilities:

- ✅ Provider abstraction — OpenAI, Claude, Gemini, Groq, Ollama, each
  behind `GenerationProviderInterface`
- 🟡 Prompt management — `generation/prompts/` (template loading,
  rendering, few-shot, versioning) is substantial and pre-existing;
  `GenerationService.generate_from_template()` now bridges it into
  Generation with schema-aware format instructions
  (`PydanticOutputParser.get_format_instructions()`)
- ✅ Validation — `generation/validation/` implements input validation
  (empty prompt, token budget, provider limits, context quality), output
  validation (JSON, schema via `jsonschema`, formatting, completeness,
  consistency, response size, fabricated-citation detection — full PRD
  pipeline), a lightweight no-LLM hallucination/groundedness validator,
  five per-runtime Contracts (Research/Planner/Reviewer/Agent/MCP), a
  `ValidationRegistry`, weighted scoring, a multi-stage
  `ValidationReport`, and an Acceptance/Fail-Fast/Runtime Validation
  policy layer (`generation/policies/`) — see `validation_platform_prd.md`,
  `generation_platform_complexion_prd.md`
- ✅ Guardrails — a new standalone, platform-wide Guardrails Platform
  (`apps/api/app/ai/guardrails/`, Milestone 11.16 per
  `guardrails_platform_prd.md`) now exists outside this phase's own
  scope, spanning input/retrieval/generation/runtime stages (distinct
  from the Context Platform's retrieval-time-only guardrails above);
  complete as an MVP foundation and wired directly into
  `GenerationService` (input gate + full report on
  `GenerationResult.guardrails`) per `guardrail_integration_prd.md`
- ✅ Structured outputs — native provider structured decoding for all
  five providers (OpenAI `text.format`, Gemini `response_json_schema`,
  Claude `output_config.format`, Groq `response_format.json_schema`,
  Ollama schema-constrained `format`), a parser/repair fallback, the
  Markdown/XML parser registry connected end-to-end, an optional
  LangChain `with_structured_output()` path (`generation/langchain/`,
  4 of 5 providers — `langchain-groq` is incompatible with the pinned
  `groq` SDK version), and a regenerate-on-invalid-output loop with
  corrective feedback (`GenerationRequest.max_regeneration_attempts`)
- ✅ Routing — `ProviderCapabilities` flags, `supports_*` accessors, and
  a capability-mismatch guard pre-date this phase; a full Routing
  Platform now sits on top: a scored `ModelCatalogRegistry`, a
  15-value task-based `RoutingStrategy`, capability/policy filtering,
  a weighted scoring engine with explainable reasons, and a
  distinct-provider-preferred fallback chain (`generation/routing/`,
  `generation/catalog/`); `GenerationService.generate()` routes
  automatically (with fallback retry) when no `provider` is given —
  see `routing_platform_prd.md`, ADR-026
- ✅ Streaming — per-provider `stream()` implementations, plus a full
  Streaming Platform (canonical event protocol, SSE/WebSocket
  transports) wired into `POST /api/v1/chat/stream` / `/api/v1/chat/ws`, with owner-scoped history/replay at `GET /api/v1/chat/conversations` and `GET /api/v1/chat/conversations/{id}`
  — see `docs/architecture/streaming-platform.md`, ADR-028
- ✅ Caching — Runtime Caching Platform (`generation/caching/`): L1
  exact/L2 semantic/L3 session, policy resolution, wired into
  `GenerationService` — see `docs/architecture/runtime-caching-platform.md`,
  ADR-027
- ✅ Observability — Runtime Metrics Integration (`generation/observability/`):
  `GenerationMetricsService` derives a `GenerationMetricsSnapshot`
  (request/execution/token/cost/validation/guardrail metrics) from every
  `GenerationResult`, forwards counters to a Prometheus-ready
  `MetricsRecorder` (`infrastructure/metrics/generation.py`), and logs a
  `generation.metrics.recorded` event; `generation.started/failed`,
  `validation.started/completed`, and `provider.started/completed`
  events round out the pipeline — per `generation_platform_complexion_prd.md`
- ✅ Artifacts — a new centralized Artifact Platform (`app/ai/artifacts/`,
  distinct from this directory's own now-deleted empty `artifacts/`
  scaffold) persists a canonical `GenerationArtifact` — including a
  `metrics.json` snapshot — on every `generate()` call, policy-gated and
  immutable — see `artifacts_platform_prd.md`

Providers:

- OpenAI
- Claude
- Gemini
- Groq
- Ollama

Architecture:

```text
Prompt (PromptService, optional — generate_from_template)
↓

Input Validation (empty prompt, token budget, provider limits, context quality)
↓

Routing (task-based strategy → scored model catalog → provider + fallback chain)
↓

Generation (native structured output → parser fallback → regeneration)
↓

Validation (input + output + hallucination + runtime stages, registry, scoring, ValidationReport)
↓

Validation Policy Layer (Acceptance / Fail-Fast / Runtime Validation decisions)
↓

Metrics (GenerationMetricsService — request/execution/token/cost/validation/guardrail)
↓

Artifacts (GenerationArtifact incl. metrics.json, persisted, policy-gated, immutable)
```

Current maturity:

100% (Generation Platform scope) — only a future `/research` API remains, tracked separately under Phase 3.9

---

# Phase 4

# Evaluation Platform

Status:

⏳ Planned

Purpose:

Measure and improve AI quality.

Responsibilities:

- Retrieval evaluation
- Groundedness
- Faithfulness
- Regression testing
- Benchmark datasets
- Prompt evaluations
- Model evaluations
- Quality scoring

Architecture:

```text
Question
↓

Retrieval
↓

Generation
↓

Evaluation
↓

Metrics
```

Principle:

Evaluation should precede agent development.

Current maturity:

0%

---

# Phase 5

# Research Runtime

Status:

⏳ Planned

Purpose:

Deep Research workflows.

Responsibilities:

- Planning
- Query decomposition
- Parallel retrieval
- Evidence collection
- Evidence synthesis
- Report generation

Architecture:

```text
Question
↓

Planner
↓

Decomposition
↓

Parallel Retrieval
↓

Evidence Merge
↓

Generation
```

Framework:

LangGraph

Current maturity:

0%

---

# Phase 6

# Agent Runtime

Status:

⏳ Planned

Purpose:

Multi-step autonomous workflows.

Responsibilities:

- Tool calling
- Multi-agent systems
- Workflow execution
- Reflection
- Planning
- Memory
- Human approval

Architecture:

```text
Agent
↓

Tools
↓

Research Runtime
↓

Generation
```

Framework:

LangGraph

Current maturity:

0%

---

# Phase 7

# MCP Integrations

Status:

⏳ Planned

Purpose:

External tool interoperability.

Responsibilities:

- MCP Servers
- MCP Clients
- External tool access
- IDE integrations
- Research tools
- Third-party workflows

Examples:

- GitHub
- Figma
- Browser
- Search
- Internal tools

Current maturity:

0%

---

# Architectural Principles

---

# 1. Platform First

ResearchMind is not a single application.

ResearchMind is a reusable platform.

---

# 2. Provider Independence

Providers should remain implementation details.

Core platform models remain canonical.

---

# 3. Framework Friendly

ResearchMind owns architecture.

External frameworks are leveraged heavily when useful.

Examples:

- LangChain
- LangGraph
- LangSmith

Frameworks should not dictate platform architecture.

---

# 4. Evaluation First

Agent systems should only be introduced after:

- retrieval evaluation
- generation evaluation
- regression testing

exist.

---

# 5. Production Oriented

All major components should support:

- observability
- cost tracking
- testing
- artifacts
- benchmarking

from the beginning.

---

# Current Priorities

P0

```text
Knowledge
↓

Context
↓

Generation
```

End-to-end integration.

---

P1

~~Generation Platform completion.~~ ✅ Complete, per `generation_platform_complexion_prd.md`.

---

P2

Evaluation Platform.

---

P3

Research Runtime.

---

P4

Agent Runtime.

---

P5

MCP Integrations.

---

# End State

```text
Knowledge Platform
        ↓
Context Platform
        ↓
Generation Platform
        ↓
Evaluation Platform
        ↓
Research Runtime
        ↓
Agent Runtime
        ↓
MCP Ecosystem
```

ResearchMind should eventually support:

- RAG applications
- Deep Research systems
- Autonomous agents
- AI experimentation
- Benchmarking
- Enterprise knowledge systems

without requiring architectural redesign.

---

# Consequences

Positive:

- Clear long-term direction
- Reduced architectural drift
- Better prioritization
- Easier onboarding
- Stronger portfolio narrative

Negative:

- Larger scope
- Increased maintenance burden
- Longer implementation timeline

---

# Final Statement

ResearchMind is officially considered an:

# AI Research Platform

rather than solely a:

# RAG Application.
