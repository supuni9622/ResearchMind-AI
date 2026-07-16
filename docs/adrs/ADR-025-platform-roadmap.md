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

🚧 In Progress — structured output, output validation, regeneration, and
prompt-template integration are now substantially complete (see
`docs/architecture/structured-output-platform.md`, ~99% complete in its
own scope). Routing, caching, generation-level guardrails, and artifacts
remain unbuilt.

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
- 🟡 Validation — `generation/validation/` implements input validation
  (empty prompt, token budget, provider limits, context quality), output
  validation (schema via `jsonschema`, JSON parseability, fabricated-
  citation detection), a lightweight no-LLM hallucination/groundedness
  validator, a `ValidationRegistry`, weighted scoring, and a multi-stage
  `ValidationReport`; per-runtime Contracts/Runtime Validators and a few
  output checks (completeness/consistency/formatting/response-size)
  remain (`validation_platform_prd.md`)
- ❌ Guardrails — not addressed this phase (distinct from the Context
  Platform's retrieval-time guardrails)
- ✅ Structured outputs — native provider structured decoding for all
  five providers (OpenAI `text.format`, Gemini `response_json_schema`,
  Claude `output_config.format`, Groq `response_format.json_schema`,
  Ollama schema-constrained `format`), a parser/repair fallback, the
  Markdown/XML parser registry connected end-to-end, an optional
  LangChain `with_structured_output()` path (`generation/langchain/`,
  4 of 5 providers — `langchain-groq` is incompatible with the pinned
  `groq` SDK version), and a regenerate-on-invalid-output loop with
  corrective feedback (`GenerationRequest.max_regeneration_attempts`)
- 🟡 Routing — `ProviderCapabilities` flags and `supports_*` accessors
  pre-date this phase; a capability-mismatch guard now makes silent
  degradation observable, but there is still no capability-based
  provider selection engine (`generation/routing/` is empty stubs)
- ✅ Streaming — per-provider `stream()` implementations
- ❌ Caching — `generation/caching/` scaffolding exists, not wired
- 🟡 Observability — structured logging throughout; `cost_tracker` /
  `latency_tracker` / `token_counter` pre-exist, not newly verified
- ❌ Artifacts — not addressed this phase

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

Routing (capability guard only — no provider-selection engine)
↓

Generation (native structured output → parser fallback → regeneration)
↓

Validation (input + output + hallucination stages, registry, scoring, ValidationReport)
↓

Artifacts (not built)
```

Current maturity:

~65%

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

Generation Platform completion.

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
