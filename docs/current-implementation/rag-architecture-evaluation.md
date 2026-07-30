# RAG Architecture Evaluation of the Current ResearchMind Implementation

**Code snapshot reviewed:** 2026-07-28  
**Evaluation basis:** The five reference architectures supplied for this evaluation: Naive RAG, Corrective RAG (CRAG), Adaptive RAG, GraphRAG, Agentic RAG, plus the proposed production hybrid.  
**Scope:** Architecture, components, control flow, and concepts. Framework and library differences are intentionally ignored.

## 1. Evaluation method

ResearchMind exposes three different user-facing paths, so it cannot be classified accurately as one RAG architecture:

| Product path | Current architectural role |
|---|---|
| Chat | Conversational generation with memory and optional web/paper tools. It intentionally does not retrieve uploaded documents and is therefore not a document RAG path. |
| Linear Research | Single-pass, document-grounded RAG using hybrid retrieval, reranking, context processing, citations, and generation. |
| Deep Research | Bounded planner-driven research workflow using multiple retrieval tasks, dependency waves, evidence aggregation, conditional web search, synthesis, review, repair loops, and human approvals. |

The following labels are used throughout:

| Rating | Meaning |
|---|---|
| **Strong alignment** | The core architectural concept is implemented and active in the runtime path. |
| **Partial alignment** | Important parts exist, but the reference architecture's defining control-flow contract is incomplete or limited to one product path. |
| **Conceptual overlap only** | A similarly named or adjacent component exists, but it does not perform the architectural role in the reference model. |
| **Not implemented** | The defining architectural component or retrieval plane is absent from active code. |

## 2. Executive assessment

| Reference architecture | Overall alignment | Where ResearchMind aligns | Main misalignment or gap |
|---|---|---|---|
| Naive RAG | **Strong alignment, substantially exceeded** | Documents are chunked, embedded, indexed, retrieved, placed into an LLM context, and used to generate an answer. | The active system is much more complex than fixed-size, dense-only top-k retrieval. It does not preserve Naive RAG's simplicity, latency, or low operational cost. |
| CRAG | **Partial alignment; strongest in Deep Research** | Deep Research evaluates whether private evidence is topically relevant and sufficient, then conditionally searches the web. It re-aggregates evidence before synthesis. | There is no canonical per-query or per-chunk `CORRECT / INCORRECT / AMBIGUOUS` relevance grader. Linear Research has no corrective fallback. |
| Adaptive RAG | **Partial alignment** | The platform has intentionally different Chat, Linear, and Deep paths; an escalation planner classifies research complexity; Deep Research can select document or web evidence. | No front-door query classifier automatically routes each query to direct LLM, vector RAG, web search, GraphRAG, or agentic execution. Product mode is primarily user-selected. |
| GraphRAG | **Not implemented** | Deep Research can answer multi-step questions by decomposing them into dependent text-retrieval tasks. | No entity extraction pipeline, knowledge graph, relationship edges, graph database, community summaries, graph traversal, or relationship-path retrieval exists. |
| Agentic RAG | **Partial-to-strong alignment in Deep Research only** | Deep Research plans tasks, executes dependency waves, evaluates evidence and drafts, performs bounded corrective retrieval/synthesis loops, and conditionally uses web search. | It is a bounded workflow, not a general autonomous tool-selection loop. Tools and transitions are predefined, and there is no general calculate/code/API tool set or open-ended “continue until satisfied” controller. |
| Production hybrid from the images | **Partial alignment** | ResearchMind combines vector RAG, CRAG-like evidence correction, bounded agentic research, web fallback, validation, guardrails, and output review. | It lacks the hybrid diagram's adaptive front router, GraphRAG branch, and one unified retrieval-quality grader shared across all branches. |

## 3. Current ResearchMind RAG baseline

Before comparing individual patterns, the current active RAG implementation can be summarized as follows:

