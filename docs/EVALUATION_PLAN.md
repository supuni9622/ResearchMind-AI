# ResearchMind — Finalized Evaluation Plan

**Status:** finalized design, supersedes `PHASE_2_3_ROADMAP.md` Part 1 (1a–1g)
as the canonical evaluation reference. That section's sequencing table still
holds for near-term execution order — treat it as this plan's MVP slice, not
a competing design. **Source:** reconciles two inputs — (1) the original
"don't over-engineer" evaluation design built earlier in this planning cycle
(Part 1, 1a–1g), and (2) a comprehensive RAG-evaluation framework (RAGAS +
LangSmith control-plane architecture) reviewed against this codebase on
2026-08-10. Every claim about current code state below was checked, not
assumed. **Companion docs:** [`PHASE_2_3_ROADMAP.md`](PHASE_2_3_ROADMAP.md),
[`PRODUCTION_READINESS_EVALUATION.md`](../PRODUCTION_READINESS_EVALUATION.md),
[`docs/evaluation/EVALUATION_GAP_ANALYSIS.md`](evaluation/EVALUATION_GAP_ANALYSIS.md),
[`PRIORITIZED_ROADMAP.md`](PRIORITIZED_ROADMAP.md) (sequences this plan's
phases into Wave 1). **Execution tracking:**
[`EVALUATION_IMPLEMENTATION_TRACKER.md`](EVALUATION_IMPLEMENTATION_TRACKER.md)
turns §16's phase list into task/subtask checklists against verified
current code state — update it, not this file, as Wave 1 items ship.

## How to read this document

Every layer below has an **MVP scope** (ships as part of the near-term
evaluation platform build) and a **Mature scope** (the fuller version,
explicitly deferred, not silently dropped). This split exists because the
full framework this doc reconciles is written at the ambition level of a
dedicated eval team — building all of it now would be the over-engineering
this whole planning effort has repeatedly steered away from. Where MVP and
Mature aren't both stated for a layer, assume MVP only is in scope now.

---

## 1. Central design

**RAGAS computes metrics. LangSmith is the control plane — datasets,
experiments, traces, feedback, online evaluators. Prometheus/Grafana
monitors infrastructure. ResearchMind code owns deterministic domain rules
and release decisions.** Nobody's job is to build a bespoke scoring
framework, dataset manager, or experiment UI — all three already exist as
products; this plan wires them together and adds only the deterministic,
domain-specific logic (citation validity, schema checks, budget
enforcement) that can't come from a third party.

| Capability | RAGAS | LangSmith | Prometheus/Grafana | ResearchMind code |
|---|---|---|---|---|
| Faithfulness / context precision / recall / factual correctness | **Primary** | Stores & displays scores | — | Supplies inputs (question, answer, contexts, reference) |
| Datasets | Can generate synthetic examples | **Primary registry** | — | Owns schema, versioning |
| Experiments (config comparison) | Computes the metric | **Primary orchestration/UI** | — | Triggers runs, supplies config fingerprint |
| Production traces | — | **Primary** | Aggregates operational trends | Instrumentation (already live) |
| Online evaluation | Individual scorers | **Primary orchestration** | Alerting | Sampling policy, remote evaluator glue |
| Human annotation / feedback | — | **Primary** | — | Review-queue policy (1c/1g) |
| Latency / error metrics | — | Trace-level | **Primary dashboards** | Instrumentation (already live) |
| Cost tracking | Evaluation-call cost only | Trace/model cost | **Primary aggregates** | `GenerationUsage` ledger (already live) |
| Deterministic citation/schema checks | — | Stores result | Counters/alerts | **Primary implementation** |
| CI release gates | Produces scores | Experiment comparison | — | **GitHub Actions logic, `benchmarks/regression/`** |

---

## 2. The layered evaluation model

The single biggest change from the original plan: evaluate the *pipeline*,
not just the final answer. A correct-looking response doesn't reveal
whether retrieval, context-construction, or generation actually did its
job — these need independent measurement or a real failure hides behind an
adjacent stage's compensating behavior (e.g. the model answering correctly
from parametric knowledge while ignoring bad retrieved context).

