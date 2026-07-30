# Agentic RAG Industry-Alignment Evaluation

**Code snapshot reviewed:** 2026-07-28  
**Reference:** The supplied Agentic RAG architecture images and production checklist.  
**Scope:** Current executable architecture in `apps/api`, `apps/worker`, and `apps/web`. Framework differences are ignored; component responsibilities, decisions, control flow, safety, and operational behavior are evaluated.

## 1. Executive verdict

ResearchMind has a credible production-oriented Agentic RAG implementation in its **Deep Research** path, but it is more accurately described as a:

> **Bounded, single-agent research workflow with deterministic orchestration, LLM planning and review, hybrid retrieval, corrective web fallback, persistent checkpoints, memory, human approvals, and strong runtime controls.**

It is not a general-purpose ReAct agent where an LLM freely chooses arbitrary tools after every observation. This difference is not automatically a weakness. For ResearchMind's current product, the bounded workflow covers many of the highest-value Agentic RAG capabilities while reducing unpredictable tool use, infinite loops, security risk, latency, and evaluation difficulty.

### Overall industry-alignment summary

| Dimension | Alignment | Summary |
|---|---|---|
| Agentic planning and decomposition | **Strong** | Deep Research creates schema-bound plans, classifies complexity, validates dependencies, and executes parallel dependency waves. |
| Retrieval quality | **Strong** | Dense, sparse, and metadata retrieval, RRF fusion, reranking, context processing, and citations exceed the reference baseline. |
| Corrective retrieval | **Strong partial** | Deep Research can evaluate evidence sufficiency and add web or targeted document evidence. Linear Research lacks this correction path. |
| Self-reflection | **Strong partial** | Deep drafts receive deterministic and model-assisted review with bounded revision. There are no Self-RAG reflection tokens or mid-generation retrieval decisions. |
| Adaptive routing | **Partial** | Product paths and complexity classification exist, but no shared front-door `DIRECT / RETRIEVE / DEEP / CLARIFY` router exists. |
| ReAct behavior | **Low-to-partial** | The graph contains action/observation/retry behavior, but transitions and tools are predefined rather than dynamically selected by an LLM. |
| Retrieval as an LLM-callable tool | **Low** | Retrieval is a canonical service invoked by graph nodes, not a native tool exposed for optional model function-calling. |
| Multi-tool autonomy | **Low-to-partial** | Document retrieval and web search are conditionally selected; paper search is available in limited positions. There is no general tool registry or SQL/calculation/code tool plane. |
| State, checkpointing, and memory | **Strong** | PostgreSQL graph checkpoints, durable run state, event journal, conversation history, and session/semantic/research memory are implemented. |
| Loop and cost controls | **Strong** | Task, concurrency, review-iteration, web-call, recursion, duration, queue, and estimated-cost limits are enforced. |
| Security and human control | **Strong** | Retrieval sanitization, input guardrails, owner scoping, rate limits, and explicit approvals are substantial strengths. |
| Streaming and UX | **Strong** | Chat/Linear token streaming and Deep Research progress-event streaming are implemented with visible approvals and replay. |
| Agent-specific evaluation | **Weak-to-partial** | General retrieval/generation benchmarks and runtime metrics exist, but routing accuracy, tool-selection accuracy, retry utility, and over/under-retrieval metrics are not first-class. |
| Full graph observability | **Partial-to-strong** | Durable events, logs, metrics, artifacts, and generation traces exist; one unified trace of every graph node, decision, state transition, and tool call is incomplete. |
| Multi-agent RAG | **Not implemented by design** | The accepted architecture intentionally prefers one bounded workflow until specialization demonstrates measurable value. |

### Bottom line

| Question | Verdict |
|---|---|
| Does ResearchMind meet the core idea of Agentic RAG? | **Yes, in Deep Research.** It plans, decomposes, retrieves repeatedly, evaluates results, corrects gaps, synthesizes, reviews, and stops under explicit bounds. |
| Does every product path use Agentic RAG? | **No.** Chat and Linear Research deliberately provide cheaper, simpler paths. |
| Does it match a classic open-ended ReAct agent? | **No.** The graph is bounded and mostly deterministic, with LLM decisions inside controlled nodes. |
| Is that an industry misalignment? | **Not necessarily.** Bounded agency is a common production trade-off and is appropriate when reliability, consent, cost, and auditability matter. |
| Largest standards gaps | A shared adaptive router, canonical retrieval grading, Linear corrective fallback, explicit ambiguity handling, agent-specific evaluation, and end-to-end graph tracing. |
| Capabilities that are optional today | General native tool calling, SQL/code/calculator tools, fully dynamic replanning, and multi-agent supervision. |

## 2. Evaluation scale and necessity classes

### Alignment scale

| Rating | Meaning |
|---|---|
| **Strong** | The reference capability is active and fulfills its architectural purpose. |
| **Partial** | Important elements exist, but only in one path or with a narrower contract. |
| **Conceptual overlap** | A related component exists but does not perform the reference capability's defining role. |
| **Absent** | The component or behavior is not implemented in the active runtime. |

### Necessity classification

Not every image component should automatically become a backlog item.

| Class | Meaning |
|---|---|
| **Essential now** | Needed for safety, reliability, grounding, or the current Deep Research value proposition. |
| **High-value next** | Would materially improve quality, cost, or usability across existing product paths. |
| **Conditional** | Implement only when validated use cases show measurable value. |
| **Not required now** | The current bounded architecture intentionally achieves the product goal without it. |

## 3. Named Agentic RAG patterns

### 3.1 Pattern landscape