| Phase | Current implementation | Architectural significance |
|---|---|---|
| Ingestion | Upload validation, SHA-256 duplicate detection, object storage, asynchronous queue, parsing, metadata/statistics enrichment, chunking, embedding, indexing | Production ingestion pipeline rather than an in-request prototype |
| Active chunking default | `ProcessingService` explicitly uses `ChunkingStrategy.MARKDOWN` | Structure-aware chunking is active; fixed-size, recursive, and hierarchical providers exist but are not the active default in this orchestration |
| Dense representation | Voyage AI document and query embeddings | Dense semantic retrieval |
| Sparse representation | FastEmbed/SPLADE sparse vectors | Lexical retrieval alongside dense retrieval |
| Vector store | Qdrant | Dense, sparse, and metadata-filtered retrieval plane |
| Candidate generation | Dense, sparse, and metadata retrieval run concurrently | Multi-channel retrieval rather than dense-only similarity search |
| Fusion | Reciprocal Rank Fusion | Combines multiple ranked candidate lists |
| Reranking | Voyage AI reranker when configured and results exist | Improves final candidate ordering |
| Context processing | Deduplication, optional parent expansion, adjacent merge, ordering, redundancy compression, optional contextual compression, token budgeting | Context optimization between retrieval and generation |
| Retrieval safety | Access control, source-trust reporting, sanitization, context guardrails | Safety and trust checks; not equivalent to a CRAG relevance grader |
| Grounding | Canonical citations plus generated-output citation and hallucination validation | Evidence-linked response generation |
| Generation | Provider routing, fallback chain, cache, structured output, guardrails, validation, bounded regeneration | Production generation layer beyond basic RAG |
| Multi-step research | Planner, dependency waves, per-task retrieval, evidence aggregation, synthesis, review, gap research, conditional web search | Bounded agentic/corrective extension over the baseline retrieval plane |

## 4. Architecture 1: Naive RAG

### Reference contract

The supplied Naive RAG architecture has the following defining sequence:

`Documents -> chunk -> embed -> vector store -> embed query -> similarity search -> top-k chunks -> LLM -> response`

### Component-by-component comparison

| Reference component or behavior | ResearchMind implementation | Alignment | Misalignment or gap |
|---|---|---|---|
| Document ingestion | Uploaded documents are validated, stored, parsed asynchronously, and indexed | **Strong alignment** | More operationally complex than the reference's direct document-to-vector-store path |
| Fixed-size chunking | A fixed-size provider exists, but the active processing orchestration selects Markdown chunking | **Partial alignment** | The active default does not use the reference architecture's fixed-size chunks |
| Embed every chunk | Active ingestion uses Voyage AI embeddings and builds embedding artifacts | **Strong alignment** | None at the conceptual level |
| Store in vector database | Qdrant stores indexed chunk representations | **Strong alignment** | None |
| Embed user query | Dense query embedding service is called for dense retrieval | **Strong alignment** | Query embedding is only one of three active retrieval channels |
| Similarity search | Qdrant dense search is implemented | **Strong alignment** | The system does not rely on similarity search alone |
| Fixed top-k | The API accepts `top_k`; hybrid retrieval expands the internal candidate pool and then returns the requested top-k | **Strong alignment with enhancement** | Candidate expansion, fusion, and reranking mean this is not a strictly fixed-k single-search pipeline |
| Retrieved chunks become LLM context | `ContextBuilderService` creates `PromptContext` for Linear and Deep Research | **Strong alignment** | Context is transformed significantly before generation |
| One retrieval pass | Linear Research performs one hybrid retrieval/context pass | **Strong alignment for Linear Research** | Deep Research performs multiple task and repair retrieval rounds |
| Direct response | Linear Research generates and optionally streams a cited response | **Strong alignment** | Additional persistence, validation, memory, artifacts, and citation handling add latency and complexity |
| Ambiguous-query handling | Dense+sparse+metadata fusion and reranking improve candidate selection | **Partial mitigation** | No dedicated query disambiguation or query-rewrite stage is present in the canonical Linear Research flow |
| Retrieval failure fallback | Deep Research can use conditional web search; individual Deep tasks become partial failures | **Partial alignment outside Linear Research** | Linear Research does not fall back to web search or another retrieval strategy when document retrieval is irrelevant, empty, or fails |
| Multi-hop support | Deep Research planner creates dependent task waves | **Strong mitigation in Deep Research** | Linear Research remains a single retrieval/generation pass |

### Assessment

| Question | Finding |
|---|---|
| Does ResearchMind implement Naive RAG's core? | **Yes.** The essential ingestion, embedding, vector retrieval, context, and generation chain is present. |
| Is ResearchMind currently a Naive RAG system? | **No.** Linear Research is better described as advanced hybrid-vector RAG, while Deep Research adds bounded corrective and agentic behavior. |
| Main advantage over Naive RAG | Hybrid retrieval, reranking, context processing, citations, guardrails, validation, and multi-step Deep Research reduce several classic Naive RAG failure modes. |
| Main trade-off | More services, external calls, latency, failure surfaces, observability requirements, and operating cost. |

