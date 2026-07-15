# ResearchMind AI — AI Engineering Architecture Audit

**Date:** 2026-07-15
**Scope:** `apps/api/app/ai/` (Knowledge Platform + Generation Platform), plus the app-wide infrastructure that supports it (observability, error handling, testing, API wiring).
**Purpose:** Establish an honest, evidence-based baseline of where the platform stands against current AI-engineering practice, and enumerate what's missing so future work can be planned deliberately. This report does not recommend rewriting anything already built — the gaps below are framed as **additions**, not corrections, per the constraint that existing implementations stay as-is.

---

## 1. Executive Summary

ResearchMind AI is built as two parallel platforms under `apps/api/app/ai/`:

- **Knowledge Platform** (`app/ai/knowledge/`, ~14.6k LOC) — document upload, parsing, chunking, embedding, hybrid retrieval, reranking, context assembly, citations, and guardrails. This is the most mature part of the codebase: real providers, real registries, real Qdrant/Valkey integration, real test coverage.
- **Generation Platform** (`app/ai/runtime/generation/`) — five real LLM provider adapters (Groq, OpenAI, Claude, Gemini, Ollama) behind a thin registry/service, surrounded by roughly 75 empty stub files representing an intended architecture (guardrails, caching, routing, streaming, validation, structured output, observability, prompts) that was scaffolded but never implemented.

**The single biggest finding is structural, not a missing feature:** neither platform is reachable from the API today. `app/api/v1/chat.py` is a 0-byte file. `create_generation_service()` is defined and never called from anywhere outside its own module. The Knowledge Platform's `ContextBuilderService` — which is where citations and guardrails actually execute — is also never invoked by any router; the only live endpoint (`retrieval.py`) returns raw chunks and bypasses context assembly entirely. **There is currently no end-to-end path from "user asks a question" to "cited, guarded, LLM-generated answer."** Both halves are real, tested (unevenly), and individually reasonable — but they are islands.