| Pattern from reference | Defining industry concept | ResearchMind equivalent | Alignment | Main gap | Necessity |
|---|---|---|---|---|---|
| Self-RAG | Model critiques retrieval and its own output, potentially requesting more evidence during generation | Generation validation and hallucination scoring; Deep deterministic/model review; synthesis revision loop | **Partial** | No special reflection-token protocol, no mid-token retrieval, and no equivalent revision loop for Linear Research | **High-value next** for a unified post-answer reflection contract; reflection tokens are **not required now** |
| Corrective RAG | Grade retrieved evidence and fall back to a broader source when weak | Deep `WebSearchNecessityService`, early evidence check, targeted gap retrieval, Tavily fallback, re-aggregation | **Strong partial** | No reusable `relevant / irrelevant / ambiguous / insufficient` evidence-grade contract; Linear has no correction | **High-value next** |
| Adaptive RAG | Route by query complexity and need before choosing execution path | User-selected Chat/Linear/Deep modes; Deep planner complexity; escalation recommendation | **Partial** | No global front-door router or explicit `DIRECT / RETRIEVE / DEEP / CLARIFY` decision | **High-value next** |
| ReAct-style RAG | Repeated reason -> act/tool -> observe -> choose next action | Planner -> task retrieval -> evidence -> review -> gap action -> re-synthesis | **Partial** | LLM does not freely select arbitrary tools or the next graph transition after each observation | **Conditional**; bounded flow is currently safer |
| Multi-Agent RAG | Supervisor routes work to specialized agents | Single Deep Research workflow with specialized services/nodes | **Absent by design** | No supervisor/worker-agent topology or inter-agent protocols | **Not required now** per ADR-033 |

### 3.2 Self-RAG comparison

| Self-RAG component | Current implementation | Alignment | Gap or qualification |
|---|---|---|---|
| Critique retrieved evidence | Deep Research evaluates private evidence for topical match and sufficiency before synthesis | **Partial-to-strong** | Evaluation is a separate structured decision, not model-generated reflection tokens |
| Critique generated output | Deep Research reviews citation integrity, completeness, model quality, concerns, and evidence gaps | **Strong** | Linear Research does not route a failed answer back through a correction loop |
| Detect unsupported citations | Deterministic review identifies citations not present in the evidence bundle; generation validation also checks citations/hallucination | **Strong** | Citation correctness does not prove every factual claim is semantically entailed |
| Request more evidence | `RESEARCH_GAPS` can trigger a targeted document task or conditional web search | **Strong** | At most one targeted question per review iteration |
| Regenerate with feedback | `REVISE_SYNTHESIS` carries explicit revision instructions into the next synthesis | **Strong** | Only Deep Research has this graph-level correction |
| Reflect during token generation | Streaming and non-streaming providers generate conventionally | **Absent** | No mid-generation retrieve/reflect control token mechanism |
| Bound reflection cycles | Complexity-specific review-iteration, cost, duration, and graph-recursion limits | **Strong** | None |
| Return supported/limited answer | PASS, FINALIZE_WITH_LIMITATIONS, rejection-as-plain-answer, or failure outcomes exist | **Strong** | A consistent confidence/verification label is not exposed across all surfaces |

### 3.3 CRAG comparison

| CRAG component | Current implementation | Alignment | Gap or qualification |
|---|---|---|---|
| Grade retrieved documents | Deep evidence summary is judged for topical relevance and sufficiency | **Partial-to-strong** | No canonical per-chunk or three-state grade |
| Continue with good local evidence | Deep proceeds to plan approval and synthesis when web is unnecessary | **Strong** | Limited to Deep |
| Broader fallback | Tavily web search adds normalized web evidence | **Strong** | User approval may be required, correctly preserving consent |
| Combine local and web evidence | Web results become synthetic task results and are re-aggregated with local evidence | **Strong** | Web evidence does not traverse exactly the same context/trust pipeline as document chunks |
| Correct again after answer review | Review gaps can trigger another targeted retrieval round | **Strong** | Bounded to the review budget |
| Handle evaluator failure | Necessity failure logs and continues document-only | **Safe but weak correction** | Avoids breaking the run but can under-retrieve |
| Apply to fast RAG path | Linear Research always runs its document pipeline | **Absent** | No fallback for empty, irrelevant, or stale Linear evidence |

### 3.4 Adaptive RAG comparison

| Adaptive component | Current implementation | Alignment | Gap or qualification |
|---|---|---|---|
| Classify query complexity | Planner emits SIMPLE, MODERATE, or COMPLEX | **Strong inside Deep/escalation** | Classification is not applied to every incoming query |
| Simple -> direct/cheap path | Chat and Linear paths exist | **Partial** | User selects the path |
| Complex -> multi-step path | Deep Research proposal and runtime | **Strong** | Requires explicit approval, which is a desirable product constraint |
| Current/external -> web | Chat toggle and Deep AUTO/REQUIRED modes | **Partial** | No global router automatically recommends web for all surfaces |
| Clarify ambiguous query | No dedicated clarify branch | **Absent** | Memory may resolve references, but genuinely ambiguous intent is not returned as a clarification request |
| Record route decision | Escalation, plan, and web decisions are logged/persisted | **Partial** | There is no one canonical route-decision artifact |
| Measure routing accuracy | General metrics exist | **Absent** | No labeled route-evaluation dataset or routing-confusion metrics |

### 3.5 ReAct-style comparison

| ReAct component | Current implementation | Alignment | Gap or qualification |
|---|---|---|---|
| Reason | Planner and reviewer make structured LLM decisions | **Strong** |
| Act | Graph executes document retrieval, web search, synthesis, and persistence nodes | **Strong** |
| Observe | Evidence bundles, task statuses, draft, review, cost, and counts are written into state | **Strong** |
| Select next action from observation | Conditional edges route on review and web decisions | **Partial** | Available actions are predefined and mostly selected through typed decisions rather than native tool calls |
| Repeat until satisfied | Review loops to revision or gap retrieval | **Strong but bounded** | Correctly stops on iteration/cost/duration limits instead of trusting the model to stop |
| General-purpose tool use | No general calculator, code, SQL, arbitrary API, or internal-action tools | **Absent** | Only needed if product requirements expand beyond research over documents/web |
| Parallel actions | Retrieval tasks in the same dependency wave execute in parallel | **Strong** | No general parallel native tool-call planner |
| Dynamic replanning | Gap research appends a targeted task and increments plan version | **Partial** | The complete DAG is not freely rewritten after every observation |