## 5. Architecture 2: CRAG — Self-Correcting Retrieval

### Reference contract

The supplied CRAG architecture retrieves documents and then grades their usefulness:

| Grade | Reference behavior |
|---|---|
| Correct/relevant | Use retrieved documents directly |
| Incorrect/irrelevant | Fall back to web search |
| Ambiguous | Use both document and web evidence, allowing the answer stage to weigh them |

### Component-by-component comparison

| Reference component or behavior | ResearchMind implementation | Alignment | Misalignment or gap |
|---|---|---|---|
| Retrieve private documents first | Deep Research task execution uses owner-scoped hybrid Qdrant retrieval | **Strong alignment** | None |
| Relevance evaluator after retrieval | `WebSearchNecessityService` evaluates whether gathered private evidence is topically matched and sufficient before plan approval | **Partial-to-strong alignment in Deep Research** | It outputs `needs_web_search: bool`, not the reference's three-way relevance grade |
| Evaluate actual retrieved evidence | The necessity prompt receives a compact `ResearchEvidenceBundle` containing document names and excerpts | **Strong alignment** | Evaluation is capped to a bounded evidence summary, not every chunk |
| Correct -> use documents | When the evaluator says web search is unnecessary, Deep Research proceeds with private evidence | **Strong alignment** | Limited to Deep Research |
| Incorrect -> web fallback | A topical mismatch or coverage/recency gap can produce a web-search suggestion | **Strong alignment in Deep Research** | Search may require human approval and can be disabled; unavailable evaluator fails closed to document-only behavior |
| Ambiguous -> use both | Existing document task results remain while web evidence is added and evidence is re-aggregated | **Partial alignment** | There is no explicit `AMBIGUOUS` grade or confidence-weighting contract |
| Corrective evidence merge | Web results are normalized into the same `ResearchTaskResult`/evidence model and passed through evidence aggregation | **Strong alignment** | Web evidence does not pass through the same Qdrant context builder or source-trust model as uploaded chunks |
| Retrieval retry after review | A `RESEARCH_GAPS` review can trigger targeted document retrieval or another conditional web search, then re-synthesis | **Strong alignment with enhancement** | The correction is report-level and bounded, not a generic relevance correction applied to every retrieval call |
| Low-quality source detection | Retrieval guardrails include source trust and sanitization | **Conceptual overlap only** | Source trust checks provenance category, not semantic relevance to the query |
| Reranker as evaluator | Voyage reranking improves ordering | **Conceptual overlap only** | A reranker ranks candidates; it does not decide whether the whole evidence set is sufficient or whether to fall back |
| Linear Research correction | No equivalent post-retrieval adequacy decision exists | **Not implemented** | Linear Research always proceeds with the retrieved context unless retrieval/context raises an error |
| Chat correction | Chat's optional web necessity decision happens without document retrieval | **Not CRAG** | There is no private-document evidence to grade on the Chat path |

### CRAG alignment by product path

| Product path | CRAG alignment | Reason |
|---|---|---|
| Chat | **Low** | Web-search necessity exists, but Chat does not retrieve or grade uploaded documents |
| Linear Research | **Low-to-partial** | Advanced retrieval and guardrails exist, but no adequacy grade or corrective fallback exists |
| Deep Research | **Strong partial** | Evidence is evaluated, web fallback is conditional, evidence is merged, and review can trigger another retrieval round |

### Primary CRAG gaps

| Priority | Gap | Why it matters |
|---|---|---|
| High | No canonical retrieval-grade result such as `RELEVANT`, `IRRELEVANT`, `AMBIGUOUS` with confidence and reasons | The fallback decision cannot be reused consistently across Linear Research, Deep Research, retrieval APIs, and future agents |
| High | Linear Research has no empty/irrelevant/low-confidence fallback | The fastest document-grounded product path retains a central Naive RAG failure mode |
| Medium | No per-chunk semantic relevance filter after reranking | Weak chunks can remain in the context as long as they survive ranking and other context transformations |
| Medium | Web evidence and document evidence have different trust/context-processing paths | Mixed evidence does not receive one uniform grading and trust-normalization contract |
| Medium | Necessity-check failure returns “no web search” | This is safe for cost and consent, but not corrective robustness when private evidence is actually inadequate |

## 6. Architecture 3: Adaptive RAG — Route by Query Type

### Reference contract

The supplied Adaptive RAG architecture classifies a query before retrieval and selects an execution strategy such as:

| Query type | Reference route |
|---|---|
| Simple | Direct LLM or lowest-cost lookup |
| Complex/document question | Vector RAG |
| Current/external | Web search |
| Relational or multi-hop | GraphRAG or another multi-step engine |

### Component-by-component comparison

| Reference component or behavior | ResearchMind implementation | Alignment | Misalignment or gap |
|---|---|---|---|
| Front-door query classifier | No single classifier runs before all product paths | **Not implemented** | The user chooses Chat, Linear, or Deep mode in the frontend |
| Simple -> direct LLM | Chat provides a direct conversational generation path | **Partial alignment** | Selection is user-driven, not query-classifier-driven |
| Document query -> vector RAG | Linear Research provides hybrid Qdrant RAG | **Strong component alignment** | No automatic query-based routing into it |
| Current query -> web search | Chat has an opt-in web toggle and necessity decision; Deep Research supports AUTO/REQUIRED web modes | **Partial alignment** | Web activation depends on user mode/toggle and, in Deep Research, occurs after initial private retrieval |
| Multi-hop -> multi-step execution | Deep Research planner classifies complexity and builds dependent task waves | **Strong component alignment** | This is not GraphRAG and is not automatically selected by a global router |
| Complexity classification | Deep Research planner produces `SIMPLE`, `MODERATE`, or `COMPLEX` plans | **Partial-to-strong alignment** | Classification occurs only in proposal/escalation workflows and does not route among all RAG engines |
| Escalation recommendation | `/research/escalation-check` recommends Deep Research for non-simple plans without automatically executing it | **Strong alignment with explicit-consent product design** | It is advisory, not the reference's automatic adaptive router |
| Different retrieval strategies | Dense, sparse, and metadata retrieval always run together in hybrid retrieval | **Conceptual overlap only** | These are parallel retrieval channels, not query-conditioned architecture selection |
| Generation routing | Routing strategies select generation provider/model candidates | **Not Adaptive RAG routing** | Model routing does not choose document RAG, web search, GraphRAG, or agentic research |
| Cost-aware simple path | Chat is cheaper than document and Deep Research paths; Deep Research budgets tasks, iterations, and cost | **Partial alignment** | There is no automatic cheapest-sufficient-path policy |
| Automatic fallback between engines | Deep Research can add web search after evidence evaluation | **Partial alignment** | No routing between Linear, Deep, GraphRAG, or direct LLM after a failed route |

### Adaptive RAG gaps

| Priority | Gap | Required architectural capability |
|---|---|---|
| High | No shared query-routing contract | A typed classifier result describing intent, freshness, document dependence, relational/multi-hop need, risk, and confidence |
| High | No automatic or recommendation-based routing across all three product surfaces | A routing layer ahead of Chat/Linear/Deep orchestration while preserving explicit user consent for costly or external actions |
| High | No GraphRAG route | A relational retrieval engine must exist before a router can select it |
| Medium | No router fallback on low confidence | Low-confidence classifications should request user choice or use a safe combined strategy |
| Medium | No measured route-selection evaluation | A dataset must test whether queries are sent to the cheapest architecture that can answer correctly |

### Important non-equivalences

| Existing feature | Why it is not a full Adaptive RAG router |
|---|---|
| Generation `RoutingService` | Routes between LLM providers/models, not retrieval architectures |
| Qdrant hybrid retrieval | Runs multiple retrieval channels for every query instead of choosing a query-specific engine |
| Deep Research planner complexity | Classifies only inside the Deep/escalation workflow and produces research tasks rather than a global product route |
| Web-search necessity service | Decides whether web evidence is needed after or alongside a selected product path; it does not choose the initial architecture |

## 7. Architecture 4: GraphRAG — Retrieve Relationships

### Reference contract

The supplied GraphRAG architecture requires:

`Documents -> entity/concept extraction -> nodes and typed relationships -> knowledge graph -> graph-aware query -> relationship traversal -> evidence path -> answer`

### Component-by-component comparison

