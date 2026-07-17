ResearchMind Roadmap (Frozen)
✅ Phase 2.1 — Upload Platform (Complete)
Authentication

↓

Validation

↓

Storage (S3)

↓

Database

↓

Upload API

↓

Frontend

Status: DONE

🟨 Phase 2.2 — Document Intelligence Platform
✅ 2.2.1 Processing Foundation
Processing models
Interfaces
Registry
Parser abstraction
Enums
Exceptions

Status: COMPLETE

✅ 2.2.2 Docling Integration
Docling parser
Canonical ProcessedDocument
OCR disabled for MVP
Parser registry

Status: COMPLETE

✅ 2.2.3 Processing Orchestration
ProcessingService

↓

Resolve Parser

↓

Parse

↓

Return ProcessedDocument

Status: COMPLETE

✅ 2.2.4 Processing Artifacts
ProcessedDocument

↓

ArtifactBuilder

↓

ArtifactWriter

↓

S3

Artifacts:

original.pdf
parsed.md
parsed.txt
processed_document.json

Status: COMPLETE

✅ 2.2.5 Processing Lifecycle
Upload

↓

DocumentProcessingService

↓

Download Original

↓

Process

↓

Write Artifacts

↓

Update Status

Verified:

✅ S3
✅ PostgreSQL
✅ Status transitions
✅ Temporary file cleanup
✅ Frontend upload
✅ End-to-end synchronous flow

Status: COMPLETE

🟨 Processing Quality Pass (Next)

This is now our immediate focus before introducing queues.

2.2.6 Parser Intelligence
Metadata
Improve document metadata
Preserve Docling metadata
Replace temp path with canonical source
Statistics

Replace placeholders with real values:

Page count
Heading count
Paragraph count
Tables
Figures
Lists
References
Duplicate Detection

Current:

Upload

↓

Hash

↓

Ignored

Target:

Upload

↓

Hash

↓

Repository.exists_by_checksum()

↓

Duplicate?

↓

Skip Processing
Language Detection

Detect:

English

German

French

...

Store on ProcessedDocument.

Parser Tests

Verify:

PDF
DOCX
Markdown
TXT

Verify:

statistics
metadata
artifacts
🚫 Deferred (Not MVP)

These remain intentionally postponed.

OCR

Decision:

Digital research papers only.

OCR will be introduced only when scanned PDFs become a requirement.

Citation Mapping

Requires semantic parsing.

Move to Phase 2.3.

Page Mapping

Will naturally fit with chunk generation.

Move to Phase 2.3.

Quality Score

Needs richer document analysis.

Move until after chunking.

✅ Phase 2.3 — Chunking Platform (Complete)

Markdown

↓

Semantic Blocks

↓

Chunk Builder

↓

Chunk Metadata

↓

Chunk Persistence

Implemented strategies: Fixed, Recursive, Markdown. Benchmarked via
`benchmarks/chunking/`. Semantic/Parent-child/Agentic chunking deferred.

Status: COMPLETE

✅ Phase 2.4 — Embedding Platform (Complete)
Chunks

↓

Embedding Models

↓

Batch Embedding

↓

Qdrant

Providers: Sentence Transformers, Voyage AI, OpenAI. Valkey-backed
embedding cache with TTL. Benchmarked via `benchmarks/embeddings/`.

Status: COMPLETE

✅ Phase 2.5 — Retrieval Platform (Complete)
Hybrid Search ✅

↓

Metadata Filters ✅

↓

Reranking ✅ (Voyage AI + CrossEncoder)

↓

Parallel Retrieval ✅ (dense + sparse via `asyncio.gather`)

Implemented: query validation/normalization, dense (Voyage AI) search,
sparse (SPLADE) search, hybrid search via Reciprocal Rank Fusion,
query embedding cache (Valkey), metadata filtering (`document_id`,
`filename`, `owner_id`, `language`, server-enforced `owner_id`),
Voyage AI + CrossEncoder reranking, parallel dense+sparse execution,
retrieval evaluation (Recall@K, Precision@K, MRR, NDCG@K, latency,
cost — `benchmarks/retrieval/`, `benchmarks/reranking/`, ADR-020).

Reclassified: Parent/Child retrieval moved out of this platform into
the Context Platform below (2.6), since persisted chunk artifacts —
not the vector index — are the source of truth for parent resolution.
Query Decomposition moved to the future Research Runtime.