## 4. Core Agentic RAG building blocks

| Reference building block | Current ResearchMind implementation | Alignment | Gap | Necessity |
|---|---|---|---|---|
| Retrieval as a tool | `ResearchTaskRetrievalService` is a callable application service used by graph nodes | **Conceptual overlap** | It is not exposed to the LLM as an optional native function/tool with a schema and description | **Conditional** |
| Decision/router node | Planner, escalation check, web necessity, review routing, and deterministic conditional edges | **Partial-to-strong** | No single pre-retrieval `DIRECT / RETRIEVE / DEEP / CLARIFY` router | **High-value next** |
| Grading node | Web necessity evaluates evidence; review grades citation integrity/completeness and optional model quality | **Strong partial** | Retrieval grading is not canonical or shared across product paths | **High-value next** |
| Correction path | Targeted document gap retrieval, web fallback, synthesis revision, limitations, failure | **Strong** | Linear correction path missing | **High-value next** |
| The loop | Multi-wave retrieval and bounded review/gap loops | **Strong** | No open-ended general tool loop—which is not currently necessary |
| Short-term state | Typed graph state includes plan, waves, task results, evidence, draft, review, counters, decisions, and refs | **Strong** | Some state is dictionary-based rather than fully domain-typed at every boundary |
| Durable graph state | PostgreSQL checkpointer with run/thread identity and resume commands | **Strong** | Operational provisioning must be performed explicitly |
| Cross-turn memory | Conversation history plus session, semantic, user, and research memory | **Strong** | Memory quality and promotion accuracy remain separate evaluation concerns |

## 5. Step-by-step component evaluation

### Step 1: Expose retrieval as a tool

| Reference expectation | Current implementation | Alignment | Gap analysis |
|---|---|---|---|
| LLM can optionally call retrieval | Deep graph deterministically invokes retrieval for every planned task | **Low** | Retrieval is mandatory within a planned task, not optional native tool use |
| Clear tool description determines usage | Retrieval service has a clear code contract, but the LLM does not read a tool description | **Absent for native tool use** | Planner prompts describe research planning rather than bind a retrieval function |
| One tool per source | Document retrieval, Tavily, and MCP paper search are separate services | **Partial component alignment** | They are not presented together in one tool-selection registry |
| Structured arguments and results | Typed requests/results exist for retrieval, web, and paper search | **Strong foundation** | No common `ToolDefinition`/`ToolResult` envelope across them |
| Retrieval can be skipped | Web can be skipped; document retrieval is intrinsic to Linear and Deep planned tasks | **Partial** | Global direct-answer routing is user-selected rather than agent-selected |

**Assessment:** Native retrieval-as-tool is optional for ResearchMind today. The existing explicit graph node is more predictable. It becomes valuable if ResearchMind adds heterogeneous tools whose selection cannot be modeled cleanly with fixed workflow nodes.

### Step 2: Decision/router node

| Reference expectation | Current implementation | Alignment | Gap analysis |
|---|---|---|---|
| Decide whether external knowledge is needed before retrieval | Product mode decides Chat vs Research; Deep proposal always plans research; Chat web necessity decides web need | **Partial** | No shared router ahead of all paths |
| Narrow typed output | Planner, web necessity, and review all use structured models | **Strong** | Route taxonomy is distributed across multiple models |
| Separate decision from answering | Planner and necessity services do not answer the user | **Strong** | None |
| Log production decisions | Structured logs, run state, budget usage, and event journal record many decisions | **Strong partial** | No canonical route-decision table/artifact or accuracy label |
| Avoid over/under-retrieval | User mode and web necessity reduce some waste | **Partial** | No measured over/under-retrieval rates |

### Step 3: Query reformulation

| Reference expectation | Current implementation | Alignment | Gap analysis |
|---|---|---|---|
| Rewrite raw input into retrieval query | Deep planner rewrites the overall goal and creates task questions | **Strong for Deep** | Linear Research sends the user's query directly after whitespace normalization |
| Resolve pronouns from history | Conversation transcript and memory/session-state context are available; paper-query extraction explicitly uses context | **Partial-to-strong** | Canonical document retrieval has no dedicated conversational query-condensation service |
| Preserve original intent | Original query remains persisted alongside plan/tasks | **Strong** | No rewrite-quality score or diff evaluation |
| Fail safely if rewrite fails | Planner schema failure stops Deep before retrieval | **Strong** | Linear has no rewrite stage to fail or fall back |

**Important distinction:** Deep planning/decomposition covers the search-query optimization need for Deep Research. A separate query rewrite is mainly a gap for Linear Research follow-ups and ambiguous queries.

### Step 4: Query decomposition and multi-hop execution

| Reference expectation | Current implementation | Alignment | Gap analysis |
|---|---|---|---|
| Break complex query into subquestions | Planner creates bounded `ResearchPlanTask` items | **Strong** |
| Express dependencies | Tasks carry dependencies and the plan is validated as a DAG | **Exceeds reference** |
| Execute independent questions separately | Topological waves fan out ready tasks with bounded concurrency | **Strong** |
| Combine evidence | Stable task-result reducer and evidence bundle aggregate all tasks | **Strong** |
| Revisit missing subquestions | Reviewer may create one targeted gap task | **Strong partial** | Only one gap question per review |
| Version evolving plan | `plan_version` and `plan_versions` are stored in graph state | **Strong** | Initial plan edits after evidence do not rebuild and rerun the task graph |

### Step 5: Hybrid retrieval execution