| Reference component or behavior | ResearchMind implementation | Alignment | Misalignment or gap |
|---|---|---|---|
| Entity extraction during ingestion | Metadata and document statistics are extracted | **Conceptual overlap only** | No canonical entity extraction for people, organizations, concepts, events, or claims |
| Relationship extraction | No active subject-predicate-object or typed relationship pipeline | **Not implemented** | No edges are created from documents |
| Knowledge graph storage | PostgreSQL, Valkey, Qdrant, and object storage are used | **Not implemented** | None is used as an entity-relationship knowledge graph retrieval plane |
| Graph schema and provenance | Chunk/document provenance exists | **Conceptual overlap only** | No entity IDs, relationship types, edge provenance, temporal validity, or confidence model |
| Entity linking and resolution | Duplicate documents are detected by checksum | **Not implemented** | Document duplicate detection is not entity resolution |
| Graph traversal | No graph traversal query service exists | **Not implemented** | Retrieval is vector, sparse, and metadata based |
| Relationship-path evidence | Citations point to chunks/documents | **Not implemented** | Citations do not encode a traversed relationship path |
| Multi-hop question support | Deep Research decomposes a question into dependent retrieval tasks | **Functional overlap, not GraphRAG** | Each task independently retrieves text; it does not traverse entity relationships |
| Community/global summaries | No graph community detection or hierarchical graph summaries | **Not implemented** | Broad corpus-level relational questions depend on text retrieval and synthesis |
| Graph-aware adaptive route | No GraphRAG engine exists | **Not implemented** | Adaptive routing cannot select a relational retrieval path |

### GraphRAG conclusion

| Question | Finding |
|---|---|
| Can Deep Research answer some multi-hop questions today? | **Yes.** The planner can decompose them into dependent text-retrieval tasks and synthesize across evidence. |
| Does that make the system GraphRAG? | **No.** Multi-step orchestration over vector-retrieved text is not graph construction or graph traversal. |
| Current official architectural stance | Existing ADR material explicitly treats GraphRAG as a future enhancement rather than an implemented retrieval path. |
| Largest missing investment | A complete second knowledge representation and retrieval plane: extraction, resolution, graph persistence, traversal, provenance, evaluation, and integration into context/citation services. |

## 8. Architecture 5: Agentic RAG — Reason to Retrieve

### Reference contract

The supplied Agentic RAG pattern lets an LLM-driven controller:

1. Plan steps.
2. Select a tool.
3. Execute the tool.
4. Evaluate the result.
5. Repeat when evidence is incomplete.
6. Produce a final answer when satisfied or when a bound is reached.

### Component-by-component comparison

| Reference component or behavior | ResearchMind implementation | Alignment | Misalignment or gap |
|---|---|---|---|
| Plan research steps | `ResearchPlanner` produces a schema-bound goal, complexity, execution strategy, tasks, priorities, and dependencies | **Strong alignment** | Planner is available only in Deep Research proposal/escalation |
| Validate the plan | Plan schema, task limits, dependency validation, and topological scheduling are implemented | **Strong alignment with production hardening** | User edits currently focus on the rewritten goal after retrieval, not re-execution of edited task topology |
| Execute multiple steps | LangGraph executes dependency waves and parallel task fan-out | **Strong alignment** | Steps are restricted to the predefined research workflow |
| Select among tools | Deep Research can perform document retrieval and conditional Tavily web search; paper search runs after report generation | **Partial alignment** | There is no general LLM tool-selection protocol; most transitions are deterministic and predefined |
| Evaluate result quality | Evidence adequacy check, deterministic citation/completeness review, and optional model review exist | **Strong alignment** | Evidence evaluation and final-draft review are separate specialized decisions, not one general agent observation loop |
| Repeat if incomplete | Review can trigger synthesis revision, targeted document gap retrieval, or web-gap retrieval | **Strong alignment** | Loops are narrow and bounded by predefined decisions |
| Stop when satisfactory | PASS or FINALIZE_WITH_LIMITATIONS proceeds to report approval and persistence | **Strong alignment** | A human report checkpoint is additionally required |
| Bounded autonomy | Maximum tasks, concurrency, review iterations, web calls, cost, duration, and approvals constrain execution | **Strong production alignment** | Less flexible than open-ended Agentic RAG by deliberate design |
| Human-in-the-loop | Proposal approval, plan approval, conditional web-search approval, and report approval are implemented | **Enhancement over reference** | Increases latency and user effort |
| General calculation/code/API tools | No general calculator, code executor, arbitrary API, database query, or reusable tool registry is active in the Deep graph | **Not implemented** | Complex analytical tasks remain limited to retrieval, generation, and synthesis |
| Dynamic replanning | Gap research adds one targeted task and increments plan version | **Partial alignment** | The agent does not fully revise the task DAG or select an arbitrary next tool based on all observations |
| Tool-result memory/scratchpad | Compact task results and evidence bundles are kept in graph state and artifacts | **Strong alignment** | Raw documents/provider outputs are deliberately excluded, limiting flexible later reuse |
| Paper tool in the reasoning loop | MCP paper search suggests related papers after the final report | **Low alignment** | It is non-blocking post-processing, not evidence used by the current report |