Beyond that, the platform is missing essentially all of the "day 2" AI-engineering infrastructure that separates a working prototype from a production LLM system: no cost tracking (despite pricing data existing in the model catalog), no token-budget enforcement, no LLM response caching, no tracing/APM, no metrics, no evaluation harness, no retry/circuit-breaker resilience around provider calls, and no agentic-flow capability (LangGraph isn't even installed despite being part of the stated project vision).

None of this is a criticism of engineering quality — the code that *does* exist (hybrid retrieval with RRF fusion, embedding cache with fail-open semantics, the provider adapters this session hardened with logging and error handling) is well-structured, type-safe, and consistent. The gap is entirely one of **breadth of completion**, not depth of what's been built.

---

## 2. Maturity Scorecard

Scale: **0** = nonexistent · **1** = stub/placeholder only · **2** = minimal/partial · **3** = functional but incomplete · **4** = solid, production-leaning · **5** = production-grade with headroom for scale

| Dimension | Score | One-line verdict |
|---|:-:|---|
| RAG / retrieval pipeline | **4/5** | Real hybrid (dense+sparse+RRF) search, reranking, context compression — genuinely strong |
| Data modeling & type safety | **4.5/5** | Consistent Pydantic `extra="forbid"` + `StrEnum` discipline throughout |
| Generation provider layer | **3/5** | 5 real adapters, now with logging/error-wrapping; no retries, no streaming, no tools |
| **End-to-end wiring (API reachability)** | **1/5** | Neither generation nor context-assembly is reachable from any route |
| Caching — embeddings | **4/5** | Real Valkey-backed cache, fail-open, TTL, null-object pattern |
| Caching — generation/semantic | **0/5** | `cache_hit` field exists, never set `True`; no semantic cache |
| Observability — structured logging | **3/5** | Real structlog + request-id propagation; one confirmed bug (prod JSON renderer never actually runs) |
| Observability — tracing/APM/metrics | **0.5/5** | No OpenTelemetry/Sentry/Prometheus; a `NoOpMetricsRecorder` exists but is itself unwired |
| Cost tracking & token optimization | **0.5/5** | Pricing catalog exists; never multiplied against token counts; `tiktoken` installed, zero usage |
| Guardrails | **2/5** | Real regex-based prompt-injection/jailbreak detector, but chunk-level only, one strategy, orphaned from the API |
| Input/output validation | **1.5/5** | Only empty-string checks; no token-budget, hallucination, schema, or citation validation |
| Error handling / resilience | **2/5** | Domain exceptions bypass the app's structured HTTP error handler; no retry/backoff library anywhere |
| Evaluation & QA | **0/5** | `app/ai/quality/` (benchmarks, evaluation, experiments, regression, telemetry, tracing) is empty `__init__.py` files only |
| Testing | **2.5/5** (skewed) | 52 real test files for Knowledge Platform; **0** for `runtime/generation`; 0 for auth; eval/security/perf test files exist as 0-byte stubs |
| Agentic-flow readiness (LangGraph/MCP/tools/streaming/memory) | **0/5** | LangGraph not installed; zero tool-calling, orchestration, memory, or streaming code anywhere |

**Composite: ~2.1/5 — early-stage / prototype-to-production transition.** The RAG core is ahead of where most teams are at this stage; the operational scaffolding around it (cost, eval, observability, resilience) and the connective tissue between subsystems are behind.

---

## 3. Architecture — What Actually Exists Today

```
                    ┌─────────────────────────────────────────┐
                    │         app/api/v1/  (FastAPI)           │
                    │  health ✅  auth ✅  documents ✅         │
                    │  retrieval ✅ (dense/sparse/hybrid only)  │
                    │  chat ❌ (0 bytes)  evaluation ❌ (0 bytes)│
                    └───────────────┬───────────────────────────┘
                                    │  retrieval.py calls RetrievalService
                                    │  directly — bypasses everything below
                                    ▼
     ┌──────────────────────────────────────────────────────────────┐
     │  Knowledge Platform  (app/ai/knowledge/)  — ~14.6k LOC, real  │
     │                                                                │
     │  upload → processing/docling → chunking (3 strategies) →      │
     │  embeddings (3 providers + Valkey cache) → indexing (Qdrant)  │
     │  → retrieval (dense+sparse+RRF+rerank) → ContextBuilderService │
     │       (dedup → expand → merge → compress → GUARDRAILS →       │
     │        CITATIONS → format) → PromptContext                    │
     │                                                                │
     │  ⚠ ContextBuilderService.build() is never called by any       │
     │    router — citations & guardrails never execute in prod      │
     └───────────────────────────┬────────────────────────────────────┘
                                  │  PromptContext is the designed hand-off
                                  │  point — but nothing constructs it live
                                  ▼
     ┌──────────────────────────────────────────────────────────────┐
     │  Generation Platform  (app/ai/runtime/generation/)            │
     │                                                                │
     │  create.py → GenerationRegistry → GenerationService.generate()│
     │  → 5 real provider adapters (groq/openai/claude/gemini/ollama)│
     │                                                                │
     │  ⚠ create_generation_service() is never called from app/api/  │
     │  ⚠ ~75 files are 0-byte stubs: guardrails/ caching/ routing/  │
     │    streaming/ validation/ structured_output/ observability/   │
     │    prompts/ artifacts/ langchain/                              │
     └──────────────────────────────────────────────────────────────┘
```

Both platforms individually reflect a coherent design (composition-root factory functions, registry/provider patterns, interface segregation via ABCs) — this is a deliberate, well-thought-out architecture. The problem is entirely that **construction stopped before the seams were connected.**

---

## 4. Detailed Findings by Category

### 4.1 RAG Pipeline — strong, with real gaps

**What's real:** S3-backed upload with dedup/rollback (`upload/service.py`); Docling-based parsing; three chunking strategies (fixed, recursive, markdown-header-aware); three embedding providers (OpenAI, Voyage, local sentence-transformers) behind a shared batcher; a real Valkey-backed embedding cache with fail-open semantics; hybrid retrieval running dense and sparse search in parallel and fusing with genuine Reciprocal Rank Fusion (`retrieval/fusion/rrf.py`, `1/(k+rank)`, k=60); two independent reranking providers (Voyage API, local cross-encoder); and a multi-stage context assembly pipeline (dedup → parent-chunk expansion → adjacent-chunk merge → embedding-similarity compression → token-budget compression → guardrails → citations → format).

**What's missing:**
- **No semantic (embedding-similarity) chunking** — only fixed/recursive/markdown-structural strategies exist.
- **Query-level prompt-injection detection is explicitly deferred** (`retrieval/service.py` docstring marks it "Future") — the only injection detection that runs is post-retrieval, at the chunk level.
- **Guardrail strategy is hardcoded** to `RULE_BASED` in `ContextBuilderService.build()` — `GuardrailStrategy.LLAMA_GUARD`, `.NEMO`, `.LAKERA` exist as enum values with no provider classes behind them; selecting them would raise `GuardrailProviderNotFound`.
- **`vectorstores/artifacts/{builder,models,writer}.py` are empty** — an abandoned artifact-tracking stub inconsistent with the artifact pattern used everywhere else in the platform.
- **The entire pipeline is orchestration-dead at the API layer** (see §3) — it's unit-tested in isolation but never exercised end-to-end via HTTP.

### 4.2 Generation Platform — functional core, no operational shell

The five provider adapters (`providers/{groq,openai,claude,gemini,ollama}.py`) are real, now instrumented this session with structured logging (`generation.<provider>.started/completed/failed`) and SDK-error wrapping into `GenerationExecutionError`. Two silent correctness bugs were also fixed in that pass: Gemini and Ollama were never reading token usage from their responses.

Still missing, all as empty stub directories under `runtime/generation/`:
- **No prompt management** (`prompts/`) — prompts are inline string concatenation (`request.prompt_context.context + "\n\n" + request.user_prompt"`) in every provider, duplicated 5×, with no versioning, templating, or A/B capability.
- **No automatic routing** (`routing/`) — `RoutingStrategy` enum defines `MANUAL/CHEAPEST/FASTEST/QUALITY/PRIVACY/AUTO`, but every strategy file is empty; provider selection is 100% caller-specified today.
- **No structured output** (`structured_output/`) — no JSON-schema-constrained generation, no Pydantic-model-typed responses, despite `ResponseFormat.STRUCTURED` existing as an enum value.
- **No output validation** (`validation/output/`) — hallucination, citation, JSON, and schema validators are all empty; nothing checks a generation result before it's returned.
- **No token-budget enforcement** (`validation/input/token_budget.py`) — combined with `tiktoken` being installed but never imported anywhere in the app, there is no pre-flight way to know a prompt's token count before sending it to a provider.
- **Config fields with no effect:** `BaseGenerationConfig.timeout_seconds` and `.max_retries` are defined (`config.py:23-31`) but never read by any of the 5 providers' client constructors — `AsyncGroq(api_key=...)`, `AsyncOpenAI(api_key=...)`, `AsyncAnthropic(api_key=...)`, `genai.Client(api_key=...)`, and `AsyncClient(host=...)` all construct with only credentials, no timeout or retry policy.

### 4.3 Caching

Embedding-layer caching is genuinely good: Valkey-backed, TTL'd, JSON-encoded, fail-open on cache errors (treated as a miss rather than propagating), with a proper null-object fallback (`NullEmbeddingCache`) when disabled. A parallel cache exists for query-time embeddings.

**Nothing above that layer is cached.** `GenerationStatistics.cache_hit: bool = False` exists as a field and is never set `True` anywhere — there is no semantic cache, no exact-match response cache, and no use of Anthropic/OpenAI's native prompt-caching features (which would reduce both cost and latency for the repeated system-prompt + retrieved-context pattern this app already has). `runtime/generation/caching/` (interfaces, models, service, exact/semantic/session-cache providers) is entirely empty stubs.

### 4.4 Observability

**Logging** is the one area with a real foundation: `structlog` is configured centrally (`core/logging.py`), invoked at startup from the FastAPI lifespan, with request-id propagation via contextvars threaded through middleware (`middleware/request_logging.py`, `middleware/request_id.py`). This session's work extended that pattern correctly into the Generation Platform.

**One concrete bug found during this audit:** `configure_logging()`'s docstring claims production uses a JSON renderer, but the code path for `environment == "production"` only adds `structlog.processors.ExceptionRenderer()` — which reformats exception info, but is not a terminal serializer — and never calls `structlog.processors.JSONRenderer()`. If this is accurate in production today, structured logs may not actually be emitted as JSON, which would silently break any log-aggregation pipeline expecting JSON lines. **Worth verifying directly against the deployed config**, since this wasn't otherwise in scope to fix in this pass.

**Tracing/APM: absent.** No OpenTelemetry, Sentry, Datadog, LangSmith, or Langfuse integration anywhere, despite a `langsmith_api_key` setting existing in `core/settings.py` that is never read anywhere else in the codebase — a vestige of an intended integration that was never finished.

**Metrics: absent.** `runtime/generation/observability/` is fully empty. There's a separate, generic `MetricsRecorder` interface + `NoOpMetricsRecorder` under `app/infrastructure/metrics/` with a comment "Until Prometheus is added, use a no-op implementation" — but this abstraction itself is never instantiated or wired into anything, so it's dead scaffolding rather than an active system the generation code failed to use.

### 4.5 Cost & Token Optimization

The model catalog (`catalog/models.py`) carries real per-model pricing (`cost_per_input_1m`, `cost_per_output_1m`) sourced from provider pricing pages, and that data is threaded correctly into each provider's config object. **It is never used** — no code anywhere multiplies token counts against these rates, so `GenerationStatistics.estimated_cost_usd` stays `0` forever. There is consequently no per-request cost visibility, no per-user/per-tenant cost aggregation, and no budget alerting possible today.

Token optimization is similarly absent: no pre-flight token counting (`tiktoken` is installed, unused), no prompt compression beyond what already exists in the Knowledge Platform's context-compression stage (which caps retrieved *context*, not the full prompt+system-instructions+context total sent to a provider), and no dynamic model routing toward cheaper models for lower-stakes requests (the `RoutingStrategy.CHEAPEST` enum value exists with no implementation behind it).

### 4.6 Guardrails & Safety

Real but narrow: `context/guardrails/providers/rule_based.py` runs regex pattern matching for **prompt-injection and jailbreak phrases only** (patterns like `ignore.*instructions`, `system prompt`, `reveal.*prompt`, `jailbreak`) against retrieved chunks, assigning each a `ChunkRiskLevel` (SAFE/SUSPICIOUS/MALICIOUS). It does **not** cover PII detection, toxicity/harassment content, or output-side guardrails (checking what the *model generates*, as opposed to what it *retrieves*). As noted in §4.1, it's also orphaned from the live API today.

The `RoutingStrategy`-style placeholder pattern repeats here too: `GuardrailStrategy.LLAMA_GUARD/NEMO/LAKERA` exist as enum options with zero provider implementations, meaning any config that requested them would fail at runtime.

### 4.7 Validation & Error Handling

`GenerationService._validate()` checks exactly two things: non-empty user prompt, non-empty context string. There is no schema validation of provider responses beyond what this session added (usage-field null-guards), no hallucination detection, no citation-accuracy validation, and no structured-output/JSON-schema validation.

More structurally: **`GenerationError` and `EmbeddingError` (and all their subclasses) inherit from plain `Exception`, not the app's `AppException` base** (`exceptions/base.py`). The app has a real, working exception-handling architecture — `AppException` carries `status_code`/`code`/`details`, and `register_exception_handlers()` (wired at startup via `core/setup.py`) maps it to proper structured JSON error responses. Because the AI-domain exceptions don't participate in that hierarchy, any `GenerationProviderNotFoundError`, `GenerationValidationError`, `GenerationExecutionError`, etc. that reaches a route today falls through to the generic catch-all `Exception` handler and returns an opaque 500 with no domain-specific status code or error code — even though the app already has the machinery to do this properly. This is the kind of gap that's cheap to close later (subclass `AppException` instead of `Exception`) without touching any of the logic that raises these exceptions today.

**Resilience:** no retry/backoff library (`tenacity`, `backoff`, `stamina`) is used anywhere. The only retry behavior in the entire AI stack is SDK-native `max_retries` passed at client-construction time for two of the three *embedding* providers (Voyage, OpenAI) — not for any of the five generation providers, and not for Qdrant or S3 calls. There are no circuit breakers anywhere.

### 4.8 Evaluation & Quality Assurance

This is the starkest gap in the report. `app/ai/quality/` exists with five subpackages — `benchmarks/`, `evaluation/`, `experiments/`, `regression/`, `telemetry/`, `tracing/` — and **every single one contains only an empty `__init__.py`**. There is no golden dataset, no LLM-as-judge scoring, no RAGAS/DeepEval/promptfoo-style automated evaluation, no prompt-regression testing, and no A/B testing infrastructure for comparing models or prompt variants. `routing/strategies/quality.py` (which would presumably feed quality-based routing decisions) is likewise empty.

This gap is echoed in the test suite: `tests/evaluation/{test_faithfulness,test_groundedness,test_reranking,test_retrieval_precision}.py` and `tests/security/{test_jailbreaks,test_prompt_injection}.py` all exist as 0-byte files — someone scaffolded exactly the right test surface for these concerns and then didn't fill it in.

### 4.9 Testing

Coverage is real but extremely skewed: 52 substantive test files under `tests/unit/ai/knowledge/` and `tests/integration/ai/knowledge/` (some genuinely thorough — e.g. a 508-line test for the processing service, a 401-line test for retrieval). By contrast, **`app/ai/runtime/generation/` — the entire Generation Platform — has zero test files**, and neither does the auth module. Only two of the four live routers (`health`, `retrieval`) have any test coverage; `documents.py` and `auth.py` do not. CI (`.github/workflows/ci.yml`) runs ruff format/lint, mypy, and pytest with coverage reporting — but coverage isn't gated on a threshold, so this skew doesn't currently block merges.

### 4.10 Agentic-Flow Readiness

Given the project's stated vision is "RAG + LangGraph + MCP," this is worth calling out explicitly as its own category rather than folding into "future work" generically:

- **LangGraph is not installed** — `langgraph`, `langgraph-checkpoint`, `langgraph-prebuilt`, `langgraph-sdk` appear nowhere in `pyproject.toml`, despite being part of the stated architecture.
- Of the LangChain packages that *are* installed (`langchain`, `langchain-core`, `langchain-anthropic`, `langchain-openai`, `langchain-google-genai`), only `langchain_text_splitters` is actually imported anywhere, and only for two chunking providers. The rest are installed with zero usage.
- **No tool/function-calling infrastructure** — none of the five provider adapters pass `tools=`/`tool_choice=`/`functions=` to their SDK calls. The only artifact is a `ProviderCapabilities.tool_calling: bool` metadata flag that nothing consumes.
- **No agent/planner/orchestrator classes exist anywhere** in the codebase (confirmed via repo-wide search for the pattern). `structured_output/schemas/{agent,planner}.py` and `routing/strategies/auto.py` are all empty.
- **No MCP implementation** — every reference to MCP in the repo is in planning documents (`ROADMAP.md` lists it as Phase 6, "Planned"; `phase-3-ai-runtime-roadmap.md` marks it "Not Started"). No MCP server or client code exists.
- **No conversation memory or multi-turn state** — no session/checkpoint classes, no `conversation_history` handling anywhere. Every generation request is single-shot and stateless by construction.
- **No streaming** — `streaming/` is four empty files; `BaseGenerationConfig.enable_streaming: bool = True` is dead config since no provider ever passes `stream=True`, and no route uses `StreamingResponse`, SSE, or WebSockets.

**In short: the agentic half of the stated vision is 0% started.** This isn't a criticism — RAG-first is a reasonable sequencing choice — but it means "agentic flows" is genuinely a from-scratch build, not an extension of existing partial work.

---

## 5. Gap Inventory (Prioritized)

These are additions to plan for, not corrections to existing code. Ordered by what unlocks the most value first.

### P0 — Nothing works end-to-end without these
1. **Wire the Generation Platform into the API.** Add a `chat.py` router, a `get_generation_service()` dependency (mirroring the existing `app/dependencies/` pattern), and call `create_generation_service()` from it. Currently zero HTTP paths reach any LLM.
2. **Wire `ContextBuilderService` into whatever consumes retrieval results**, so citations and guardrails actually execute before context reaches generation. Currently `retrieval.py` bypasses this pipeline entirely.
3. **Connect the two platforms**: the designed hand-off point (`PromptContext` → `GenerationRequest.prompt_context`) exists in the type system already — it just needs a caller that builds context, then generates, then returns a cited answer.

### P1 — Needed before this is safe/affordable to run for real users
4. **Cost tracking**: multiply `cost_per_input_1m`/`cost_per_output_1m` (already in the catalog) against actual token counts (already returned by every provider) to populate `estimated_cost_usd`. This is almost entirely arithmetic on data that already exists.
5. **Make AI-domain exceptions inherit `AppException`** instead of plain `Exception`, so `GenerationError`/`EmbeddingError` subclasses get proper HTTP status codes instead of opaque 500s — the handler infrastructure to support this already exists and works.
6. **Retry/timeout policy for provider calls** — wire the already-defined-but-unused `BaseGenerationConfig.timeout_seconds`/`max_retries` fields into each provider's client constructor, and/or adopt `tenacity` for backoff around transient provider failures (rate limits, timeouts).
7. **Output validation** — at minimum, validate that generated citations actually correspond to chunk IDs present in the context (the data for this already exists via `Citation.chunk_ids`), before trusting the answer.
8. **Token-budget enforcement** — wire `tiktoken` (already a dependency) into a pre-flight check so oversized prompts fail fast with a clear error instead of hitting a provider's context-window limit.

### P2 — Needed to operate this with confidence at scale
9. **Tracing/APM** — pick one of OpenTelemetry, LangSmith, or Langfuse (the `langsmith_api_key` setting already exists, suggesting this was the original intent) and instrument the generation call path.
10. **Metrics** — either build out Prometheus behind the existing (currently unwired) `MetricsRecorder` interface, or replace it; either way, emit latency/cost/token histograms per provider/model.
11. **LLM response caching** — semantic or exact-match caching for repeated queries, and adoption of native provider prompt-caching (Anthropic/OpenAI) for the repeated system-prompt + retrieved-context pattern.
12. **Evaluation harness** — this is the largest single gap: golden Q&A datasets, retrieval-precision and faithfulness/groundedness scoring (test files already scaffolded, just empty), and a regression gate in CI before prompt or model changes ship.
13. **Test coverage for `runtime/generation` and `auth`** — currently zero for both.

### P3 — Roadmap items (agentic flows), from scratch
14. **Tool/function calling** — needed before any agentic capability is possible; the `ProviderCapabilities.tool_calling` flag is already there as a hook point.
15. **Streaming** — token-by-token SSE responses; `enable_streaming` config flag already exists as a hook point.
16. **LangGraph adoption** — install it, then build a real orchestration layer (multi-step retrieval-then-generate-then-verify flows, or agentic tool use) on top of the existing Knowledge/Generation platforms.
17. **MCP** — either an MCP server exposing this platform's retrieval/generation as tools, or an MCP client for consuming external tools, per the roadmap docs' Phase 6 plan.
18. **Conversation memory** — session/checkpoint state for multi-turn interactions, which LangGraph's checkpointer pattern would provide once adopted.
19. **Automatic routing strategies** — cost/latency/quality-based provider selection (`RoutingStrategy.AUTO/CHEAPEST/FASTEST/QUALITY`), which becomes valuable once cost tracking (P1 #4) and evaluation (P2 #12) exist to make routing decisions on.

---

## 6. What's Already Good (worth preserving as-is)

- The **composition-root pattern** (`create_*()` factory functions building registries from `settings`) is consistent across both platforms and makes dependency wiring explicit and testable.
- **Pydantic discipline** (`extra="forbid"`, `StrEnum`, frozen configs) is applied consistently — this alone prevents a large class of silent-data-corruption bugs common in fast-moving AI codebases.
- **Hybrid retrieval with real RRF fusion + reranking** is more sophisticated than what many production RAG systems ship with initially.
- **The embedding cache's fail-open design** (cache errors are logged and treated as misses, never propagated as failures) is exactly the right resilience posture for a cache — it should be the template for any future generation-response cache.
- **This session's structured-logging pattern** (`structlog.get_logger()`, dot-namespaced events, kwargs-not-f-strings) is consistent with the one real observability convention already established in `app/ai/knowledge/embeddings/` — future additions to the Generation Platform should keep following it.

---

## 7. Bottom Line

ResearchMind AI has a genuinely strong RAG core and a clean, if incomplete, generation layer — but as of today it is two well-built subsystems that don't talk to each other in production, wrapped in an architecture that anticipated (via its empty scaffolding) most of the operational concerns — cost, caching, observability, evaluation, guardrails, agentic flows — that it hasn't yet implemented. The scaffolding itself is a good sign: someone thought through the target shape of this system before building it. The work ahead is filling that shape in, starting with the P0 wiring gap, since nothing else on this list matters to a real user until a question can actually reach an LLM and come back with an answer.