| Reference expectation | Current implementation | Alignment | Gap analysis |
|---|---|---|---|
| Dense semantic retrieval | Voyage query/document embeddings with Qdrant dense search | **Strong** |
| Sparse lexical retrieval | SPLADE/FastEmbed sparse query and Qdrant sparse search | **Strong concept alignment** | Uses learned sparse retrieval rather than BM25; framework/algorithm difference is not a conceptual gap |
| Run retrievers together | Dense, sparse, and metadata searches execute concurrently | **Exceeds reference** |
| Combine rankings | Reciprocal Rank Fusion | **Strong** |
| Tune weighting by domain | Fixed RRF behavior in the active service | **Partial** | No query/domain-conditioned fusion weighting |
| Rerank final candidates | Voyage AI reranking | **Strong** |
| Optimize context after retrieval | Deduplication, parent expansion, adjacent merge, ordering, contextual/token compression | **Exceeds reference** |

### Step 6: Grade retrieved documents

| Reference expectation | Current implementation | Alignment | Gap analysis |
|---|---|---|---|
| Ask whether documents are sufficient | Deep `WebSearchNecessityService` evaluates topical match and sufficiency | **Strong partial** |
| Grade before answering | Early Deep evaluation occurs before synthesis | **Strong** |
| Per-chunk relevance | Reranking orders chunks; guardrails inspect safety/trust | **Partial** | No explicit semantic relevance grade on each surviving chunk |
| Typed grade | `WebSearchNecessityDecision` is structured | **Strong foundation** | Binary web need is not the same as evidence quality/ambiguity/confidence |
| Feed reasons into correction | Suggested query and reason are shown at web approval | **Strong** |
| Use in Linear Research | No adequacy check after Linear context construction | **Absent** |

### Step 7: Corrective retrieval and web fallback

| Reference expectation | Current implementation | Alignment | Gap analysis |
|---|---|---|---|
| Route weak local retrieval to web | Deep AUTO/REQUIRED web behavior | **Strong** |
| Do not silently hallucinate | Review can fail, revise, research gaps, or finalize with disclosed limitations | **Strong** |
| Keep source identity | Evidence references retain source type, filename/title, citation ID, and URL/synthetic IDs | **Strong** |
| Apply source trust | Document retrieval guardrail has source-trust reporting; web sources are distinguished in evidence/UI | **Partial** | Web and private evidence do not use one uniform trust-scoring pipeline |
| Tool timeout | Tavily and MCP clients use configured timeouts | **Strong** |
| Tool-call budget | Web search has a per-run maximum; paper search uses timeout/cache | **Strong** |
| Human approval | AUTO web search can interrupt for approval; REQUIRED/auto-approved modes are explicit | **Exceeds reference for consent** |
| Total fallback failure | Web failure is converted to a failed synthetic task and the bounded workflow continues | **Strong partial** | User-facing insufficiency messaging depends on later review outcome |

### Step 8: Self-reflection on the answer

| Reference expectation | Current implementation | Alignment | Gap analysis |
|---|---|---|---|
| Critique answer against evidence | Deep deterministic and model-assisted review | **Strong** |
| Detect unsupported claims/citations | Citation-integrity checks, hallucination validation, faithfulness guardrails | **Strong** |
| Route unsupported output to regenerate | `REVISE_SYNTHESIS` loops with instructions | **Strong** |
| Route incomplete output to retrieve | `RESEARCH_GAPS` creates targeted retrieval | **Strong** |
| Surface low confidence/limitations | `FINALIZE_WITH_LIMITATIONS` persists limitations | **Strong** |
| Reflect on Linear answers | Generation validation scores output | **Partial** | Linear does not have a graph loop that reacts to the score |
| Reflect on streamed output before delivery | Scoring occurs after tokens are streamed | **Weak** | A bad verdict cannot retract delivered content |

### Step 9: Final answer with citations

| Reference expectation | Current implementation | Alignment | Gap analysis |
|---|---|---|---|
| Stable citation IDs | Context citation service and Deep evidence citation IDs | **Strong** |
| Claim/source traceability | Research responses and reports carry citations and sources | **Strong** |
| Detect fabricated citation markers | Output validation and deterministic Deep review | **Strong** |
| Human-readable sources | Filenames are resolved for document citations; web sources retain titles/URLs | **Strong** |
| Report artifact | Deep writes Markdown and PDF reports after approval | **Exceeds reference** |
| User edits preserve citation safety | Draft review accepts validated edited draft | **Strong** |
| Chat citation durability | Chat shows web/paper source chips | **Partial** | Chat tool sources are not stored in the same durable canonical citation model |

## 6. Multi-tool routing and autonomy

| Industry expectation | Current implementation | Alignment | Gap | Necessity |
|---|---|---|---|---|
| Common tool registry | Separate document, web, and paper services | **Low** | No unified tool definition, authorization, timeout, result, and telemetry contract | **Conditional** |
| Native model function calling | Generation providers expose capability checks, but Deep does not bind and execute a general tool list | **Absent in Agentic RAG flow** | Tool choice is graph-defined | **Not required now** |
| Select correct source dynamically | Web necessity chooses private-only vs add web; paper suggestions are separately gated | **Partial** | No docs vs SQL vs web vs calculator choice |
| Parallel tool calling | Parallel document task retrieval | **Partial** | Not general multi-tool parallelism |
| Sequential tool reasoning | Gap loop can retrieve, observe review, and retrieve again | **Strong bounded overlap** |
| Tool authorization policy | Web approval, owner scoping, rate limits, paper service authorization | **Strong for current tools** | No reusable side-effect classification because current research tools are read-only |
| Structured tool errors | Task failures become typed `ResearchTaskResult`; web failures become failed synthetic tasks | **Strong** | Not one universal error schema |
| Tool-selection evaluation | Tool metrics count calls/outcomes | **Weak-to-partial** | No labeled tool-selection accuracy benchmark |