### Agentic RAG conclusion

| Dimension | Finding |
|---|---|
| Best description | **Bounded, single-agent research workflow with controlled corrective loops** |
| Not an accurate description | General-purpose autonomous Agentic RAG or unrestricted ReAct tool use |
| Architectural strength | Deterministic state, explicit budgets, checkpointing, partial failure handling, citations, review, and human approvals |
| Architectural limitation | The controller cannot freely choose and sequence a broad tool set or rewrite the entire plan based on observations |

## 9. Production hybrid architecture comparison

The supplied production pattern combines:

`Adaptive router -> Naive/Graph/Agentic branch -> CRAG retrieval grading -> optional web fallback -> LLM and output validation -> verified response`

### End-to-end comparison

| Hybrid stage | ResearchMind equivalent | Alignment | Gap |
|---|---|---|---|
| User query | Chat, Linear Research, and Deep Research entry points | **Strong component alignment** | Entry points are separate product modes |
| Adaptive query router | User mode selection plus optional escalation check | **Partial alignment** | No shared automatic front router |
| Simple -> Naive/vector RAG | Linear Research uses advanced hybrid-vector RAG | **Strong branch alignment** | It is not automatically selected based on query type |
| Relation -> GraphRAG | None | **Not implemented** | No graph retrieval plane |
| Complex -> Agentic | Deep Research proposal and bounded runtime | **Strong branch alignment** | User must select/approve it; no global router |
| CRAG quality grade | Deep Research web-search necessity and later review/gap loop | **Partial alignment** | No uniform grader shared by Linear and Deep paths; no explicit correct/incorrect/ambiguous result |
| Insufficient -> web fallback | Deep Research conditional Tavily search | **Strong alignment in Deep Research** | Linear Research lacks it; fallback can be disabled or approval-gated |
| LLM generation | Shared Generation Runtime | **Strong alignment** | None conceptually |
| Output validation | Validation, hallucination scoring, guardrails, structured-output repair, citation checks | **Strong alignment and enhancement** | Streaming validation is informational after tokens have already reached the client |
| Verified response | Cited Linear responses and reviewed Deep reports | **Strong alignment** | Chat web/paper source metadata is not a durable canonical citation model |

### Current hybrid shape

ResearchMind's current effective hybrid is:

| Stage | Current behavior |
|---|---|
| Route selection | User selects Chat, Linear, or Deep; escalation check can recommend Deep |
| Primary document retrieval | Dense + sparse + metadata -> RRF -> optional rerank |
| Context optimization | Guardrails -> dedup -> parent expansion -> merge -> compression -> citations |
| Fast answer path | Linear Research performs one retrieval/context/generation pass |
| Complex answer path | Deep Research plans multiple retrieval tasks and aggregates evidence |
| Corrective behavior | Deep Research evaluates web necessity and review gaps, then performs bounded additional retrieval |
| External evidence | Tavily web search during Chat/Deep; MCP papers during Chat or after a Deep report |
| Output assurance | Generation guardrails, validation, hallucination/citation checks, deterministic research review, human approval |

This is a real hybrid architecture, but it is not yet the exact hybrid shown in the reference because routing, correction, and graph retrieval are unevenly distributed across product paths.

## 10. Cross-architecture alignment matrix