APIs: `POST /retrieve`, `POST /retrieve/sparse`, `POST /retrieve/hybrid`.

Status: COMPLETE

✅ Phase 2.6 — Context Platform (Complete — Phase 3.7, `context_platform_complexion_prd.md`)
Parent Expansion ✅

↓

Adjacent Merge ✅

↓

Compression (Token Budget + Embedding + LangChain + LLM, V1-V4) ✅

↓

Guardrails V1 ✅

↓

Citation Platform ✅

↓

Prompt Formatter ✅

Implemented: `ChunkArtifactReader`, `ParentExpansionService`,
`AdjacentMergeService`, Token Budget + Embedding + LangChain
(`ContextualCompressionRetriever` + `LLMChainExtractor`) + LLM
(per-chunk `GenerationService.generate()` summarization) Compression
providers, `RuleBasedGuardrailProvider` with risk scoring, citation IDs/pages/
headings/chunk IDs, and strategy-based prompt formatting (`DEFAULT`,
`NOTEBOOKLM`, `PERPLEXITY`, `RESEARCH`, `AGENT`). The LangChain compression
provider (V3) is now wired into `ContextBuilderService.build()`'s default
pipeline, gated by `settings.enable_langchain_compression` and gated on a
`query` being passed; the LLM provider (V4) is implemented and registered
but intentionally not part of the default pipeline.

Status: COMPLETE

🟨 Phase 2.7 — Generation Platform (~85% complete — structured output, validation, regeneration, prompt bridge, routing, caching, streaming, and artifacts done; per-runtime validators/contracts remain unwired, /research API remains)
Prompt Context

↓

Generation Service (native structured output → parser fallback → validation → regeneration)

↓

LLM Provider (Groq, OpenAI, Claude, Gemini, Ollama)

↓

Generated Answer

This replaces the earlier "RAG Engine" placeholder now that Retrieval
and Context are done. Provider Structured Output Integration is
complete for all five providers (native schema-constrained decoding,
parser/repair fallback, Markdown/XML registry), plus an optional
LangChain `with_structured_output()` path (OpenAI/Claude/Gemini/Ollama),
Output Validation (schema + citation, `generation/validation/`), a
regenerate-on-invalid-output loop (`max_regeneration_attempts`), a
provider-capability-mismatch guard, and `generate_from_template()`
bridging the existing Prompt Platform into Generation with schema-aware
format instructions. Detail: `docs/architecture/structured-output-platform.md`.

Also now complete: a Routing Platform (scored model catalog, task-based
strategies, capability/policy filtering, fallback chains —
`routing_platform_prd.md`, ADR-026), a Runtime Caching Platform (L1
exact/L2 semantic/L3 session, policy resolution —
`runtime_caching_platform_prd.md`, ADR-027), a Streaming Platform
(canonical event protocol, SSE/WebSocket, wired into `POST
/api/v1/chat/stream` / `/api/v1/chat/ws` — `streaming_platform_prd.md`,
ADR-028), and an Artifact Platform (canonical, immutable, policy-gated
`GenerationArtifact` persistence on every `generate()` call —
`artifacts_platform_prd.md`).

Not yet built: per-runtime Validation Contracts/Runtime Validators are
implemented but unreachable until a caller (e.g. a future `/research`
API) sets `GenerationRequest.runtime`, and a few PRD output-validation
checks (completeness/consistency/formatting/response-size). Hallucination
validation and generation-level guardrails are both complete elsewhere: a
`HallucinationValidator` ships as part of `generation/validation/`, and a
Guardrails Platform (`apps/api/app/ai/guardrails/`, see
`guardrails_platform_prd.md`) covers input/retrieval/generation/runtime
guardrails as an MVP foundation — wired directly into this service (see
`guardrail_integration_prd.md`): an input-stage gate runs before every
provider call, and the full guardrail report lands on
`GenerationResult.guardrails` before validation runs.

Status: IN PROGRESS (~85%)

⏳ Phase 2.8 — Queue & Workers

This stays exactly where we agreed.

BullMQ

↓

Workers

↓

Retry

↓

Dead Letter Queue

↓

Observability

Reason: We're making an already-correct synchronous workflow asynchronous, rather than debugging business logic inside background jobs.