**Conclusion:** A general native tool router would add flexibility, but it is not necessary to claim meaningful Agentic RAG alignment. ResearchMind already exercises controlled tool-like actions. Generalization should wait for a concrete need such as SQL analytics, calculators, code execution, or internal APIs.

## 7. Memory and state management

| Reference capability | Current implementation | Alignment | Gap or qualification |
|---|---|---|---|
| Per-run short-term state | Typed `MultiWaveResearchState` | **Strong** |
| Retry/loop counters | Wave index, synthesis revisions, gap count, web count, plan version | **Strong** |
| Persistent checkpoint | `AsyncPostgresSaver` keyed by graph thread/run | **Strong** |
| Resume after human decision | LangGraph `interrupt()` and `Command` resume through durable dispatch | **Strong** |
| Survive process restarts | PostgreSQL checkpoints, durable run/dispatch/event records | **Strong** |
| Conversation history | PostgreSQL conversation/message/research session persistence | **Strong** |
| Long-term memory | Session, semantic, user, and research memory services | **Strong** |
| Memory retrieval into planning | Proposal planner receives formatted memory context | **Strong** |
| Memory retrieval into synthesis/retrieval | Memory is used in the user-facing research prompt and planning context | **Partial** | Deep task retrieval itself uses task questions, not direct memory-conditioned rewriting |
| Memory write after success | Session state/raw turn and durable memory extraction | **Strong** |
| State size discipline | Graph stores compact evidence excerpts and artifact references rather than full raw documents | **Strong production practice** |

## 8. Ambiguity handling

| Industry expectation | Current implementation | Alignment | Gap |
|---|---|---|---|
| Detect vague or underspecified requests | Planner may rewrite/interpret the goal; memory helps pronoun resolution | **Partial** | No explicit ambiguity classifier |
| Ask a clarification question | User can reject/edit proposals and plans | **Conceptual overlap** | No `CLARIFY` route that returns a focused question before retrieval |
| Avoid confident guessing | Guardrails and review reduce unsupported output | **Partial** | System can still retrieve against the wrong interpretation |
| Use history to resolve references | Transcript and session-state memory are injected; paper query extraction uses conversation context | **Strong partial** | Linear document query is not explicitly condensed |
| Measure clarification quality | No dedicated evaluation | **Absent** |

**Priority:** A clarification route is high value for the future shared router, but it does not need to block the current Deep workflow because proposal and plan review already give users correction opportunities.

## 9. Error handling, fallbacks, and loop safety

| Failure mode from reference | Current implementation | Alignment | Gap or qualification |
|---|---|---|---|
| Empty retrieval | Deep task can complete with zero evidence and later fail/review; Linear builds context from the result | **Partial** | No immediate canonical `NO_RESULTS` correction in Linear |
| Retrieval exception | Deep converts it to a typed failed task; Linear returns an error | **Strong for Deep** | Linear has no alternate source |
| Web timeout | Configured HTTP timeout and failure normalization | **Strong** |
| MCP timeout | Configured client timeout plus `asyncio.wait_for` in Deep suggestions | **Strong** |
| LLM/provider failure | Routing fallback chain for non-streaming generation; classified failure and metrics | **Strong** |
| Streaming provider failure | Emits canonical ERROR; no unsafe mid-stream provider switch | **Strong** |
| Infinite loop | Review caps, graph recursion limit, web-call limit, duration timeout, task limits | **Strong** |
| Excess cost | Complexity budgets, usage accounting, rate limits, queue capacity, estimated-cost checks | **Strong** |
| Cancellation | Durable cancellation request checked by execution/graph and terminal cancellation state | **Strong** |
| Worker crash/stale session | Durable dispatch lease/checkpoint plus explicit refresh/rollback protections | **Strong** |
| Approval never arrives | Periodic stale-approval expiry sweep | **Strong** |
| Total research failure | Durable FAILED state and event | **Strong** | A standardized user-facing “insufficient evidence” result could be clearer than generic failure |
| Partial task failure | Evidence bundle counts failures; report can finalize with limitations | **Strong** |

## 10. Caching, cost, and latency

| Reference optimization | Current implementation | Alignment | Gap or qualification |
|---|---|---|---|
| Query embedding cache | Valkey-backed query-embedding cache | **Strong** |
| Document embedding cache | Embedding cache | **Strong** |
| Retrieval-result cache | No active end-to-end retrieved-chunk result cache identified | **Weak** | Query embeddings are cached, but Qdrant search/context work still runs |
| Decision cache | Planner/reviewer/web-necessity use policies designed to avoid unsafe cross-run reuse | **Intentional non-alignment** | No route/grade decision cache; correctness is prioritized |
| Exact LLM response cache | Generation exact cache | **Strong** |
| Semantic LLM response cache | Generation semantic cache | **Strong** |
| Session cache | Generation session cache | **Strong** |
| Paper-search cache | Valkey paper-result cache | **Strong** |
| Web-search cache | No equivalent web-result cache identified | **Weak** | May be appropriate because freshness is a web-search reason |
| Cheap model for classification | Web necessity selects a cheap configured provider/fallback classification route | **Strong** |
| Expensive model only where useful | Model routing catalog and runtime strategies exist | **Partial-to-strong** | Planner/reviewer/synthesis selection is configurable rather than a universally enforced tier rule |
| Hard retry caps | Enforced throughout Deep and generation | **Strong** |
| Avoid agentic path for simple queries | Separate Chat and Linear paths; escalation is advisory | **Strong product alignment** |
| Per-call cost accounting | Generation usage table and conversation/run cost lookup | **Strong** |
| Budget-aware loop routing | Review checks estimated cost before additional work | **Strong** |

**Important:** The absence of caching for synthesis/review is deliberate. Those outputs depend on run-specific evidence, so semantic reuse could cause cross-run grounding errors.