| Capability | Naive | CRAG | Adaptive | GraphRAG | Agentic | ResearchMind status |
|---|---:|---:|---:|---:|---:|---|
| Document parsing/chunking | Required | Required | Branch-dependent | Required | Tool-dependent | **Implemented** |
| Dense vector retrieval | Core | Usually core | One possible route | Optional supplement | One possible tool | **Implemented** |
| Sparse retrieval | Optional | Optional | One possible route | Optional supplement | One possible tool | **Implemented** |
| Metadata retrieval | Optional | Optional | One possible route | Optional supplement | One possible tool | **Implemented** |
| Fusion and reranking | Optional enhancement | Helpful | Route-specific | Optional | Tool-specific | **Implemented** |
| Context compression | Optional | Helpful | Route-specific | Helpful | Helpful | **Implemented** |
| Retrieval relevance grading | Absent | Core | Helpful | Helpful | Part of observation | **Partial, Deep only** |
| Web fallback | Absent | Core corrective route | Current/external route | Optional | Tool option | **Partial, Chat/Deep** |
| Query-type routing | Absent | Optional | Core | Useful | Planner may decide | **Partial, advisory/user-driven** |
| Entity and relation extraction | Absent | Absent | Graph branch prerequisite | Core | Optional tool | **Not implemented** |
| Knowledge graph traversal | Absent | Absent | Graph branch | Core | Optional tool | **Not implemented** |
| Planning/decomposition | Absent | Optional | Complex route | Query planning | Core | **Implemented in Deep** |
| Multi-step retrieval loop | Absent | Corrective | Route-dependent | Multi-hop traversal | Core | **Implemented in Deep** |
| Dynamic tool selection | Absent | Small branch | Router selects engine | Graph operations | Core | **Limited/predefined** |
| Result-quality evaluation | Minimal | Core retrieval grade | Router/fallback dependent | Path/evidence validation | Core loop decision | **Implemented, but split across stages** |
| Output validation | Optional | Recommended | Recommended | Recommended | Recommended | **Implemented** |
| Citations and provenance | Optional | Recommended | Recommended | Graph-path provenance | Recommended | **Implemented for document research** |
| Human approvals | Absent | Optional | Optional | Optional | Optional | **Implemented extensively in Deep** |
| Budgets and loop limits | Not needed | Recommended | Recommended | Recommended | Essential | **Implemented in Deep** |

## 11. Misalignments that should not be mistaken for gaps

Some differences are deliberate product or safety choices rather than defects:

| Difference | Interpretation |
|---|---|
| Chat does not retrieve uploaded documents | Deliberate separation between conversational Chat and document-grounded Research |
| Deep Research requires explicit proposal approval | Consent and cost-control boundary, not missing agent capability |
| Web search may require approval | External-data and cost checkpoint, not a CRAG implementation error |
| Deep loops are bounded | Production safety property rather than failure to support agentic behavior |
| Retrieval always uses dense+sparse+metadata | Deliberate robust default; not necessarily inferior to selecting only one retriever per query |
| Paper search runs after a Deep report | Deliberate recommendation feature; it should not be credited as a report-evidence tool |
| Frameworks differ from the images | Out of scope for this evaluation; component responsibilities and control flow are what matter |

## 12. Prioritized architecture gaps

| Priority | Gap | Architectures affected | Current consequence | Suggested architectural direction |
|---|---|---|---|---|
| P0 | No shared retrieval adequacy/grading contract | CRAG, Hybrid, Agentic | Linear Research cannot detect “retrieved but irrelevant” as a first-class outcome | Introduce a typed evidence-grade service after context building with label, confidence, reasons, failed dimensions, and recommended next action |
| P0 | No adaptive front-door router | Adaptive, Hybrid | Users must understand which product mode and tool toggle to choose | Add an advisory router first; preserve user confirmation for Deep Research and external search |
| P1 | Linear Research has no corrective fallback | CRAG, Hybrid | Empty, stale, or off-topic evidence either produces a weak answer or a hard failure | Route low-grade evidence to query rewrite, broader retrieval, web suggestion, or explicit “insufficient evidence” response |
| P1 | No GraphRAG retrieval plane | GraphRAG, Adaptive, Hybrid | Relationship-heavy and corpus-global questions rely on text similarity and synthesis | Add entity/relation extraction, resolution, graph persistence, traversal, provenance, and a graph context adapter only when validated use cases justify the cost |
| P1 | No unified evidence-quality policy across document and web sources | CRAG, Hybrid, Agentic | Evidence types are normalized structurally but do not receive identical relevance/trust grading | Define one evidence model and grading interface with source-specific adapters |
| P2 | No query rewriting/clarification in Linear Research | Naive mitigation, CRAG, Adaptive | Ambiguous or conversational queries can retrieve the wrong chunks | Add a bounded rewrite/clarification stage informed by conversation and memory, with original-query provenance |
| P2 | Deep Research tool choice is mostly fixed | Agentic | The workflow cannot incorporate calculations, structured data, or arbitrary internal tools | Add a policy-controlled tool registry only for validated tool classes, with schemas, budgets, approvals, and result normalization |
| P2 | Deep replanning is narrow | Agentic | Gap repair adds one targeted task instead of revising the plan DAG | Support bounded plan amendments with dependency validation and explicit versioning |
| P2 | Streaming output is scored after delivery | Hybrid verified-response goal | A blocked post-generation verdict cannot retract streamed tokens | Buffer high-risk runtimes or stream provisional output with a final verification state |
| P3 | Active ingestion does not use hierarchical chunking by default | Naive enhancement, CRAG | Parent expansion exists but default Markdown chunks may not supply hierarchical parent relationships | Evaluate Markdown versus hierarchical chunking by document type and retrieval benchmark before changing defaults |