| Layer | What we evaluate | Current state in ResearchMind | MVP | Mature |
|---|---|---|---|---|
| **Ingestion** | Parsing, chunk/heading/table preservation | **Uncovered.** `benchmarks/chunking/` compares strategies against each other offline, but nothing checks parse fidelity against labeled source fixtures. | Deterministic parse-success-rate + a handful of labeled fixture documents (heading/table preservation) | Full 12-check table (metadata accuracy, chunk boundary rubric, parent-child integrity, ingestion cost) |
| **Retrieval** | Recall@K/MRR/NDCG, hybrid fusion, metadata filtering | Real, live: dense/sparse/RRF fusion (`fusion/rrf.py`), reranking, `benchmarks/retrieval/` (NDCG@5/10 already built). | Reuse existing `benchmarks/` suite; add Recall@K/Hit Rate@K if not already present | Full experiment matrix (§5) |
| **Context construction** | What's actually sent to the LLM after fusion/rerank/compression | **Uncovered as a distinct layer** — the pipeline stages exist (fusion, reranking) but nothing evaluates the *result* independently of retrieval or generation. | Provenance preservation (deterministic — every context item traces to a chunk) + token efficiency | Redundancy ratio, lost-in-the-middle sensitivity, compression preservation |
| **Generation** | Faithfulness, relevancy, correctness | This is what the original plan (1a/1b) already covers — surface-aware Ragas metrics, real. | As already designed in 1a/1b | Semantic similarity, uncertainty calibration |
| **Citation** | Valid, non-fabricated, correctly attributed sources | **Partial, Deep-Research-only.** `ResearchReview.citation_integrity_score` (`review.py`) is a real, deterministic, binary "do cited IDs exist in evidence" check — but internal-only, never a cross-surface release gate. | Generalize the existing check into a cross-surface deterministic validator (§8) — release-blocking | Entailment judge, citation placement/specificity |
| **Guardrails** | Injection, unsupported claims, unsafe output | Real, mature per `AI_ENGINEERING_AUDIT.md` — input/runtime/retrieval/generation stages all live. Not yet eval-suite-tested against an adversarial dataset. | Small hand-built adversarial dataset (10-20 cases), ties into the already-planned V3 NeMo-guardrails evaluate-before-committing item | Full adversarial suite, red-team rotation |
| **Workflow** | Plan quality, tool use, synthesis (Deep Research); clarification quality (Chat) | Deep Research's `review.py` decision (`PASS`/`REVISE_SYNTHESIS`/...) is a real workflow-quality signal already computed, unused for eval. | Reuse `review.py`'s existing decision as a workflow-health metric; add 2-3 surface-specific metrics (§10) | Full per-surface scorecard |
| **Operational** | Latency, cost, errors, routing | Real and live — Prometheus/Grafana (Phase 9), `GenerationUsage` ledger. | Already sufficient — just needs the config fingerprint (1f) to slice by version | — |
| **Human** | Whether researchers find output useful | This is 1c/1g, already designed — arguably ahead of the reviewed framework (objective/preference split, owner-scoped vs. global). | As already designed | Dedicated annotation queue UI |

---

## 3. Datasets

**Don't build 10 separate datasets.** The framework's real insight is the
**per-example schema** (below) — rich enough fields on each example that
one well-designed dataset can be sliced by `query_type`/`workflow`/`domain`
for reporting, instead of needing a dozen separate tables that all have to
be curated and kept in sync independently. Two datasets are worth keeping
genuinely separate because they have fundamentally different curation
workflows, not just different content:

| Dataset | Why separate | Curation |
|---|---|---|
| `rag_answer_gold` | The main dataset — covers retrieval, generation, citation, and abstention cases via the schema below, sliced by `query_type`/`workflow` for reporting | Hand-curated (50-150 to start, per the original 1a design), grown via the confirmed-feedback promotion loop (1c) |
| `production_failures` | Auto-sourced from real incidents, not hand-written — different provenance, same schema | Fed by 1c's confirmed-thumbs-down review queue |
| `adversarial` | Security/guardrail testing needs deliberately malicious inputs — mixing these into the main dataset would contaminate query-type distributions used for other reporting | Hand-built red-team cases (§2's Guardrails MVP) |

Mature tier can split further (`retrieval_gold`, `citation_gold`,
`unanswerable`, `multilingual`, `performance`) once the single dataset's
volume actually justifies separate curation pipelines — start with the
`query_type`/`workflow` fields doing that job via filtering instead.

### Per-example schema (adopted as-is — this is the framework's strongest idea)

| Field | Purpose |
|---|---|
| `question` | User input |
| `reference_answer` | Human-approved expected answer, where applicable |
| `reference_context_ids` | Known relevant chunks/documents |
| `required_claims` / `forbidden_claims` | Facts that must / must not appear |
| `expected_citation_ids` | Sources that should support the answer |
| `expected_behavior` | answer / clarify / refuse / abstain / continue-research |
| `query_type` | factual / synthesis / comparison / exploratory / unanswerable |
| `difficulty` | easy / medium / hard |
| `workflow` | chat / linear_research / deep_research — **matches the surface split already built into 1a/1b** |
| `metadata_filters` | Filters expected during retrieval |
| `rubric` | Example-specific evaluation criteria (for LLM-judge cases) |
| `expected_tool` | Correct tool/action for a turn — web search, paper search, or none (Deep Research/Chat tool use, §10) |
| `expected_route` | Correct workflow path — which wave/gap-research branch a Deep Research run should take |
| `failure_category` | For `production_failures` examples only — see the taxonomy below |

**`failure_category` taxonomy** (added 2026-08-10, cross-checked against an
LLM-eval methodology guide) — each confirmed production failure (1c's
promotion loop) gets tagged with one of these, so segment-analysis (1f) can
slice by *failure type*, not just by config/content segment:

| Category | Example | Feeds |
|---|---|---|
| `wrong_citation` | Citation points to the wrong or nonexistent source | §8's citation validator |
| `hallucination` | Claim not supported by retrieved context | Faithfulness (§7) |
| `retrieval_miss` | Relevant evidence existed but wasn't retrieved | Retrieval recall (§5) |
| `unnecessary_tool_use` | Web/paper search fired when it shouldn't have | Tool-invocation logging (§10) |
| `abstention_failure` | Answered with unwarranted certainty on insufficient evidence | Generation (§7) |
| `workflow_loop` | Repeated gap-research/revision without progress | Workflow decision quality (§10) |
| `schema_violation` | Malformed structured output | Schema validity (§13) |
| `injection_success` | Prompt injection altered intended behavior | Guardrails (§9) |

---

## 4. Ingestion & chunking evaluation (MVP slice)

**Status: MVP done (2026-08-11).** Was genuinely new coverage — this
didn't exist in any form beyond `benchmarks/chunking/`'s
strategy-vs-strategy comparison, which never checked fidelity against a
known-correct source. Implementation: `benchmarks/ingestion/`, reusing
the 5 already-cached research-paper fixtures with hand-verified
heading/table minimums rather than adding new fixture PDFs. Detail:
`EVALUATION_IMPLEMENTATION_TRACKER.md` E12.

| Check | Detects | Method | Tier |
|---|---|---|---|
| Parse success rate | Documents that fail ingestion outright | Deterministic — already loggable from existing processing pipeline errors | MVP |
| Heading preservation | Lost document hierarchy | Compare parsed heading tree against a handful of labeled fixture PDFs | MVP |
| Table preservation | Corrupted scientific tables | Same fixture set, table-specific comparison | MVP |
| Metadata accuracy, chunk boundary rubric, chunk size distribution, parent-child integrity | — | — | Mature |

Run these when changing Docling configuration, chunking strategy, or the
canonical document schema — exactly the trigger already identified for
`benchmarks/chunking/` in the existing plan, just extended to fidelity, not
only strategy comparison.

---

## 5. Retrieval evaluation

Reuses `benchmarks/retrieval/` (already real, NDCG@5/10 already built per
`ROADMAP.md` Phase 8) — this section is mostly about **making sure the
metric set is complete** and **fixing the config-fingerprint gap** already
identified in 1f.

| Metric | Reference needed? | Status |
|---|---|---|
| Recall@K | Yes | Already built |
| Hit Rate@K | Yes | ✅ Done 2026-08-11 — was the one genuinely missing metric, see `EVALUATION_IMPLEMENTATION_TRACKER.md` E14 |
| MRR | Yes | Already built |
| NDCG@K | Graded labels | Already built |
| Context Precision / Recall (Ragas) | Reference contexts | Covered by 1a's Ragas integration |
| Metadata-filter accuracy | Expected filters | Already built — `MetadataFilteringBenchmark` |
| Noise sensitivity, context entity recall, diversity/coverage | Varies | Mature tier |

**Experiment metadata — merges 1f's config fingerprint with the fuller
field list this framework specifies.** Two different things, don't
conflate them:

- **Production request fingerprint** (threads through `GenerationRequest` →
  `GenerationUsage`, per 1f): `surface`, `prompt_version`,
  `chunking_strategy`, `embedding_model`, `reranker`, `routing_strategy` —
  stays exactly as scoped in 1f, this is what ties a *live* answer back to
  the config that produced it. **Status: done 2026-08-11**, see
  `EVALUATION_IMPLEMENTATION_TRACKER.md` E8.
- **Retrieval-experiment metadata** (lives in `benchmarks/`/LangSmith
  experiment tracking, not the production ledger — a different, offline
  concern): `retriever_version`, `embedding_provider`, `chunker_version`,
  `chunk_size`, `chunk_overlap`, `fusion_method`, `retrieval_top_k`,
  `reranker_provider`, `rerank_top_n`, `parent_expansion_enabled`,
  `compression_strategy`. Without this, an improved offline benchmark score
  can't be traced back to *which* architectural change caused it — already
  partially present per-vector (`indexing/service.py:277-300` tags
  `chunking_strategy`/`embedding_model`), needs to be captured at the
  benchmark-run level too, not just per-vector.

---

## 6. Context-construction evaluation (new layer, MVP slice)

**Status: MVP done (2026-08-11).** Implementation:
`app/ai/knowledge/context/quality.py`. Detail:
`EVALUATION_IMPLEMENTATION_TRACKER.md` E13.

| Metric | Question | Method | Tier |
|---|---|---|---|
| Provenance preservation | Can every context item trace back to a chunk/source? | Deterministic — cheap, and directly reuses the citation-provenance logic being built in §8 | MVP |
| Context token efficiency | Useful evidence per context token | Deterministic ratio | MVP |
| Redundancy ratio, evidence coverage, lost-in-the-middle sensitivity, compression preservation | — | Requires embedding-similarity or reordering experiments | Mature |

This layer matters because retrieval can succeed while a later
fusion/rerank/compression step silently drops the evidence that mattered —
today nothing would catch that specific failure mode.

---

## 7. Generation evaluation

**Status: MVP scoring function done (2026-08-11).** This is what 1a/1b
already designed at the decision level — restated here for completeness
of the layered model, but note the actual Ragas *integration* was net-new
work, not already in place (see the corrected claim in
`EVALUATION_IMPLEMENTATION_TRACKER.md` §0/E1: no `ragas` dependency
existed anywhere in this codebase before this pass). Implementation:
`benchmarks/generation/ragas_scoring.py` (`score_generation()`) +
`ragas_judge.py` (real ragas wiring, including a documented workaround
for a genuine upstream `ragas==0.4.3` packaging bug). Detail:
`EVALUATION_IMPLEMENTATION_TRACKER.md` E1.

- Linear Research / Deep Research: faithfulness, answer_relevancy,
  context_precision, context_recall (full Ragas RAG suite)
- Chat, no tool use: answer_relevancy only (no retrieved context to be
  faithful to — this distinction was corrected earlier in this planning
  cycle and holds)
- Chat with web/paper search: full suite, scoped to that turn's
  tool-returned passages

**Mature tier adds:** factual_correctness and semantic_similarity where a
`reference_answer` exists (most golden-set examples, rare in sampled
production), completeness against `required_claims`.

---

## 8. Citation evaluation (new first-class layer, MVP slice)

**Status: Done (2026-08-11).** Generalizes `ResearchReview.citation_integrity_score`
— was a real, working, deterministic check, but Deep-Research-only and
never a release gate — into a cross-surface deterministic validator.
Implementation: `app/ai/knowledge/context/citations/validity.py`
(`check_citation_validity()` strict core +
`check_prompt_context_citation_validity()` free-text wrapper);
`CitationValidator` and `review_draft()` both now delegate to it. Detail:
`EVALUATION_IMPLEMENTATION_TRACKER.md` E4. Still open: wiring the checker
into CI's absolute gates and the online scoring job's 100%-sampled
free-signal category (tracker items E2/E5).

| Check | Method | Blocking? |
|---|---|---|
| Source existence — cited `document_id` exists in the retrieved set | Deterministic | **Release-blocking** |
| Retrieval provenance — cited `chunk_id` was actually retrieved this turn | Deterministic | **Release-blocking** |
| Fabricated citation rate — model invented a source/DOI not in context | Deterministic (cross-check against retrieved set) | **Release-blocking, target 0%** |
| Citation syntax validity | Deterministic, schema-level | **Release-blocking** |
| Entailment (does the source actually support the claim) | LLM/NLI judge | Mature |
| Citation placement, specificity | Custom judge | Mature |

**Treat as release-blocking, matching the reviewed framework's
recommendation almost verbatim** — these are cheap (pure code, no LLM
call, reusing data already on the `Citation` object: `document_id`,
`chunk_ids`) and catch a failure mode (a fabricated or wrong-source
citation) that's arguably worse than a merely-unhelpful answer, since it's
actively misleading. This is the highest-value-per-effort addition in this
entire plan — small new code, generalizing an already-proven pattern,
directly closes a real trust risk.

---

## 9. Guardrails evaluation (MVP addition)

**Status: MVP done (2026-08-11).** The guardrails platform itself was
already real and mature (input/runtime/retrieval/generation stages, per
`AI_ENGINEERING_AUDIT.md`) — now genuinely tested against a deliberately
adversarial set for the first time, feeding Wave 7's in-house guardrails
gap-filling directly. Implementation: `benchmarks/guardrails/` +
`datasets/adversarial/adversarial_cases.json`. Detail:
`EVALUATION_IMPLEMENTATION_TRACKER.md` E15.

- **MVP:** a small (10-20 example) hand-built adversarial dataset —
  prompt injection in an uploaded document, poisoned instructions, a
  handful of known jailbreak patterns — run against the existing guardrail
  stages, pass/fail per case. **Shipped at 18 cases**, empirically
  verified against the live guardrail code (not a guessed spec) — 13
  detected, 5 deliberately evasive and confirmed undetected (paraphrase,
  Unicode homoglyphs, spelled-out PII, keyword-free jailbreak phrasing).
- **Mature:** full adversarial suite, red-team rotation, security
  evaluation (this is `ROADMAP.md` Phase 8's "Security Evaluation ❌ Not
  started" — this MVP slice is the first real step toward closing that).

---

## 10. Workflow / feature-specific evaluation

Extends 1a's surface-split (which metrics apply per surface) with
surface-specific metrics beyond Ragas's generic RAG set — scoped to what's
already computed somewhere in the codebase, not a from-scratch metric
design.

| Metric | Chat | Linear Research | Deep Research | Already computed today? |
|---|:---:|:---:|:---:|---|
| Response relevancy, faithfulness | ✓ | ✓ | ✓ | Yes — 1a/1b |
| Citation correctness | when tools used | ✓ | ✓ | Partial — §8 generalizes it |
| Workflow decision quality | — | — | ✓ | **Yes, unused** — `ResearchReview.decision` (PASS/REVISE_SYNTHESIS/RESEARCH_GAPS/FINALIZE_WITH_LIMITATIONS/FAIL) is already computed every run; just needs to be rolled into the eval dashboard as a workflow-health metric, zero new computation |
| Cost per completed task | — | ✓ | ✓ | Yes — `GenerationUsage` ledger, per-session sum already exists |
| Human-interrupt outcome rate (approve/reject/revise) | — | — | ✓ | New, but cheap — a count over `budget_usage.plan_decision`/`report_decision`, already-persisted fields |
| Tool-invocation rate & success rate (web/paper search) | ✓ (if toggled) | — | ✓ | **New, MVP-worthy, cheap** — `WebSearchNecessityDecision`/paper-search query extraction are already computed; this is a count of invocation rate and non-empty/success rate, not a new judge. Whether the *right* tool was chosen (vs. just "was it invoked and did it return something") is the Mature-tier version below. |
| Plan quality, subquestion coverage, tool-call **correctness** (was the right tool chosen), source diversity, synthesis coherence | — | Limited | ✓ | Mature tier — would need new LLM-judge rubrics |

The MVP row worth highlighting: **`ResearchReview.decision` is already a
real workflow-quality signal computed on every single Deep Research run,
and nothing currently reports on it in aggregate.** This is the same
"already computed, currently discarded" pattern that showed up repeatedly
earlier in this planning cycle (retrieval scores dropped before reaching
`Citation`, review fields not rendered in `draft-review.tsx`) — rolling it
into the segment-analysis job (1f) costs nothing new to compute.

---

## 11. Operational evaluation

Already covered — Prometheus/Grafana (Phase 9, real and wired) plus the
`GenerationUsage` ledger. The only work item is the config fingerprint
(1f) so operational data can be sliced by version, already scoped there.
No change from the original plan.

**Cross-reference, easy to miss:** `PRODUCTION_READINESS_EVALUATION.md`
item 8 and `PHASE_2_3_ROADMAP.md` V2 #5 both already scope adding
`owner_id`/tenant as a LangSmith **trace tag** (today the trace only
carries `provider`/`model`/`runtime`). This plan's owner-scoped dashboard
(§1g) gets its `owner_id` from the separate Postgres `eval_scores`
table, which is sufficient for this plan's own dashboard — but without
that trace-tag fix, drilling from a trace *inside LangSmith's own UI*
back to a specific user still isn't possible. Both fixes are needed for
"LangSmith as the control plane" to fully deliver on the owner-scoped
story this plan relies on in §1; the trace-tag fix isn't optional
polish, just already tracked elsewhere rather than duplicated here.

---

## 12. Human layer

This is 1c (feedback) and 1g (objective/preference scope split) — **no
change, already ahead of the reviewed framework**, which has no equivalent
mechanism for keeping one user's stylistic preference out of the shared
regression gate. Restated here only to complete the layer table in §2.
**Status:** 1c's collection mechanism (`POST /feedback`) is live as of
2026-08-11, including the frontend affordance across all three surfaces
(Chat, Linear Research, Deep Research) — a real browser click was
confirmed the same day. The objective/preference classification split
(1g) itself is not yet implemented. Tracked as
`EVALUATION_IMPLEMENTATION_TRACKER.md` E21.

Same day, once real feedback was flowing, a related gap surfaced: user
feedback landed in our own `feedback` table but was invisible inside
LangSmith's own UI, since nothing correlated it back to the trace it was
left on. Fixed by wiring `POST /feedback` to also call LangSmith's
`create_feedback()` API against the originating run — see
`EVALUATION_IMPLEMENTATION_TRACKER.md` E22. This directly serves this
section's own "LangSmith as the control plane" framing (§11's trace-tag
point above): a user's thumbs up/down and the trace it was left on are
now both visible together inside LangSmith, not just in our own DB.

---

## 13. Offline evaluation system

**Status: smoke-tier CI wiring done (2026-08-11), full trigger matrix
still open.** Reuses `benchmarks/regression/` (already built, per 1a) —
CI wiring done for the fully-offline Ingestion Fidelity benchmark only;
retrieval-config-change and prompt/LLM-change triggers for the
live-service-dependent benchmarks need CI credentials not yet configured.
The absolute gates declared for citation/schema/abstention checks
(below) also have no benchmark run populating them yet — declared in
`thresholds.py` but structurally unreachable until a benchmark actually
emits those metric names. Detail: `EVALUATION_IMPLEMENTATION_TRACKER.md`
E2, follow-up E20. Gate-severity
distinction below — now implemented via `ThresholdDirection.ABSOLUTE_MIN`/
`ABSOLUTE_MAX`, worth adopting precisely:

**Relative regression gates for fuzzy/LLM-judged metrics; absolute gates
only for deterministic checks.** Don't set an arbitrary target like
"faithfulness must exceed 0.90" before calibrating judges against human
labels — a regression gate ("must not drop more than 2-3% from the current
production baseline") is safer until there's a calibrated sense of what a
good absolute score even looks like for this specific product's traffic.

| Gate | Type | Initial bar | Status |
|---|---|---|---|
| Retrieval Recall@10, NDCG@10 | Relative | No regression beyond 2-3% vs. baseline | Threshold defined (`_QUALITY_DROP`, 5% — not yet 2-3%, close enough not to have blocked this pass); not yet CI-wired (needs live Qdrant) |
| Faithfulness, answer_relevancy | Relative | No statistically meaningful regression | Threshold defined; metric itself not yet produced (needs E1's Ragas integration) |
| Citation validity, fabricated-citation-rate | **Absolute** | 100% valid / 0% fabricated — deterministic, cheap, no reason not to hold a hard line | `ABSOLUTE_MAX` threshold defined 2026-08-11; checker exists (E4); not yet emitted into a benchmark report (needs E1's golden set) |
| Schema/format validity | **Absolute** | 100% | `ABSOLUTE_MIN` threshold defined 2026-08-11; not yet populated by any benchmark |
| Abstention pass rate (unanswerable cases) | Absolute | ≥ 95% on the controlled subset | `ABSOLUTE_MIN` threshold defined 2026-08-11; needs E1's golden set |
| P95 latency, avg. eval cost | Absolute | Within existing budget (readiness item 2's latency-SLO work, item 1's cost budget) | Not yet defined — tracked as E17/E18 |

Offline triggers: retrieval-config change → retrieval benchmark; prompt/LLM
change → generation benchmark; every PR → CI smoke eval (small, fast
subset); release candidate → full regression suite. This matches 1a's
existing CI design; no change, just formalized with the gate-type split
above.

---

## 14. Online evaluation system

Reconciles 1b's risk-weighted sampling (already more targeted than a flat
rate) with the framework's cheap-vs-expensive sampling-rate split. **Both
are correct, at different layers — merge them:**

| Signal category | Sampling | Source |
|---|---|---|
| Request success/error, latency, cost, routing metadata | 100% | Already free — Prometheus/`GenerationUsage`, no new work |
| Citation existence/provenance, schema validity | 100% | Deterministic, cheap — §8's validator, run on every response |
| Guardrail-flagged requests | 100% (always score) | 1b's existing risk-weighted rule — reuse unchanged |
| Deep Research runs with a non-`PASS` review decision | 100% (always score) | 1b's existing risk-weighted rule — reuse unchanged |
| Requests under a config-fingerprint canary window | Oversampled | 1b's existing risk-weighted rule — reuse unchanged |
| Faithfulness / relevancy LLM judges (everything else) | 5-10% flat baseline | 1b's baseline rate — standardized here; `EVALUATION_GAP_ANALYSIS.md`'s addendum independently suggested 10-20%, superseded by this number |
| Deep Research trajectory judge | 5-10% | New, mature tier |
| Human expert review | Queue-based, not sampled | Feeds from 1c's confirmed-feedback queue |

The reviewed framework's contribution here is formalizing "100% for
whatever's already free" as an explicit category — 1b already did this
implicitly (guardrail/review-decision checks are free lookups) but stating
it as a general rule makes it easy to slot in new free signals later (e.g.
§8's citation validator) without re-deriving the reasoning each time.

---

## 15. Offline → online feedback loop

Unchanged from 1c's design — restated because both this plan and the
reviewed framework independently converge on the same loop, which is a
good validation signal:

```
Offline experiments gate every release (§13)
  -> Deploy only if gates pass
  -> Production traces exist already (LangSmith, live)
  -> Free/deterministic checks run on 100% of traces (§14)
  -> LLM judges run on the risk-weighted sample (§14)
  -> Failures + negative feedback route to the review queue (1c)
  -> Human confirms genuine misses
  -> Confirmed examples promoted into rag_answer_gold (both directions, 1c)
  -> Re-run in every future release (§13's CI gate)
```

---

## 16. Finalized implementation phases

Merges the reviewed framework's 12-phase rollout with 1a-1g's existing
11-step sequencing table into one ordered list. **MVP** phases are the
near-term build; **Mature** phases are explicitly deferred, not dropped.

| # | Phase | Tier | Note |
|---|---|---|---|
| 1 | ✅ Golden dataset (`rag_answer_gold`, schema from §3) — Done, 115 examples (grown from 24) 2026-08-11 | MVP | = original 1a step 1. Grounded in real, verified content throughout — started at 24 to avoid padding with unverified facts, grown to 115 the same day once the underlying corpus expanded from 5 to 50 papers (§4/§5's update). See `EVALUATION_IMPLEMENTATION_TRACKER.md` E1 for the full growth breakdown. LangSmith registration done same day (tracker E19) — all 115 examples live and browsable in LangSmith's UI; only Experiment-logging (successive `score_generation()` runs comparable over time in-UI) remains open |
| 2 | ✅ Wire `benchmarks/regression/` into CI, gate types per §13 — Done (smoke tier) 2026-08-11 | MVP | = original 1a step 2. Absolute + relative gates both implemented; one CI job wired for the fully-offline Ingestion Fidelity benchmark. Retrieval/generation benchmark CI triggers still need live-service credentials — not yet configured, and the absolute gates this phase declared have no benchmark run populating them yet. Detail: `EVALUATION_IMPLEMENTATION_TRACKER.md` E2, follow-up E20 |
| 3 | ✅ `POST /feedback` + thumbs up/down (backend + frontend, all 3 surfaces) — Done 2026-08-11 — ✅ mirrored into LangSmith's own `create_feedback()` — Done 2026-08-11 — ⬜ objective/preference classification (1c/1g) not started | MVP | = original steps 3, 10. Detail: `EVALUATION_IMPLEMENTATION_TRACKER.md` E3, follow-ups E21/E22 |
| 4 | ✅ Citation validator (§8) — generalize `citation_integrity_score` cross-surface, release-blocking — Done 2026-08-11 | MVP | **New, highest value-per-effort item in this plan.** Checker built (`app/ai/knowledge/context/citations/validity.py`); CI/online-gate wiring is phases 2/6. Detail: `EVALUATION_IMPLEMENTATION_TRACKER.md` E4, follow-up E20 |
| 5 | ✅ Config fingerprint threaded through `GenerationRequest`→`GenerationUsage` (1f) — Done 2026-08-11 | MVP | = original step 8. `app/ai/runtime/generation/config_fingerprint.py`; populated at the 3 answer-producing call sites (Chat, Linear Research, Deep Research synthesis). Verified against a real Postgres row + real migration upgrade/downgrade. Detail: `EVALUATION_IMPLEMENTATION_TRACKER.md` E8 |
| 6 | ✅ Online risk-weighted scoring job, merged sampling table (§14) — Done 2026-08-11 | MVP | = original steps 4, 9. `app/ai/runtime/generation/online_scoring/`, `eval_scores` table (built here, ahead of phase 7). Detail: `EVALUATION_IMPLEMENTATION_TRACKER.md` E5 |
| 7 | ✅ Feedback → trace attachment — Done 2026-08-11 (`eval_scores` table itself already built by phase 6 above) | MVP | = original step 5. Also closed a gap this phase surfaced: E1's golden-set Ragas scoring had no runnable driver until now — `benchmarks/generation/golden_set_benchmark.py`. Detail: `EVALUATION_IMPLEMENTATION_TRACKER.md` E6 |
| 8 | ✅ Internal dashboard, owner-scoped drill-down, roll in `ResearchReview.decision` as workflow signal (§10) — Done 2026-08-11 | MVP | = original step 6. 1g's objective/preference split not applied yet — needs E11. Detail: `EVALUATION_IMPLEMENTATION_TRACKER.md` E7 |
| 9 | Golden-set promotion review, both directions (1c) | MVP | = original step 7 |
| 10 | Segment-analysis job (1f) | MVP | = original step 9 |
| 11 | ✅ Ingestion fidelity checks (§4) — parse success rate + fixture comparison — Done 2026-08-11 | MVP | New, small. `benchmarks/ingestion/`, reuses the 5 existing cached research-paper fixtures. Detail: `EVALUATION_IMPLEMENTATION_TRACKER.md` E12 |
| 12 | ✅ Context-construction provenance + token-efficiency checks (§6) — Done 2026-08-11 | MVP | New, small. `app/ai/knowledge/context/quality.py`. Detail: `EVALUATION_IMPLEMENTATION_TRACKER.md` E13 |
| 13 | ✅ Adversarial guardrail dataset (§9) — Done 2026-08-11 | MVP | 18 cases, `datasets/adversarial/`. Also feeds Wave 7's in-house guardrails gap-filling (superseded the NeMo-evaluation framing — see `PRIORITIZED_ROADMAP.md` Wave 7). Detail: `EVALUATION_IMPLEMENTATION_TRACKER.md` E15 |
| 14 | ✅ Retrieval metric completeness (Recall@K, Hit Rate@K, metadata-filter accuracy) — Done 2026-08-11 | MVP | Recall@K/MRR/NDCG/metadata-filter accuracy were already built; only `hit_rate_at_k` was actually missing — added to `benchmarks/retrieval/metrics.py`+`benchmark.py`, regression threshold, tests. Detail: `EVALUATION_IMPLEMENTATION_TRACKER.md` E14 |
| 15 | Full context-construction layer (redundancy, lost-in-the-middle, compression preservation) | Mature | |
| 16 | Citation entailment/placement/specificity judges | Mature | |
| 17 | Full workflow scorecards (plan quality, subquestion coverage, tool-call accuracy) | Mature | |
| 18 | Judge calibration (compare automated judges against expert labels) — methodology in §18 | Mature | Only worth doing once MVP has real production volume to calibrate against |
| 19 | Full dataset taxonomy split (retrieval/citation/unanswerable/multilingual as separate datasets) | Mature | Only once volume justifies it — see §3 |
| 20 | Product-level A/B testing (satisfaction, task completion, retention across variants) — see §18 | Mature | Distinct from and consistent with 1f's already-deferred "no live A/B traffic splitting" — that's about regression detection, this is about product decisions; both deferred for the same reason |

---

## 17. What's deliberately deferred, and why

Stated explicitly so nothing here reads as an oversight:

| Deferred item | Why not now |
|---|---|
| Separate datasets per query type (10+ tables) | The schema in §3 already supports slicing one dataset by field — splitting only pays off once curation volume outgrows that |
| Citation entailment (LLM/NLI judge) | The deterministic checks in §8 (existence, provenance, fabrication) catch the highest-severity failures for near-zero cost; entailment needs an LLM call per citation and should wait until the cheap layer proves insufficient |
| Full workflow scorecards (plan quality, tool-call accuracy judges) | New LLM-judge rubrics to design and calibrate — real work, lower value-per-effort than the MVP items above |
| Judge calibration against expert labels | Needs real production volume and a real disagreement rate to calibrate against — premature before MVP ships |
| Multilingual, performance-specific datasets | No evidence yet that either is a live product concern — build when there's a signal, not preemptively |
| Adaptive/statistical sampling | Already ruled out in 1b — static risk-weighted rules cover the known blind spots without a sampler that itself needs tuning |
| Product-level A/B testing (real-user variant comparison) | High-cost, needs real traffic volume and a variant-assignment mechanism neither of which exist yet — same reasoning that already deferred live A/B traffic splitting in 1f, just stated for the product-metrics version too |
| A dedicated `evals/` top-level folder | **Considered and rejected, not deferred** — see §18. This would duplicate `benchmarks/`, which already does this job |

---

## 18. Evaluation levels, judge methodology, and where things physically live

Added 2026-08-10, cross-checked against an LLM-evaluation methodology
guide reviewed against this plan. Nothing here changes scope — it
organizes and locates work already planned above, plus captures a
methodology (judge calibration) that was previously just a one-line
deferred bullet.

### Three levels, and which tool owns each

| Level | What | Tool | Where in this plan |
|---|---|---|---|
| **1 — Deterministic checks** | Schema validity, citation existence, type/range checks on structured output | **Pytest** — not just "ResearchMind code" generically | §8's citation validator, §13's absolute gates. **Concrete, already-existing home**: `tests/evaluation/test_faithfulness.py`, `test_groundedness.py`, `test_reranking.py`, `test_retrieval_precision.py` and `tests/security/test_jailbreaks.py`, `test_prompt_injection.py` were all real, already-named, **0-byte empty files** in this repo — confirmed 2026-08-10. **Status 2026-08-11: all but `test_reranking.py` now populated** (E1/E4/E14/E15) — the mapping stated here turned out not to be 1:1 by position once actually filled in: citation checks (§8) needed their own new file (`test_citation_validity.py`, no existing stub name fit — see E4), `test_faithfulness.py` ended up covering §7's new Ragas tier + the golden dataset, `test_groundedness.py` covers §7's pre-existing lexical tier, `test_retrieval_precision.py` covers §5's retrieval metrics (E14), and the security pair now covers §9's adversarial guardrail dataset (E15) exactly as originally mapped here. `test_reranking.py` remains the one open stub — no Wave 1 item currently scoped to fill it. |
| **2 — Human + LLM-judge** | Subjective quality, faithfulness, tone | RAGAS + human review (1c) | §7, §8's Mature entailment judge, §9 |
| **3 — Product A/B testing** | Real-user outcome comparison across variants | Would need new infrastructure | Explicitly deferred, §17 |

### Evaluation vs. debugging vs. improvement — a distinction worth keeping explicit

LangSmith plays two different roles in this plan and it's easy to blur
them: **tracing answers "why did this fail" for one specific request**
(debugging — read a trace) vs. **telling you "is quality acceptable
across the whole system"** (evaluation — §13/§14's scores and gates). A
trace showing a wrong document was retrieved doesn't tell you whether
that's a one-off or a systemic regression across 500 cases — that's what
the golden set and segment-analysis job are for. Both matter; neither
substitutes for the other.

### Judge output format — default to pass/fail + critique, not a bare score

Every judge this plan adds going forward (§8's Mature-tier entailment
judge, §10's Mature-tier tool-call-correctness/plan-quality judges)
should default to returning **a pass/fail decision plus a short written
reason**, not just a 0-1 float. A bare score of 0.6 doesn't tell anyone
what to fix; "fail — cites Paper B for a claim actually made in Paper C"
does. This costs nothing extra to compute (the reasoning is typically
already in the model's response) and directly determines whether a
low-scoring case is actionable or just noise. Ragas's own metrics
already report component-level detail consistent with this principle —
this is a default output-shape rule for any *new* judge this plan adds
beyond what Ragas provides.

### Judge calibration methodology (fills in §17's deferred item, when its time comes)

When judge calibration becomes worth doing (real production volume, per
§17):

1. Collect a representative sample of judge outputs alongside independent
   human/expert labels on the same examples.
2. Compute **raw agreement rate** (matching decisions ÷ total).
3. **Watch for base-rate distortion** — if 95% of real answers are
   genuinely good, a judge that always says "pass" scores 95% agreement
   while catching zero real failures. Raw agreement alone is misleading
   whenever one label dominates, which is expected for a system that's
   mostly working. Use **precision, recall, and F1 against the human
   labels specifically on the failure class**, not just overall agreement.
4. For cases with more than two labels or class imbalance, Cohen's kappa
   is a better summary statistic than raw agreement.
5. **Read the disagreement cases individually before tuning anything** —
   they reveal ambiguous rubrics, missing domain rules, judge bias, or
   inconsistent human labeling, not just "the judge needs work." Don't
   optimize blindly for 100% agreement — if human labels are themselves
   inconsistent, 100% agreement would mean the judge overfit to that
   inconsistency.

### Repo-structure note: no new `evals/` folder

A generic version of this plan would put datasets/evaluators/tests under
a new top-level `evals/`. Not adopted here — `benchmarks/` already has
`benchmarks/retrieval/`, `benchmarks/generation/`, `benchmarks/regression/`,
and `benchmarks/datasets/` doing this job, and introducing a second,
parallel structure would directly contradict this plan's own "don't
rebuild what already exists" principle (§1). New MVP work in this plan
lives in one of three places: `benchmarks/` (offline, engineering-facing),
the newly-identified empty stubs under `tests/evaluation/`/`tests/security/`
(deterministic Level-1 checks), or LangSmith + a small Postgres `eval_scores`
table (production-facing, per §14).