## 11. Streaming and user experience

| Reference expectation | Current implementation | Alignment | Gap or qualification |
|---|---|---|---|
| Stream intermediate progress | Deep event journal exposes planner, retrieval, evidence, synthesis, review, approval, report, web, and paper events over SSE | **Strong** |
| Replay events after refresh | Run events are durable and replayed before tailing | **Strong** |
| Show approval state | Plan, web, and report review UIs are implemented | **Strong** |
| Stream final answer tokens | Chat and Linear Research stream tokens | **Strong** |
| Deep report token streaming | Deep shows phase progress and later the draft/report | **Partial** | Synthesis tokens are not streamed as the final report is being created |
| Preserve state after page refresh | Conversation replay reconstructs Deep state | **Strong** |
| Cancel long run | Cancellation endpoint and lifecycle support | **Strong** |
| Explain limitations | Review limitations are included in the draft/report state | **Strong** |
| Expose tool/evidence rationale | Web-search reason and progress are visible | **Partial-to-strong** | Full route/review rationale is not uniformly presented to the user |

## 12. Security alignment

| Industry security expectation | Current implementation | Alignment | Gap or qualification |
|---|---|---|---|
| Treat retrieved text as untrusted | Retrieval-stage context sanitization and prompt-injection detection | **Strong** |
| Detect suspicious patterns | Rule-based chunk guardrails mark suspicious/malicious chunks and reasons | **Strong** |
| Remove/block malicious context | Context guardrail pipeline filters chunks; platform guardrails may block retrieval | **Strong** |
| Input prompt-injection checks | Input guardrail registry includes prompt-injection detection | **Strong** |
| Source trust | Trust registry and low-trust warnings | **Partial-to-strong** | Current document chunks default to user-document source type; mixed web evidence is handled separately |
| Owner isolation | Authenticated owner ID overrides request filters; retrieval is owner-scoped | **Strong** |
| Human approval for consequential actions | Proposal, plan, web, and report approvals | **Strong** |
| Limit tool autonomy | Current tools are read-only and graph-controlled | **Strong by design** |
| Side-effect tool policy | Runtime tool-policy guardrail foundation exists | **Conceptual/forward-looking** | No active side-effecting Agentic RAG tools currently require a mature permission matrix |
| Prevent tool-call injection from web evidence | Web evidence is normalized as data and tool selection is not native/open-ended | **Strong architectural mitigation** | If native tools are added, explicit data/instruction separation and tool-call authorization must be revalidated |
| Audit actions | Events, artifacts, usage, decisions, and logs provide substantial auditability | **Strong** |

## 13. Agentic RAG evaluation metrics

### Reference metrics versus current coverage

| Metric from reference | Current coverage | Alignment | Gap |
|---|---|---|---|
| Routing accuracy | Escalation/planner decisions are produced and logged | **Weak** | No labeled expected-route dataset or accuracy calculation |
| Retry efficiency | Revision/gap counts and outcomes are recorded | **Partial** | No metric proving whether each retry improved evidence or answer quality |
| Over-retrieval rate | Task counts, retrieval metrics, and costs are available | **Weak** | No definition or labeled measure of unnecessary retrieval |
| Under-retrieval rate | Review gaps/failures can be observed | **Partial** | No first-class under-retrieval metric across queries |
| Tool-selection accuracy | Web decisions and tool outcomes are observable | **Weak** | No expected-tool labels or confusion matrix |
| Standard retrieval quality | Retrieval benchmarks and evaluation documentation exist | **Strong foundation** | Must be connected to graph/path-specific evaluations |
| Answer groundedness | Hallucination, citation, faithfulness, and review signals exist | **Strong** | Need calibrated end-user quality thresholds |
| Cost per successful answer | Usage and estimated cost are persisted | **Strong foundation** | Success/quality should be joined with cost in agentic evaluation reports |
| Latency by path | Metrics/events capture stage and generation timing | **Partial-to-strong** | A single query-level critical-path breakdown should be standardized |
| Human approval burden | Approval events are persisted | **Weak** | No rate/time-to-decision or abandonment metric |
| Recovery success | Run failures and retries are tracked | **Partial** | No formal recovery-rate KPI |

### Recommended evaluation suite

| Evaluation family | Suggested cases | Primary metrics |
|---|---|---|
| Route selection | Direct conversational, document factual, current web, complex multi-hop, ambiguous | Route accuracy, clarification accuracy, over/under-retrieval |
| Planning | Simple, moderate, complex, dependent, cyclic/adversarial | Task precision, dependency validity, unnecessary-task rate |
| Tool/source selection | Private-only, web-required, mixed, unavailable tool | Tool accuracy, fallback utility, cost, latency |
| Evidence grading | Relevant, irrelevant, ambiguous, incomplete, stale | Grade accuracy, calibration, false accept/reject |
| Correction | Failed local retrieval, missing subtopic, unsupported citation | Recovery rate, answer improvement, added cost |
| Reflection | Supported, fabricated citation, unsupported claim, incomplete answer | Defect detection, false positives, successful repair |
| Loop control | Repeated failure, costly search, slow provider | Cap compliance, timeout behavior, terminal correctness |
| Security | Prompt injection in document/web evidence, owner-crossing filters, tool-instruction injection | Attack block rate, false positive rate, unauthorized action count |
| Memory | Pronouns, follow-ups, conflicting old/new facts | Resolution accuracy, stale-memory influence, owner/session isolation |
| UX | Refresh during pause, rejection, edit, cancellation, long silence | State recovery, event completeness, abandonment, time to completion |

## 14. Observability and tracing