## 13. Recommended target architecture

A practical target based on the current codebase is not to replace the existing retrieval platform. It is to add missing decisions around it:

| Order | Target stage | Reuse from current implementation | New capability |
|---:|---|---|---|
| 1 | Query characterization | Deep planner schemas, memory context, classification routing strategy | Shared query-route result: direct, document, web, deep, relational, or clarify |
| 2 | User/consent policy | Existing modes, rate limits, proposal and web approvals | Convert automatic route into recommendation when cost/external access requires consent |
| 3 | Retrieval engine | Existing hybrid Qdrant retrieval and context builder | Optional future graph retrieval adapter |
| 4 | Evidence grading | Deep web-necessity logic, source trust, reranker, context statistics | Uniform `relevant / irrelevant / ambiguous / insufficient` evidence grade |
| 5 | Corrective action | Deep web search and targeted gap retrieval | Linear query rewrite, broader retry, web suggestion, or abstention |
| 6 | Reasoning loop | Deep planner, waves, review, bounded retries | Policy-controlled tools and bounded plan amendments |
| 7 | Generation and validation | Existing Generation Runtime, guardrails, citations, hallucination checks | Pre-delivery verification policy for high-risk streaming paths |
| 8 | Evaluation | Existing benchmark and observability foundations | Route accuracy, evidence-grade accuracy, fallback utility, graph retrieval value, answer quality, latency, and cost metrics |

## 14. Final verdict

| Evaluation question | Verdict |
|---|---|
| Is the platform still Naive RAG? | **No.** It contains the Naive RAG foundation but substantially exceeds it. |
| What best describes Linear Research? | **Advanced single-pass hybrid-vector RAG with reranking, context engineering, citations, guardrails, and validation.** |
| What best describes Deep Research? | **Bounded agentic RAG with partial CRAG behavior, human approvals, and deterministic/model-assisted review.** |
| Is Adaptive RAG implemented? | **Partially.** The necessary product branches exist, but a shared automatic/advisory query router does not. |
| Is CRAG implemented? | **Partially and mainly in Deep Research.** Evidence adequacy can trigger web correction, but no reusable three-state relevance grader exists. |
| Is GraphRAG implemented? | **No.** Multi-step vector retrieval is not graph retrieval. |
| Does ResearchMind match the proposed production hybrid? | **Partially.** It has vector RAG, agentic research, corrective web fallback, and strong validation, but lacks adaptive routing, GraphRAG, and uniform retrieval grading. |
| Most important next architectural step | **Add a shared query/evidence decision layer before investing in a new retrieval store.** It improves CRAG, Adaptive, Linear, Deep, and the production hybrid simultaneously. |

## 15. Principal code references

| Concern | Primary code |
|---|---|
| Active ingestion/chunk/embed/index flow | `apps/api/app/ai/knowledge/processing/service.py` |
| Chunking providers | `apps/api/app/ai/knowledge/chunking/` |
| Hybrid retrieval, RRF, reranking | `apps/api/app/ai/knowledge/retrieval/service.py` |
| Context engineering and retrieval guardrails | `apps/api/app/ai/knowledge/context/service.py` |
| Linear Research orchestration | `apps/api/app/ai/research/service.py` |
| Chat document-retrieval boundary | `apps/api/app/api/v1/chat.py` |
| Chat web/paper augmentation | `apps/api/app/ai/runtime/chat/web_search.py`, `apps/api/app/ai/runtime/chat/paper_search.py` |
| Deep Research planning | `apps/api/app/ai/runtime/research/planner/service.py` |
| Dependency-wave scheduling | `apps/api/app/ai/runtime/research/decomposition/scheduler.py` |
| Per-task retrieval | `apps/api/app/ai/runtime/research/retrieval/service.py` |
| Deep corrective and agentic loop | `apps/api/app/ai/runtime/research/workflows/multi_wave_research.py` |
| Evidence/web necessity decision | `apps/api/app/ai/runtime/research/web_search/necessity.py` |
| Draft quality review | `apps/api/app/ai/runtime/research/review.py` |
| Generation routing, validation, fallback, and regeneration | `apps/api/app/ai/runtime/generation/service.py` |
| GraphRAG scope status | `docs/adrs/ADR-019-qdrant-native-hybrid-retrieval.md` |