| Reference expectation | Current implementation | Alignment | Gap |
|---|---|---|---|
| Log every graph step | Research event journal records major lifecycle phases and decisions | **Strong partial** | Not every internal node/state delta is guaranteed as a durable event |
| Visualize full graph execution | LangGraph defines the graph; LangSmith traces generation calls | **Partial** | No single correlated trace tree visibly contains every graph node, tool call, transition, and generation child |
| Capture route taken | Run status, phase, decisions, and events | **Strong** |
| Capture query used | Original query, plan, task questions, web suggestion/query are persisted across models/artifacts/state | **Strong** |
| Capture retrieved evidence | Evidence artifacts and task results | **Strong** |
| Capture retry counts | Synthesis revision, gap research, web count, dispatch attempts | **Strong** |
| Capture grading/reflection verdict | Review decision and web necessity are recorded | **Strong partial** | Standardized retrieval-grade artifact is missing |
| Correlate request/run/trace | Request IDs, run IDs, session IDs, owner IDs, generation trace IDs | **Strong foundation** | Cross-system correlation should be verified in one operator workflow |
| Metrics and dashboards | Prometheus/Grafana dashboards for generation, research, tools, memory, and platform health | **Strong** |
| Immutable execution artifacts | Generation, streaming, conversation, evidence, review, report, and observability artifacts | **Strong** |

## 15. Production deployment checklist assessment

| Checklist item from reference | Status | Evidence in current implementation | Remaining concern |
|---|---|---|---|
| Retry limits on every loop | **Aligned** | Complexity review caps, generation regeneration caps, web-call cap, recursion limit | Continue verifying every future tool/loop adopts the same policy |
| Timeouts on every tool call | **Mostly aligned** | Tavily, MCP, full graph duration, dispatch lease | Canonical document Qdrant/Voyage operations rely on client/service configuration; verify explicit end-to-end deadlines |
| Fallback response for total failure | **Partial** | Failed/limited/cancelled lifecycle outcomes; partial failure limitations | Standardize user-facing insufficient-evidence response across Linear and Deep |
| Logging/tracing for every graph run | **Mostly aligned** | Event journal, structured logs, artifacts, metrics | Full node-level correlated trace remains incomplete |
| Caching repeated queries/decisions | **Partial** | Generation, embeddings, paper cache | Decisions intentionally not cached; retrieval-result and web caches absent |
| Cheap model for route/grade | **Aligned for web decision** | Cheap-provider logic and classification strategy | Standardize tier policy for future shared router/grader |
| Guardrails against retrieved prompt injection | **Aligned** | Context sanitization plus retrieval and input guardrails | Continuously red-team web evidence and future native tools |
| Evaluation suite on regular schedule | **Partial** | Large test suite and offline benchmark foundations | Agent-specific metrics and an automated schedule are not evident |

## 16. Common-pitfall assessment

| Common pitfall | ResearchMind status | Finding |
|---|---|---|
| No retry cap | **Avoided** | Multiple independent caps prevent runaway loops |
| Vague tool descriptions | **Not currently applicable to native tools** | Tools are service/node controlled; future tool definitions will need precise descriptions |
| Expensive model for every node | **Partially avoided** | Cheap web-decision provider and routing strategies exist |
| Trust retrieved content as instructions | **Avoided** | Retrieval sanitization and prompt-injection guardrails treat context as untrusted |
| Do not log intermediate steps | **Largely avoided** | Durable events, logs, artifacts, and counters exist |
| Go agentic for every query | **Avoided** | Chat, Linear, and Deep are separate cost/capability paths |
| Let LLM decide when to stop | **Avoided** | Deterministic budgets and graph bounds control stopping |
| Retry identical failed action blindly | **Mostly avoided** | Revisions carry feedback; gaps create new questions; provider routing can fall back |
| Hide partial failure | **Avoided in Deep** | Failed task counts and report limitations are carried forward |
| Add multi-agent complexity prematurely | **Avoided intentionally** | ADR-033 requires measurable justification |

## 17. Gap prioritization: what matters versus what is optional

### Essential or high-value gaps

| Priority | Gap | Why it matters | Suggested direction |
|---|---|---|---|
| P0 | No shared retrieval adequacy grader | Central missing link for CRAG behavior and safe Linear fallback | Typed `EvidenceGrade` with relevance, sufficiency, freshness, confidence, reasons, and next action |
| P0 | Linear Research cannot correct weak/empty retrieval | Fast product path can still answer from poor context or fail without alternative | Query rewrite/broaden -> re-retrieve -> optional web suggestion -> abstain |
| P1 | No shared adaptive/clarify router | Users must understand product modes; ambiguous queries can be misinterpreted | Advisory `DIRECT / LINEAR / DEEP / WEB / CLARIFY` result with consent-aware routing |
| P1 | Agent-specific evaluation is incomplete | Cannot prove that agent loops improve quality enough to justify cost | Add route, grade, tool, retry, over/under-retrieval, recovery, and approval metrics |
| P1 | Full graph trace is fragmented | Debugging spans event journal, artifacts, logs, and generation traces | Correlate all nodes/tool calls/decisions into one run trace |
| P1 | Streaming verification is post-delivery | Bad streamed content cannot be retracted | Buffer high-risk paths or label streamed content provisional until verified |
| P2 | Explicit ambiguity handling is missing | Wrong interpretation can poison all downstream retrieval | Add a `CLARIFY` branch before expensive work |
| P2 | Uniform trust grading across private and web evidence | Mixed-source synthesis needs consistent provenance policy | Shared evidence envelope with source trust, freshness, and sanitization metadata |

### Conditional capabilities—not mandatory now

| Capability | Current status | Implement only when |
|---|---|---|
| Retrieval exposed as native LLM tool | Not implemented | Tool choice becomes too varied for explicit graph routing |
| General multi-tool registry | Not implemented | SQL, calculation, code, or internal APIs become real product requirements |
| Open-ended ReAct loop | Not implemented | Benchmarks show bounded nodes cannot solve required tasks |
| Full dynamic replanning | Partial targeted gap plan | Complex investigations repeatedly need material DAG changes |
| Mid-generation Self-RAG reflection tokens | Not implemented | Evidence shows post-draft review is too late or inefficient |
| Multi-agent supervisor and specialists | Not implemented by design | Domain specialization or independent verification produces measurable gains |
| Decision caching | Not implemented | Stable decision accuracy and safe cache scoping are demonstrated |
| Web-result caching | Not implemented | Freshness semantics and invalidation rules are defined |

## 18. Recommended industry-aligned target

ResearchMind does not need to replace its Deep graph with a generic agent. The most effective target is an incremental hybrid:

| Stage | Keep from current system | Add or standardize |
|---|---|---|
| 1. Characterize query | Conversation/memory context, Deep planner | Shared intent/complexity/freshness/ambiguity router |
| 2. Obtain consent | Existing mode selection and approval checkpoints | Convert automatic expensive/external routes into recommendations when appropriate |
| 3. Rewrite/decompose | Deep rewritten goal and tasks | Lightweight query condensation for Linear follow-ups |
| 4. Retrieve | Hybrid Qdrant, RRF, rerank, context pipeline | Optional query-conditioned fusion policy only if benchmarks support it |
| 5. Grade | Deep web necessity, trust, context statistics | Reusable evidence-grade contract across Linear and Deep |
| 6. Correct | Deep document/web gap retrieval | Linear retry, web suggestion, and explicit abstention |
| 7. Generate | Shared Generation Runtime | Maintain evidence/source envelope through all paths |
| 8. Reflect | Deep review and runtime validation | Consistent verified/limited/failed outcome across surfaces |
| 9. Control | Existing budgets, checkpoints, approvals | Apply common policy interfaces to every future tool |
| 10. Evaluate | Existing benchmarks, metrics, artifacts | Agentic path/decision/recovery quality suite |
| 11. Observe | Events, logs, traces, artifacts | One correlated graph-run trace |

## 19. Final standards assessment

| Industry-standard area | Final verdict |
|---|---|
| Planning and multi-hop decomposition | **Industry-aligned and strong** |
| Hybrid document retrieval | **Industry-aligned and stronger than the reference baseline** |
| Evidence grading | **Partially aligned; needs a reusable contract** |
| Corrective fallback | **Industry-aligned in Deep, missing in Linear** |
| Self-reflection | **Strong post-draft implementation; not token-level Self-RAG** |
| ReAct loop | **Bounded ReAct-like workflow, not general ReAct agent** |
| Adaptive routing | **Product-level paths exist; global router missing** |
| Query reformulation | **Strong in Deep planning, incomplete in Linear** |
| Citations and provenance | **Strong** |
| Memory and persistent state | **Strong** |
| Error handling and loop bounds | **Strong production alignment** |
| Cost controls | **Strong** |
| Security | **Strong for current read-only tools and controlled graph** |
| Streaming UX | **Strong** |
| Evaluation | **General foundations strong; agent-specific coverage weak** |
| Observability | **Substantial, but full graph correlation is incomplete** |
| Native multi-tool autonomy | **Limited; not required for current scope** |
| Multi-agent architecture | **Intentionally absent and not a maturity gap** |

The platform covers the important Agentic RAG fundamentals: controlled planning, multi-step retrieval, evidence aggregation, correction, reflection, citations, state, memory, human control, limits, and observability. Its largest maturity opportunity is not “more autonomy.” It is making routing, grading, correction, evaluation, and tracing consistent across the existing bounded paths.

## 20. Principal code references

| Concern | Primary implementation |
|---|---|
| Deep proposal and complexity planning | `apps/api/app/ai/runtime/research/proposal_service.py`, `apps/api/app/ai/runtime/research/planner/` |
| Plan validation and dependency waves | `apps/api/app/ai/runtime/research/decomposition/` |
| Multi-wave loop and conditional routing | `apps/api/app/ai/runtime/research/workflows/multi_wave_research.py` |
| Per-task document retrieval | `apps/api/app/ai/runtime/research/retrieval/service.py` |
| Hybrid retrieval and reranking | `apps/api/app/ai/knowledge/retrieval/service.py` |
| Context optimization and citations | `apps/api/app/ai/knowledge/context/service.py` |
| Evidence aggregation | `apps/api/app/ai/runtime/research/evidence.py` |
| Corrective web decision | `apps/api/app/ai/runtime/research/web_search/necessity.py` |
| Tavily and MCP tools | `apps/api/app/ai/tools/web_search/`, `apps/api/app/ai/tools/paper_search/` |
| Synthesis and reflection/review | `apps/api/app/ai/runtime/research/synthesis/`, `apps/api/app/ai/runtime/research/review.py` |
| Persistent execution and resume | `apps/api/app/ai/runtime/research/execution.py`, `apps/api/app/ai/runtime/research/checkpointing.py` |
| Durable run events | `apps/api/app/ai/runtime/research/event_journal.py`, `apps/api/app/ai/runtime/research/events.py` |
| Research worker and dispatch | `apps/worker/research_runtime_worker.py`, `apps/api/app/repositories/research_run_dispatch.py` |
| Memory | `apps/api/app/ai/memory/` |
| Generation routing/caching/validation | `apps/api/app/ai/runtime/generation/` |
| Prompt-injection and retrieval safety | `apps/api/app/ai/guardrails/`, `apps/api/app/ai/knowledge/context/guardrails/` |
| Metrics, artifacts, and tracing | `apps/api/app/ai/observability/`, `apps/api/app/ai/artifacts/`, `apps/api/app/infrastructure/metrics/` |
| Frontend Deep progress and approvals | `apps/web/src/features/research/use-deep-research.ts`, `apps/web/src/features/research/components/` |
| Single-agent architecture decision | `docs/adrs/ADR-033-Decision Framework for Single-Agent vs Multi-Agent Architectures.md` |

