# ResearchMind AI — Phase 2 & Phase 3 Plan (V2 / V3)

**Source:** handwritten planning notes (Sept 2021-dated notebook, content is current
— the dates on the page are just the notebook's printed calendar, not the plan's
timeline), transcribed and reconciled against the current codebase on 2026-08-10.
**Purpose:** turn the raw notes into a concrete, sequenced plan, cross-checked
against what's actually built today so nothing here duplicates existing work or
contradicts [`ROADMAP.md`](../ROADMAP.md)'s existing Phase 0–10 structure.
**Companion docs:** [`PRODUCTION_READINESS_EVALUATION.md`](../PRODUCTION_READINESS_EVALUATION.md)
(gap scorecard this plan closes several items from), [`docs/AI_ENGINEERING_AUDIT.md`](AI_ENGINEERING_AUDIT.md),
[`docs/evaluation/EVALUATION_GAP_ANALYSIS.md`](evaluation/EVALUATION_GAP_ANALYSIS.md),
[`docs/PRODUCT_FLOWS_AND_GAPS.md`](PRODUCT_FLOWS_AND_GAPS.md),
[`docs/NORTH_STAR.md`](NORTH_STAR.md) (the longer-term direction V2 #3 and #6
below are now explicitly scoped to anchor — **decided**, not just proposed,
as of 2026-08-10), [`docs/EVALUATION_PLAN.md`](EVALUATION_PLAN.md) (the
finalized, canonical evaluation design — supersedes Part 1 below).

**For execution order, see [`docs/PRIORITIZED_ROADMAP.md`](PRIORITIZED_ROADMAP.md)
(reconciled 2026-08-17)** — this document remains the detailed, code-verified analysis
of every item; `PRIORITIZED_ROADMAP.md` is the value×ease-ranked sequence
built from it, and is the canonical answer to "what do we build, in what
order."

For memory status, task IDs, and acceptance criteria, use
[`MEMORY_PLATFORM_PRIORITIZED_TASKS.md`](MEMORY_PLATFORM_PRIORITIZED_TASKS.md),
with [`MEMORY_MANAGEMENT_SUMMARY.md`](MEMORY_MANAGEMENT_SUMMARY.md) as the
orientation. M0-M2 and M4 are complete, M3 has rollout pending, and a
personal-only M12/M13 Memory management slice is live. M5's scope and
authorization foundation is complete; Project-aware runtime activation still
must precede any Project-scoped product write or retrieval.

## How to read this document

The notes call the current shipped product **V1**, the next slice **V2**, and a
further-out slice **V3**. Those aren't new phase numbers competing with
`ROADMAP.md` — every item below already has a home in the existing Phase 0–10
structure (mostly Phase 1.6, 2.8, 3.6, 6, 7, 8, 9). This doc is the **execution
plan** for the subset of those phases the notes call out next; `ROADMAP.md`
stays the source of truth for what phase something belongs to.

**The one theme that spans almost every item:** *"we can only fix or optimize
what we can see."* Every feature below that touches quality (evaluation,
feedback, tracing, guardrails, cost/token visibility) exists to make some
currently-invisible failure mode visible — to an engineer, an operator, or the
user — before it's fixed. The evaluation platform is the mechanism that ties
all of them together into one feedback loop (see [Part 1](#part-1--the-evaluation-platform-the-centerpiece)),
which is why it gets the most detail here and should be built first.

---

## Part 1 — The Evaluation Platform (the centerpiece)

**Superseded as the canonical design by [`docs/EVALUATION_PLAN.md`](EVALUATION_PLAN.md)
(2026-08-10).** 1a–1g below are that plan's MVP slice and remain accurate —
nothing here is wrong, the finalized doc extends this with a full layered
model (ingestion/context-construction/citation as first-class evaluated
layers, not just the final answer) reconciled against a broader RAG-eval
framework, while keeping the same "don't over-engineer" scope discipline.
Read 1a–1g for the mechanics that ship first; read `EVALUATION_PLAN.md` for
the complete design and what's deliberately deferred.

This is items **1, 4, 10, 11** from the notes (V2) and **4, 5, 10, 11** (V3) —
the notes return to "evaluation" four separate times across two pages, which is
the strongest signal in the whole plan. It maps to `ROADMAP.md` **Phase 2.8
Knowledge Evaluation** and **Phase 8 AI Quality / Evaluation Platform**.

### Where this actually stands today (verified, not assumed)

| Layer | State |
|---|---|
| Offline engineering benchmarks (chunking/embedding/retrieval/reranking/generation) | ✅ Real, live-verified (`benchmarks/`) — this is genuinely mature, don't rebuild it |
| Regression detection (`benchmarks/regression/`, threshold-based) | ✅ Built, but **not wired into CI** — runs only via manual `--check-regression` |
| Ragas | ❌ Not a dependency anywhere; generation scoring today is hand-rolled lexical word-overlap (`benchmarks/generation/metrics.py`) |
| End-to-end RAG golden-QA dataset | ❌ Doesn't exist |
| LLM-as-judge / semantic scoring | ❌ Doesn't exist |
| Online (production-traffic) evaluation | ❌ Doesn't exist — LangSmith traces every request but nothing *scores* those traces |
| User feedback capture | ❌ `apps/api/app/api/v1/feedback.py` exists as a **filename only — 0 bytes**, not registered in the router |
| Evaluation API/dashboard | ❌ `api/v1/evaluation.py` and `ai/quality/evaluation/` are empty scaffolds |
| Human-visible confidence/quality signal | ❌ Citations render; nothing about confidence or "was this right" does |

`ROADMAP.md`'s own Phase 8 reconciliation note is important context: a
previously-proposed standalone `app/ai/evaluation/` platform was **deliberately
not built as a separate thing** — it was folded into the Benchmark Platform
(offline) and the Observability Platform (runtime). This plan continues that
pattern rather than reversing it: don't build a third parallel system, extend
the two that already exist.

### Design principle: don't over-engineer, use what's already half-paid-for

The temptation with "build an evaluation platform" is to build a bespoke
scoring framework, a bespoke dataset manager, and a bespoke dashboard. Skip
all three — this repo already has the two hard parts:

- **LangSmith** is already wired for tracing (`apps/api/app/ai/observability/providers/langsmith/`).
  LangSmith natively supports **datasets, eval runs, feedback attachment, and
  online evaluators on a sample of live traces** — that's most of "online +
  offline" for free, it just isn't configured yet.
- **Ragas** is a focused library, not a platform — it computes faithfulness,
  answer relevancy, context precision, and context recall from
  `(question, answer, contexts, ground_truth)` tuples. It doesn't need its own
  service; it's a function call inside the existing `benchmarks/` runner and,
  later, inside a scheduled online-scoring job.

So the build is: **one small golden dataset, one Ragas scoring function reused
in two places (CI batch + sampled production), one feedback endpoint, and one
thin surface to show the results** — not a new subsystem.

### 1a. Offline evaluation (CI-gated, pre-merge)

**The metric set must split by surface — this isn't optional.** Chat is
deliberately ungrounded (`PromptContext.chunks` is hardcoded to `[]`; no
retrieval happens by default), while Linear Research and Deep Research are
both real RAG (retrieval runs every call). Ragas's faithfulness /
context-precision / context-recall are all defined *relative to retrieved
context* — they don't mean anything for a Chat turn with no retrieved
context to be faithful to. Treating all three surfaces as interchangeable
inputs to one metric set (an earlier draft of this doc did exactly that) is
a real design mistake, not a simplification.

```
Golden QA set (Postgres or versioned JSON, 50-150 examples to start,
  drawn separately per surface -- a Chat example and a Linear Research
  example are not interchangeable inputs)
  |
  v
benchmarks/runner.py --eval-golden   (new subcommand, reuses existing harness)
  |
  v
Linear Research / Deep Research examples: run end-to-end, capture
  (question, answer, retrieved_contexts, ground_truth)
  -> ragas.evaluate([...], metrics=[faithfulness, answer_relevancy,
                                     context_precision, context_recall])
  (the full RAG suite -- both surfaces genuinely retrieve)

Chat examples (no tool use): run end-to-end, capture (question, answer,
  conversation_history, ground_truth) -- NO retrieved_contexts field exists
  -> ragas.evaluate([...], metrics=[answer_relevancy])  only, plus a
  cheap non-Ragas check for appropriate memory use (did it correctly use/
  ignore prior turns) -- faithfulness/context precision/recall are simply
  not applicable here, not "not computed"

Chat examples WHERE web search or paper search fired: the tool's returned
  passages ARE retrieved_contexts for that turn -- these get the full RAG
  suite too, scoped to just that turn, since a real retrieval did happen
  |
  v
benchmarks/regression/detector.py  <-- ALREADY BUILT, just point it at these
  scores instead of/alongside the existing lexical metrics
  |
  v
.github/workflows/ci.yml  <-- NEW JOB, the one piece of wiring that's
  actually missing today. Runs on PRs touching apps/api/app/ai/**,
  fails the build on regression past threshold.
```

**Why this is small:** `benchmarks/regression/` already has the
threshold/detector logic. The only genuinely new code is (a) the golden
dataset itself, (b) a Ragas call, (c) a CI job — no new infrastructure.

**Start the golden set at 50-150 examples, not more.** A bigger set upfront is
exactly the over-engineering trap — the feedback loop in 1c grows it
organically from real production disagreements instead of trying to
anticipate them.

### 1b. Online evaluation (sampled production traffic)

```
Live /chat, /research, /research/stream request completes
  |
  v
LangSmith trace already exists (unchanged)
  |
  v
Select for scoring -- risk-weighted, not pure random. Pure uniform
  sampling gives a routine query and an already-borderline one the same
  N% chance of ever being checked, which undersamples exactly the traces
  most likely to be wrong. Instead, layer a few cheap rule-based triggers
  (not an adaptive/statistical sampler -- see note below) on a flat
  baseline, reusing signals the system already computes for free:
    ALWAYS score  -> guardrails already flagged this request (near-zero
                      marginal cost -- guardrails already ran)
    ALWAYS score  -> Deep Research runs where ResearchReview.decision
                      wasn't a clean PASS (REVISE_SYNTHESIS/RESEARCH_GAPS/
                      FINALIZE_WITH_LIMITATIONS) -- the deterministic
                      review already made this judgment call, for free
    OVERSAMPLE    -> requests carrying a config fingerprint (1f) that
                      shipped within the last N hours/requests -- a short
                      canary window that catches a regression fast instead
                      of waiting for the flat rate to hit it by chance;
                      falls back to baseline once that fingerprint has
                      enough samples
    BASELINE      -> flat 5-10% random sample of everything else, so
                      there's still an unbiased overall drift signal, not
                      only a risk-filtered one
  |
  v
Async job (reuses the same surface-aware scoring function as 1a) scores the
  sampled trace -- no ground_truth available in production, so only the
  reference-free metrics run, and WHICH ones depends on the surface exactly
  as in 1a:
    Linear Research / Deep Research  -> faithfulness, answer_relevancy,
                                         context_precision
    Chat, no tool use this turn      -> answer_relevancy only
    Chat, web/paper search fired     -> full reference-free set, scoped to
                                         that turn's tool-returned passages
  |
  v
Score attached back to the LangSmith trace via its feedback API
  (this is what makes a trace drillable: "show me low-faithfulness
  production traces from the last 7 days")
  |
  v
Also written to a small Postgres eval_scores table (trace_id, owner_id,
  metric scores, timestamp) so it can be queried without a LangSmith
  API round-trip for the dashboard in 1d
```

**Why sampling, not every request:** scoring every production request doubles
the LLM cost of the platform for a purpose (drift detection) that doesn't
need 100% coverage.

**Why rule-based triggers, not adaptive sampling:** this is still the
"don't over-engineer" line, just drawn more precisely than the original
version of this section did. An *adaptive* sampler (statistically learned
sampling weights, updated from observed outcomes) would be real
over-engineering for this stage — it's a model of its own, with its own
tuning and failure modes. The four rules above aren't that: each is a
static `if` condition on a signal the system already computes for free
(guardrail flags, review decision, config fingerprint age) plus one flat
baseline rate. It's a handful of conditionals, not a sampler that learns —
cheap to build, cheap to reason about, and it closes a real, foreseeable
blind spot in pure-random sampling instead of waiting to discover it in
production first.

### 1c. Human feedback (the loop that makes this "self-learning")

This is the notes' V2 item 4 ("implement human feedback loop and learn from
that") and directly closes [`PRODUCTION_READINESS_EVALUATION.md`](../PRODUCTION_READINESS_EVALUATION.md)
items 7 and 11.

```
User sees an answer (Chat / Linear Research / Deep Research report)
  |
  v
Thumbs up/down + optional free-text comment
  (apps/web: new affordance next to citation-card.tsx / message-bubble.tsx)
  |
  v
POST /feedback  <-- the empty stub file gets a real implementation
  {trace_id / research_id / session_id, rating, comment}
  |
  v
If a comment is present: one bounded, cheap LLM call classifies it against
  a fixed taxonomy split into two CLASSES, not just categories:
    OBJECTIVE  (hallucination/faithfulness, incomplete, wrong citation,
                missed context, other factual issue)
    PREFERENCE (tone, verbosity, structure/formatting, style)
  -- the objective categories are the SAME dimensions Ragas/review already
  score against, so that half slices onto 1a/1b's existing axes; the
  preference class is what routes differently, see 1g below. Plus a
  one-line paraphrase either way. This reuses a pattern already in the
  codebase (Memory Platform's interest-promotion: cheap filter first, LLM
  only when there's something worth validating), not a new idea. A rating
  with no comment is classified OBJECTIVE by default (a bare thumbs-down
  with no explanation is a correctness signal until proven otherwise) --
  nothing to classify, no LLM call needed.
  |
  v
Three things happen with the same write:
  1. Attached to the LangSmith trace as feedback (closes the loop with 1b --
     now a low-Ragas-score trace, a thumbs-down, AND its failure
     class/category are all visible on the same trace)
  2. Persisted to Postgres `feedback` table (rating, class, category,
     paraphrase, owner_id, config fingerprint from 1f)
  3. Routed by class (see 1g): OBJECTIVE feedback rolls into the shared
     segment-analysis job (1f) on BOTH signals, not just complaints --
     thumbs-down rate and thumbs-up rate, per config x content segment x
     failure category. PREFERENCE feedback stays owner-scoped and never
     enters the shared aggregate at all.
  |
  v
Weekly (or manually triggered) review, symmetric on both directions:
  - Confirmed-bad examples (reviewed thumbs-down + category) get promoted
    into the golden QA set (1a) as a new regression-guard example.
  - Confirmed-good examples (reviewed thumbs-up, prioritizing segments that
    were previously weak) get promoted as a POSITIVE exemplar -- a golden
    set built only from failures has no record of what "good" looks like,
    and can't confirm a fix actually reproduces it, only that it stopped
    reproducing the failure.
  This is the actual "self-learning" mechanism: production signal --
  positive and negative -- becomes permanent regression-test material,
  not just a one-time fix.
```

This is deliberately **not** automated end-to-end (i.e. a rating does not
auto-mutate the golden set in either direction) — a human still confirms a
flagged example before it becomes a permanent golden-set entry, otherwise
one bad-faith or confused rating could poison the eval set. That
confirmation step is cheap (it's a review queue, not a build) and is the
right amount of rigor without turning into a full active-learning pipeline.

**What "the AI learns" actually means here — stated plainly, since it's
easy to imply more than this system does:** nothing here trains or
fine-tunes a model — every provider in this system is a hosted LLM API,
there are no weights to update. There are two honest mechanisms, at two
different scopes, and both matter:

1. **Shared/global — config-level, described above.** The categorized,
   segment-sliced feedback (1f) tells a human which prompt version,
   chunking strategy, or routing config is underperforming and on which
   specific failure category. The human tests a candidate fix against the
   now-richer golden set (positive **and** negative real examples, not
   just regression guards) via the existing `benchmarks/regression/`
   harness, and ships it if it wins. The system's behavior evolves through
   versioned config changes vetted against accumulating real signal — not
   through the model updating itself. This improves the product for
   everyone, and is deliberately human-gated (§ above).
2. **Individual — memory-level, now active for prompt personalization.** This is
   the other real meaning of "self-learning" here: extracting repeated
   patterns in *one user's* behavior and adapting to that specific person,
   without touching any shared config. This isn't new — the Memory
   Platform's repeated-interest promotion
   (`app/ai/memory/policy/interest_promotion.py`) already does exactly
   this on the write side: a topic has to appear across 2+ distinct
   sessions within a 90-day window before one bounded LLM call decides
   whether to promote it into durable `USER`/`RESEARCH` memory — cheap
   lexical filtering first, an LLM validation call only for genuine
   repeat-pattern candidates. 1g's PREFERENCE-classified feedback is a
   second, more direct write path into the same `USER` memory tier. Both
   are real "the system noticed a pattern in how this person works and
   adapted" mechanisms. Reconciled 2026-08-17: the former read-side gap is
   closed. USER memory is injected into Chat, Linear Research, Deep Research
   proposal generation, and Deep Research execution. Prompt personalization
   is active; memory-driven routing remains deliberately out of scope.

Put together: the config loop makes the *product* better over time; the
memory loop makes *each user's* experience better over time. Neither is
weight training, and that distinction is worth keeping explicit — this is
the honest version of "self-improving" for a system built entirely on
hosted APIs, and 1f/1g already describe the mechanics of both.

### 1d. Making it visible (both audiences)

The notes are explicit: *"should be visible to users as well"* — not just an
internal dashboard. This splits into two genuinely different signals with
different latency profiles — see 1e for exactly where and when each one can
actually appear; don't design the UI around "a confidence score" as if it's
one thing.

- **User-visible** (closes readiness item 11): the thumbs up/down control
  (1c), plus the cheap deterministic signals in 1e — never a raw sampled
  Ragas/LLM-judge score per message (see 1e for why).
- **Internal/operator-visible**: a lightweight page (reuses the existing
  Prometheus/Grafana stack already built for Phase 9, or a minimal internal
  route reading the `eval_scores` table from 1b) showing: golden-set
  pass/fail trend over time, sampled production Ragas score trend, feedback
  volume and thumbs-down rate, and CI regression status. This is a read-only
  view over data that already exists after 1a-1c — resist building a
  full admin app around it.

### 1e. Where and when scores actually appear, concretely

Verified against the current code, not assumed. There are two tiers, and the
distinction is *what kind of score it is*, not a design preference:

**Tier 1 — deterministic, free, already computed, currently thrown away.**
No new LLM call, so it's available at the exact instant the answer renders —
same request/response, zero added latency.

| Where | What | State today |
|---|---|---|
| Chat / Linear Research, next to citations | Per-chunk retrieval similarity (Qdrant cosine, or RRF fusion score for hybrid) | Already computed on every retrieval (`RetrievedChunk.score`, `apps/api/app/ai/knowledge/retrieval/`) and survives into `ContextChunk.score` — but `CitationService.build()` never copies it onto the `Citation` object the frontend receives. **It's computed, then silently dropped.** Threading it through is a small fix, not new infrastructure. |
| Deep Research, report-approval screen (`draft-review.tsx`) | Review `decision`, `citation_integrity_score`, `completeness_score` | **Already shown today**, live — `draft-review.tsx:212-216` renders exactly these three fields as a one-line summary before the user approves. Note what these actually measure: `citation_integrity_score` is binary (do cited IDs exist in the evidence bundle, not "does the text match the citation"), `completeness_score` is a ratio of research tasks that finished, not topical coverage — both are cheap deterministic proxies, not faithfulness scores. |
| Same screen | ✅ Done — `limitations` (both `ResearchDraft.limitations`, the report's own self-declared caveats, and `ResearchReview.limitations`, the reviewer's), `model_quality_score`, `gap_questions` | Correction to this row's original claim: the backend did **not** already return `model_quality_score`/`gap_questions` -- `ResearchDraftReviewSummary` (`schemas/research.py`) was missing both fields even though `ResearchReview` (`ai/runtime/research/review.py`) already computed them, so a small schema + mapping addition (`api/v1/research.py::get_research_run_draft`) was needed alongside the frontend render. `revision_instructions` remains unrendered -- deliberately out of scope, since it's only populated on `REVISE_SYNTHESIS`, a decision that never reaches this screen (it triggers an automatic re-synthesis loop instead of pausing for approval), so it would always be empty here. |

**Tier 2 — real faithfulness/relevancy (Ragas or LLM-judge), from Part 1b.**
Requires its own LLM call, so it cannot be synchronous without adding latency
to every request — which is why Part 1b scores it *after* the response is
already delivered, and only for a sampled 5–10% of traffic.

- **Never present at the moment an answer first appears** — for any request,
  sampled or not, because scoring only starts after the response is sent.
- Lands seconds-to-minutes later, attached to that request's LangSmith trace
  and the `eval_scores` row.
- Deliberately **not** rendered as a per-message end-user badge: it would
  only exist for roughly 1 in 10 messages, and a UI element that's sometimes
  there and sometimes silently absent reads as broken, not as "sampled by
  design." It stays an internal/operator signal (1d) unless a later phase
  decides to build a "your answer is being double-checked, results in a
  minute" affordance specifically for it — not in scope for this plan.

**The practical takeaway:** ship the Tier 1 fixes first (both are near-free —
one dropped field to wire through, three already-returned fields to render).
They give users a real, honest signal immediately. Tier 2 is real evaluation
data, but it's an operator/aggregate tool by construction, not a per-answer
UI element, until there's a specific design for showing sampled/delayed
results without misleading users about coverage.

### 1f. Connecting benchmarks, prompt/config versions, and evaluation into one loop — the actual "self-improving" mechanism

This is the piece that turns "we built an evaluation platform" into "the
system tells us what to improve" — not fully autonomous (a human still
decides whether to ship a fix), but the *identification* of what's worth
improving becomes systematic instead of anecdotal.

**What already exists, verified against code — more than expected, don't
rebuild it:**

- **Prompt versioning is real**, not aspirational: `prompts/templates/{chat,research,summary}/v{1,2,3}/`
  are actual versioned directories, resolved through a `PromptRegistry` that
  can pin a specific version or default to latest
  (`apps/api/app/ai/runtime/generation/prompts/registry.py`).
- **Chunking and embedding are config-parametrized services** —
  `ChunkingService.chunk(document, strategy)` supports 7 strategies,
  `EmbeddingService.embed(artifact, provider)` supports 3 providers — with a
  genuinely good provenance model already on embeddings
  (`EmbeddingExperiment.configuration_fingerprint`, a SHA-256 hash of the
  provider config, `embeddings/models.py:122-153`).
- **Retrieval-time metadata is already tagged per-vector**: `chunking_strategy`
  and `embedding_model` are written into each vector's payload
  (`indexing/service.py:277-300`) — retrieval quality is already sliceable by
  config today.
- **The offline benchmark harness** (`benchmarks/`) already knows how to
  compare chunking/embedding/retrieval/reranking/generation variants against
  each other and detect regressions (`benchmarks/regression/`) — this is the
  mechanism to reuse for testing a candidate fix, not something to build new.

**The one gap that currently blocks all of it from connecting:** both
chunking and embedding are **hardcoded at the live call site** —
`processing/service.py:457` pins `ChunkingStrategy.MARKDOWN`,
`processing/service.py:514-524` pins `EmbeddingProvider.VOYAGE_AI` (the
alternative branches exist only as commented-out dead code) — so only one
config ever runs in production, nothing to compare live. And more
importantly, **`GenerationUsage`** — the table every eval score and cost
record joins against — **has no columns for pipeline config at all**: no
`prompt_version`, `chunking_strategy`, `embedding_model`, or
`routing_strategy`. So even once Part 1's eval scores exist, there's no way
to ask "did prompt v3 actually score better than v2?" — the dimension to
slice by never reaches the record holding the score.

**The design — one fingerprint, one segment-analysis job, human decides:**

```
1. Tag every generation request with a small config fingerprint
   {surface (chat/linear_research/deep_research), prompt_version,
    chunking_strategy, embedding_model, reranker, routing_strategy} --
   thread it through GenerationRequest -> GenerationResult ->
   GenerationUsage. A handful of nullable columns, not a new subsystem --
   the versioning already exists, it just needs to be carried through
   instead of discarded at the generation boundary. `surface` is included
   deliberately, not implied by the others: chunking_strategy/reranker are
   meaningless for a Chat turn with no retrieval, and mixing Chat's
   answer_relevancy-only scores into the same segment bucket as Linear
   Research's full RAG scores (see 1a) would be comparing different
   things under one number.
   |
   v
2. Part 1's eval scores (golden-set + sampled online Ragas) are written
   already carrying that same fingerprint, since they're computed from
   the same tagged requests.
   |
   v
3. A scheduled (e.g. weekly) segment-analysis job groups eval_scores by
   fingerprint dimension (surface first, then the rest) AND by
   query/content segment (e.g. "PDFs over 50 pages", "legal-domain
   queries") and flags cells that score statistically worse than the
   rest -- always within the same surface, never across surfaces. This is
   the "identify things to improve" step -- it writes findings to the
   internal dashboard (1d), it does not act on them.
   |
   v
4. A human reads the flagged list ("faithfulness dropped 12pts on
   hybrid-chunked docs since prompt v3 shipped") and decides whether
   it's worth investigating.
   |
   v
5. To test a fix, reuse the existing benchmarks/ harness: run the golden
   set plus the specific flagged real examples through the candidate
   config (a new prompt version, or finally flipping on SEMANTIC
   chunking) and compare scores before shipping -- exactly what
   benchmarks/regression/ already does, just pointed at a candidate
   instead of a PR diff.
   |
   v
6. If it wins, ship it -- it gets its own fingerprint, and step 3 starts
   watching it too. The loop repeats on the new baseline.
```

**Deliberately out of scope, to avoid over-engineering:** no feature-flag
system, no live A/B traffic splitting, no build-out of the `quality/experiments/`
package (confirmed a true empty stub — zero bytes). Those would be the right
next step if the product later needs to *automatically* route production
traffic across competing configs, but they're not required to identify what
needs improving, which is what was asked for. The fingerprint + segment job +
reuse of the existing benchmark harness is sufficient, and stops exactly
where human judgment should take over.

### 1g. Owner-scoped vs. global evaluation — don't let personal preference leak into the shared golden set

This is the reason 1c's feedback taxonomy splits into OBJECTIVE vs.
PREFERENCE classes, not just categories: **they must be evaluated at
different scopes, or the shared golden set silently absorbs one user's
taste.**

| | Scope | Feeds | Why |
|---|---|---|---|
| **Objective feedback** (factual correctness, citations, completeness) | **Global** — aggregated across all owners | Shared golden set (1a), shared segment-analysis job (1f) | Correctness doesn't vary by user — a hallucinated citation is wrong for everyone. This is the only class that should ever promote into a regression-guard or positive exemplar that gates every future deploy. |
| **Preference feedback** (tone, verbosity, report structure/formatting, style) | **Owner-scoped** — never aggregated into the shared set | That specific owner's `USER` memory tier (`MemoryType.USER`) | A researcher who wants terser reports and one who wants exhaustive ones are both right, for themselves. Promoting "user X thumbs-downed a verbose report" into the *shared* golden set would train the system to be terser for every user, including ones who explicitly want detail — a real correctness regression disguised as a preference fix. |

**Two concrete consequences:**

1. **Preference-classified feedback is now a write path into `USER`
   memory** — a third one, alongside the two extraction paths
   [`docs/todo/user-memory-profile-injection-gap.md`](todo/user-memory-profile-injection-gap.md)
   already documents (explicit trigger phrases, repeated-interest
   promotion). Reconciled 2026-08-17: both this write path and prompt-content
   read-side injection are complete. Feedback commits canonically before the
   optional USER-memory write runs in an isolated transaction.
2. **The internal dashboard (1d) needs an owner-scoped drill-down, not just
   an aggregate view.** A global thumbs-up rate can look perfectly healthy
   while one specific user's experience is quietly degrading — averaging
   hides exactly that case. The segment-analysis job (1f) should support
   slicing by `owner_id` in addition to config fingerprint and content
   segment, specifically to catch "this one user is having a bad time"
   even when nothing shared is wrong.

**What this deliberately does not do:** build a per-user model, per-user
prompt fork, or per-user eval suite — that would be real over-engineering
for what's fundamentally a preference-injection problem, already solved in
shape by the existing (if not yet wired) `USER` memory tier. The only new
work is (a) the classification split above, already folded into 1c's one
LLM call, and (b) an owner-scoped view on the dashboard — both small
additions to what 1a–1f already build, not a parallel system.

### Sequencing inside Part 1

| Step | What | Depends on |
|---|---|---|
| 0a | ✅ Thread `chunk.score` through `CitationService.build()` into `Citation`, render it as a lightweight relevance signal next to citations (Chat/Linear Research) — Done | Nothing — the score already exists, this is one dropped field |
| 0b | ✅ Render `limitations`, `model_quality_score`, `gap_questions` in `draft-review.tsx` (Deep Research) — Done | Nothing — the API already returns these, this is frontend-only |
| 1 | Golden QA set (50-150 examples) + Ragas scoring function | Nothing — can start immediately |
| 2 | Wire `benchmarks/runner.py --check-regression` into CI (already-built tooling, just needs a workflow job) | Nothing — independent, do in parallel with step 1 |
| 3 | Implement `POST /feedback` (real logic in the empty stub) + minimal frontend thumbs up/down | Nothing — independent, do in parallel |
| 4 | Online scoring job — risk-weighted selection (guardrail-flagged + non-PASS Deep Research reviews always scored, new-config canary oversampling, flat baseline for the rest — see 1b), reuses step 1's Ragas function | Step 1 |
| 5 | Feedback → LangSmith trace attachment + Postgres `eval_scores` | Steps 3, 4 |
| 6 | Internal dashboard view, with an owner-scoped drill-down alongside the aggregate (see 1g) | Steps 1, 2, 4, 5 |
| 7 | Feedback → golden-set promotion review process, **both directions**, **OBJECTIVE class only** (confirmed-bad → regression guard, confirmed-good → positive exemplar; PREFERENCE-class feedback never enters this queue, see 1g) | Step 3 (needs volume of real feedback first) |
| 8 | Config fingerprint (`prompt_version`/`chunking_strategy`/`embedding_model`/`reranker`/`routing_strategy`) threaded through `GenerationRequest` → `GenerationResult` → `GenerationUsage` (see 1f) | Nothing structurally, but pairs naturally with step 4/5 since it's the same records |
| 9 | Segment-analysis job flagging underperforming **and** improving config/content slices on the internal dashboard (see 1f), sliceable by `owner_id` (see 1g) — both thumbs-up and thumbs-down rate, not just complaints | Steps 4, 6, 8 |
| 10 | Comment-classification step: bounded LLM call tagging free-text feedback into OBJECTIVE/PREFERENCE class + category (see 1c/1g) | Step 3 |
| 11 | ✅ PREFERENCE-class feedback → isolated write path into that owner's `USER` memory; prompt-content injection is also complete — Done 2026-08-12 | Step 10, plus the completed V2 #2 read-side fix |

Steps 0a/0b are the cheapest possible starting point — both are already-computed
data sitting one dropped/unrendered field away from being visible, no backend
design work required. Steps 1–3 can start immediately and in parallel right
after; together this is the highest-value, lowest-risk slice and should ship
before anything else in this document.

---

## Part 2 — Remaining V2 items

| # (notes) | Item | Current state | Plan |
|---|---|---|---|
| 2 | User-profile memory — "fill complex gaps found in V1" | **Prompt-content read side complete, 2026-08-12; personal management slice and M5 isolation foundation live, 2026-08-17.** USER memory is written, deduplicated/superseded, injected into Chat and Research, and visible in an owner-scoped paginated/searchable Memory view with edit and confirmed deletion. | Continue production hardening through M3-M16 in [`MEMORY_PLATFORM_PRIORITIZED_TASKS.md`](MEMORY_PLATFORM_PRIORITIZED_TASKS.md): M3 rollout is pending; M4, M5, and the personal-only M12/M13 slice are implemented. Do not expand USER memory into the separate `HumanInsight` domain model. |
| 3 | Project-based workspace — project memory, project document set, doc mentioning | **Foundation only.** M5 adds minimal Project/membership models and first-class memory isolation; the full Project product, typed objects, routing, and UI remain net-new. | **Decided (2026-08-17, consistent with [`NORTH_STAR.md`](NORTH_STAR.md) §7):** design Project as the anchor for typed research objects and Research Paths. Activate the completed M5 scope boundary only after the Project runtime resolves membership server-side. `@document` remains a frontend affordance on the same grouping. |
| 4 | Human feedback loop | Same item as [1c](#1c-human-feedback-the-loop-that-makes-this-self-learning) above — not separate work. | See Part 1. |
| 5 | Interruption capability, traceable rebuilds, full token/cost visibility | **Interruption**: Deep Research already has three real `interrupt()` checkpoints (plan/report/web-search approval) — but confirmed (2026-08-10) that rejection at the plan/report checkpoints is a dead end today: the `reason` a user types is stored for audit only and never read again by any node. **Traceability**: ✅ Done — LangSmith traces now carry `owner_id` alongside `provider`/`model`/`runtime` (readiness item 8's trace-tag gap; cost-on-the-trace itself remains open, still cross-referenced from the `GenerationUsage` ledger). **Tokens & cost**: `GenerationUsage` ledger tracks this per-request, but nothing surfaces it live to the user during a run. | **Expanded (2026-08-10) — see the dedicated subsection right after this table.** Two concrete additions, both reusing existing mechanisms rather than new plumbing: (a) let a plan/report rejection carry revision instructions that route back into the *already-built* `REVISE_SYNTHESIS` repair path instead of just terminating; (b) surface running cost live in Deep Research's existing SSE event log. |
| 6 | Graph RAG setup | **Reserved but unimplemented — confirmed truly zero, not partial.** `KNOWLEDGE_GRAPH` is one of three `IndexType` enum members (`indexing/enums.py:22`), explicitly marked `(future)`; repo-wide grep for `IndexType` usage returns only that same enum file, and grep for `neo4j\|graph_store\|entity_extraction\|networkx` across the whole backend returns zero hits. No graph store client, no entity-extraction step, nothing beyond the bare literal. Not to be confused with LangGraph, which is the *orchestration* engine already used for Deep Research — unrelated. The frontend already has an empty, entirely unwired "Knowledge Graph" panel waiting for this (`apps/web/src/features/research/components/source-panel.tsx:91-101` — static JSX only, no fetch, no data shape defined anywhere) — the UI got ahead of the backend here. | **Reframed (2026-08-10, see [`NORTH_STAR.md`](NORTH_STAR.md) §5/§7):** this is no longer "better retrieval, someday" — it's the concrete substrate for the Knowledge Cartographer relations (`SUPPORTED_BY`/`RELATED_TO`/`CONTRADICTS`/`INSPIRED_BY`/`GENERATED`) between the typed research objects item 3 now anchors. Same engineering effort as before (entity/relation extraction at ingestion, a graph store, graph-aware retrieval), but sequence it **alongside** item 3 rather than as an independent, more-speculative-than-everything-else line item — still **after** Part 1, since a golden eval set in place first is what lets this be measured rather than assumed to help. **Hard constraint, decided 2026-08-10 — see the dedicated subsection right after this table:** must be configurable (default off) and strictly additive — the existing vector/hybrid retrieval path must behave identically, byte-for-byte, when the flag is off. |
| 7 | Deployment | Already has a decided direction and open-questions doc: [`docs/todo/aws-ecs-fargate-production-deployment.md`](todo/aws-ecs-fargate-production-deployment.md) (AWS ECS Fargate + RDS + ElastiCache, one VPC). Nothing built yet — no Dockerfiles, no IaC. | Follow that doc's open questions (L2 semantic-cache module gap, NAT Gateway cost, worker scaling on Fargate, Qdrant persistence, secrets management) before writing IaC. This is infrastructure work that can run in parallel with the product work above, not a blocker for it. |

### Item 5 in detail — reject-with-revise, and live cost in events (added 2026-08-10)

**a. Reject-with-revise (plan and report approval)**

Confirmed against code: rejecting at either checkpoint today discards any
chance to steer a retry. Plan rejection → `CANCELLED`, terminal. Report
rejection → publishes the draft as-is with no PDF, also terminal. Both
decision endpoints already accept a free-text `reason`, but it's written
into `plan_rejection_reason`/`report_rejection_reason` state fields that
are **never read again anywhere in the codebase** — pure audit trail today.

Meanwhile, the automatic model-driven repair loop already has the exact
mechanism this needs: `ResearchReview.revision_instructions` (a plain
`list[str]`) gets appended verbatim into the next synthesis call's prompt
(`synthesis/service.py:55-63`, `"Revise the prior draft according to these
requirements:\n- " + "\n- ".join(revision_instructions)`). A human's
rejection text can reuse this field unmodified — no new injection point to
build.

Design:
- Add an explicit opt-in on both decision endpoints, e.g.
  `{"approved": false, "reason": "...", "revise": true}` — today's
  "reject = abandon" behavior stays the unchanged default; `revise: true`
  is new and additive, not a breaking change to existing semantics.
- **Report rejection + revise**: route into the exact
  `prepare_synthesis_revision` → `synthesize` edge the automatic
  `REVISE_SYNTHESIS` path already uses, carrying the human's `reason` as
  `revision_instructions`. Re-runs synthesis + review once, identical
  shape to an automatic repair pass.
- **Plan rejection + revise**: no draft exists yet at this checkpoint, so
  route straight to `synthesize` (the same edge approval already uses
  today) with `revision_instructions` pre-populated from the human's text
  — it becomes steering text folded into the *first* synthesis call rather
  than a revision of an existing one. Same field, same code path, no new
  node.
- **If the instructions imply new evidence is needed, not just a different
  angle** — that's a different shape, matching `RESEARCH_GAPS`
  (`prepare_gap_research`) instead: a human-supplied question becomes the
  same kind of synthetic one-task gap-retrieval round the automatic path
  already runs. Worth deciding whether v1 supports only the
  no-new-evidence case (simpler, ships faster) or both — a scoping
  decision, not a blocker either way.

**Decided (2026-08-10): separate small allowance, not the shared budget.**
`REVISE_SYNTHESIS` and `RESEARCH_GAPS` already share one small pool
(`max_review_iterations` — 0 for SIMPLE, 1 for MODERATE, 2 for COMPLEX, per
`ResearchPlanningPolicy`). Reusing that same counter for human-triggered
revision has a real UX problem: a SIMPLE-tier run gets **zero** revision
budget, always, and for MODERATE/COMPLEX the human's budget is whatever the
*automatic* reviewer happened to leave behind — un-debuggable from the
user's side, since they can't see in advance whether anything is left.

Instead: human-triggered revision gets its **own** allowance — exactly one
revision opportunity per checkpoint (plan, report) per run, tracked
separately from `synthesis_revision_count`/`gap_research_count`. This is
**not** a cost-ceiling regression: `route_after_review` already checks
`within_iteration_budget` **and** `within_cost_budget` as two independent
gates — the new human allowance only decouples the *iteration-count*
dimension, and still has to pass the existing `max_estimated_cost_usd`/
`max_duration_seconds` check before it's allowed to run. Cost and duration
stay exactly as capped as they are today; only "does a human get to ask for
one revision" becomes independent of what the automatic reviewer already
spent. The frontend should still show whether the run's remaining
cost/duration budget can actually support one more synthesis pass before
offering the option, so a rejection-to-revise attempt that would blow the
cost ceiling fails clearly instead of silently.

**b. Live cost/token visibility in events**

Deep Research already streams a real, structured event log
(`ResearchEventType`, `GET /research/runs/{id}/events`) — this is the
right place for cost visibility, not a separate dashboard, since it's what
the user is already watching live during a run.

The gap: at the point each node emits its `*_COMPLETED` event, per-call
cost/token data isn't sitting in scope. `synthesis/service.py` and
`review.py` both call the Generation Runtime and get back a full
`GenerationResult` (with `.statistics`: tokens, `estimated_cost_usd`,
cache_hit), but both extract only the parsed domain model and **discard
`.statistics`** before returning to the graph node. Getting a precise
per-stage delta would mean threading `GenerationResult.statistics` back
out through both service layers — real plumbing across an abstraction
boundary that currently deliberately hides it.

**Cheaper, already-precedented alternative — running total, not per-stage
delta:** `execution.py` already has a `cost_lookup` closure
(`sum_cost_for_session`, a `SUM(estimated_cost_usd) WHERE session_id =
run_id` query) wired in for the existing budget check in
`route_after_review`. Reuse that same closure at each `*_COMPLETED` emit
call — the event-publishing mechanism already supports arbitrary metadata
per event (precedented by `suggest_related_papers`'s `{"label": ...,
"papers": ...}`).

**Decided (2026-08-10): show tokens, not just cost.** `sum_cost_for_session`
(`generation_usage.py:52-62`) is a single `select(func.coalesce(func.sum(...),
0)).where(session_id == ...)` query — extending it to also
`SUM(prompt_tokens)`/`SUM(completion_tokens)`/`SUM(total_tokens)` in the
same statement is a same-query, more-columns change, not a new query or a
different approach (the file's own `_aggregate`/`sum_for_conversation`
methods already do exactly this multi-column pattern). So `cost_lookup`
becomes a small aggregate returning all four numbers in one round-trip:
```
extra_metadata={
  "cost_usd_so_far": ...,
  "prompt_tokens_so_far": ...,
  "completion_tokens_so_far": ...,
  "total_tokens_so_far": ...,
}
```
attached to each `*_COMPLETED` event. This surfaces both cost and tokens
ticking up live in the same progress log the user already watches, at the
cost of one extra cheap 4-column query per stage instead of a
service-layer refactor.

**Scope note:** this only applies to Deep Research — it's the only
surface with a discrete event log. Chat and Linear Research stream raw
tokens (SSE), not a progress-event log, so cost visibility there needs a
different mechanism (the already-existing per-conversation cost endpoint,
or a post-answer cost line) — not this fix.

### Item 6 in detail — Graph RAG must be configurable and must not break existing retrieval (added 2026-08-10)

This is a hard constraint on the design, not a preference: the existing
vector/hybrid retrieval path (`RetrievalService`, Qdrant dense + sparse,
reranked) is real, working, production traffic today. Graph RAG has to be
built as something that can be fully absent from that path, not a
replacement or a fork of it.

**Four guardrails, each mapping onto an existing pattern in this codebase
— none of this is new plumbing style, all of it reuses precedent already
sitting in the repo:**

| Guardrail | How | Precedent already in the codebase |
|---|---|---|
| **Default OFF, config-driven** | A settings flag (e.g. `graph_rag_enabled: bool = False`). When off, `IndexType.KNOWLEDGE_GRAPH` stays exactly as unused as it is today — zero code path change, not just zero behavior change. | Matches how `ChunkingStrategy`/`EmbeddingProvider` are already modeled as config-parametrized-but-currently-fixed choices (`processing/service.py`) — Graph RAG becomes a third selectable option in the same style, not a new plumbing pattern. |
| **Additive at ingestion, not a fork** | Enabling the flag adds a *parallel* indexing stage (entity/relation extraction → graph store) alongside the existing chunk+embed pipeline. A document still gets chunked and embedded exactly as today regardless of the flag; if on, it *also* gets graph-indexed. | Same shape as the multi-stage `ProcessingService` pipeline already has (metadata → chunking → embedding as sequential, independently-reasoned-about stages). |
| **Additive at retrieval, fused not replacing** | Graph-traversal results get merged into the *existing* result set via `ReciprocalRankFusion.fuse()` (`retrieval/fusion/rrf.py:50-127`) as a new named parameter (e.g. `graph: RetrievalResult \| None = None`), following the exact pattern already used for the existing optional `metadata` parameter (lines 114-126) — copy that block's shape for `graph`. Confirmed: this is a small, mechanical signature change (add one parameter, one scoring block), not a rewrite of the fusion function or a second, parallel retrieval pipeline. When the flag is off, `graph` stays `None` and `fuse()` behaves identically to today, verified by the same code path executing. | `ReciprocalRankFusion.fuse()` already fuses dense+sparse+optional-metadata — it was already designed to take more than two sources. |
| **Fail-open, never blocks vector retrieval** | If the graph store is down or a traversal errors, retrieval degrades to vector-only results — the request never fails or waits on graph availability. | Directly reuses the already-established pattern from `PRODUCT_FLOWS_AND_GAPS.md`'s X4 (memory retrieval is "consistently best-effort/fail-open... a memory backend outage should never be a reason a user can't chat, research, or run Deep Research") — same philosophy, same precedent, applied to a new subsystem. |

**One more piece worth adding, following an existing precedent rather than
inventing a new one:** whether to invoke graph traversal for a *given*
query (even with the flag on) should be gated by a cheap necessity check,
not run unconditionally on every retrieval — reuse the shape of
`WebSearchNecessityService` (`ai/runtime/research/web_search/necessity.py`
— a cheap, temperature-0, structured classifier call deciding whether a
specific optional retrieval augmentation is worth invoking, fail-closed on
error). A `GraphRetrievalNecessityService` in the same shape avoids paying
graph-traversal cost/latency on queries that don't benefit from it, using a
pattern the codebase already has rather than a new one.

**Net effect:** Graph RAG becomes four small, precedented additions
(a config flag, a parallel ingestion stage, one new fusion parameter, a
necessity-check service) layered onto existing extension points, not a
parallel system living next to retrieval. With the flag off, retrieval is
provably unchanged — not just "shouldn't change," but literally the same
code path with `graph=None`.

---

## Part 3 — V3 items

| # (notes) | Item | Current state | Plan |
|---|---|---|---|
| 1 | Voice | **Absent, confirmed truly zero (2026-08-10) — the closest thing to a "blank page" in this whole document.** No STT/TTS dependency anywhere in `pyproject.toml`; repo-wide search for `whisper\|deepgram\|elevenlabs\|assemblyai\|stt\|tts\|audio.?stream\|voice` returns zero hits. `WS /chat/ws` is confirmed text-JSON-frame-only (`chat.py:863-960`) — one `receive_text()` parsed as JSON, `StreamEvent` JSON frames back; no binary/audio frame handling exists at all. | Real-time, two-way voice with a visible transcript (per the expanded scope below) is a substantially bigger build than Vision — see the dedicated subsection right after this table. Still sequence **after** Vision. |
| 2 | Vision | **Absent — and the original scaffolding claim needs a correction.** `multimodal_input`/`multimodal_output` capability flags (`vision: bool` etc.) genuinely exist at the *routing/capability* layer (model catalog, `RequiredCapability.VISION`) — but `PromptContext`/`GenerationRequest` (`apps/api/app/ai/knowledge/context/models.py`, `apps/api/app/ai/runtime/generation/models.py`) are **pure-text today with `extra="forbid"`** — there is no field anywhere to actually carry an image. "Thread an image through the existing `PromptContext`" undersold the work: that field doesn't exist yet, it needs a real (small) schema addition first. Three distinct sub-capabilities requested, each with a different cost — see the dedicated subsection right after this table. | Sequence order by cost, cheapest first: (b) chat-only image attachments → (a) image-to-RAG ingestion → (c) AI-generated charts/maps in Deep Research, which needs a genuinely new dependency (no charting library exists anywhere in this repo today). |
| 3 | Nemo guardrails | **Full evaluation now complete — see [`docs/GUARDRAILS_EVALUATION.md`](GUARDRAILS_EVALUATION.md) (2026-08-10).** Reserved enum values (`NEMO`/`LLAMA_GUARD`/`LAKERA` in `context/guardrails/enums.py`), all unimplemented. The *existing* custom rule-based system (`ai/guardrails/`) is real but not as mature as previously described: confirmed **zero ML anywhere** (pure regex/lookup tables), 5 of 16 checks are stubs, the runtime stage (budget/loop enforcement) is real logic that **never fires in production** on any surface, and `approval_gate` is unreachable dead code. | **Still evaluate-then-decide, now with a precise map instead of an assumption.** `GUARDRAILS_EVALUATION.md` found: no single vendor closes every gap (NeMo is broadest but is an architecture decision, not a detector swap; Llama Guard is the cheapest trial, fits the content-moderation stub specifically; Lakera has the richest PII/indirect-injection coverage but is SaaS-first and now part of Check Point post-acquisition). Recommended first step: build the adversarial dataset (`EVALUATION_PLAN.md` §9) and benchmark our current system's real FP/FN rate before comparing against any vendor's marketing claims. Maps to `ROADMAP.md` Phase 3.6's already-flagged "Guardrails V2" line. |
| 4, 10, 11 | Evaluation improvements / "Plan evaluation platform with Ragas & LangSmith, visible to users" / "offline & online real-time evaluation, LLM as judge" | This is Part 1, verbatim — the notes describe the same plan twice, once as a V2 item and once spelled out in more detail as V3 items 10-11. | No separate plan needed — Part 1 already covers offline (10/CI), online (11/real-time), Ragas, LangSmith, and user-visibility. "LLM as judge" is the one V3-specific addition: once the golden set (1a) exists, add an LLM-judge metric alongside Ragas's reference-free metrics for the subset of quality dimensions Ragas doesn't cover well (e.g. tone, completeness against a rubric) — bolt-on, not a redesign. |
| 5 | Observation improvements | Prometheus/Grafana (Phase 9) already real and wired across HTTP/Generation/Guardrails/Memory/Cache/Web Search/MCP. Known gaps: no `api` service in `docker-compose.yml` (host-run API scraped via `host.docker.internal`), no multiprocess Prometheus support, no latency-budget alert rules (readiness item 2). | Extend the existing stack rather than replace it: add the missing latency-SLO alert rules (readiness item 2), and feed the new `eval_scores` table (1b) into a Grafana panel so eval trends live next to the existing operational metrics instead of in a separate tool. |
| 6 | Worker-evaluator pattern | **Clarified 2026-08-10: "use another LLM to evaluate the deep research work" — confirmed this substantially already exists.** `ResearchReviewService._model_review` (`review.py:172-233`) is a genuine second, separate Generation Runtime call that judges the first call's output — draft vs. evidence, never-cached (`CacheRuntime.REVIEWER`), degrading safely to `FINALIZE_WITH_LIMITATIONS` on error rather than blocking the run. This *is* the "worker-evaluator pattern," already live, not a scaffold. | **No scoping decision needed, no Phase 6 reopening.** Verified exactly what `_model_review` does and doesn't cover: it judges the synthesized *draft* against the *evidence bundle* — it does **not** judge plan quality, per-task retrieval targeting, tool-call decisions in hindsight, or workflow efficiency (all of those are governed by deterministic budgets only, confirmed by tracing all 20 graph nodes). That remaining gap is exactly `EVALUATION_PLAN.md` §10's already-scoped Mature-tier row ("Plan quality, subquestion coverage, tool-call correctness... would need new LLM-judge rubrics") — it doesn't need separate scoping here, it's already tracked. This item effectively **drops out of Part 3 as its own line** — it's either already done (narrow reading) or already planned elsewhere (broad reading). |
| 7 | OCR support for scanned docs | ✅ Done — `docling.py` now sets `PdfPipelineOptions(do_ocr=True)`. Docling only runs OCR on pages/regions that actually need it (`bitmap_area_threshold=0.05`, `force_full_page_ocr=False` by default), so a normal digitally-generated PDF's parse latency is unaffected; only scanned/image-only pages, which previously parsed to near-empty content with no text layer, now go through OCR. | Was a literal config flip, confirmed via the real `sample.pdf` fixture test (`test_docling_parser_pdf`) plus a new regression-lock test (`test_docling_parser_enables_ocr_for_scanned_pages`) pinning `do_ocr is True`. |

### Item 2 in detail — Vision: three sub-capabilities, three different costs (added 2026-08-10)

**a. Images as RAG sources (upload → extract → chunk/embed like a document)**

The ingestion architecture is genuinely pluggable, not PDF-specific: `ParserRegistry` maps a `DocumentFormat` enum value to a `DocumentParser` implementation (`processing/registry.py`), and everything downstream of parsing (chunking, embedding, indexing) consumes the format-agnostic `ProcessedDocument` — none of it is PDF-aware. Today exactly one parser is registered (`DoclingParser`, for PDF/DOCX/Markdown/text).

Adding image sources needs three additive pieces, following the existing pattern exactly:
1. A new `DocumentFormat.IMAGE` enum value + content-type mapping (`processing/enums.py`).
2. A new parser class implementing the same `DocumentParser` contract `DoclingParser` already does — this is where the real design decision lives: **OCR alone isn't enough.** A scanned page of text is an OCR problem (reuse Docling's OCR, same mechanism as V3 #7); a chart, diagram, or photo needs a vision-model call to *describe* what's in it, not just read text off it. The parser likely needs to branch on image content (text-dense → OCR; diagram/photo → vision-model captioning) or always run a vision-model description pass and let it degrade gracefully to "no extractable text" for OCR-only cases.
3. Registering the new format in `ParserRegistry`.

**One upstream blocker, separate from parsing:** image MIME types (`image/*`) and extensions (`.jpg`/`.png`) are rejected today at **upload validation**, before a file ever reaches the parser (`upload/constants.py`'s `SUPPORTED_CONTENT_TYPES`/`SUPPORTED_EXTENSIONS`). This allowlist needs updating too — a separate, small fix from the parser itself.

**Don't conflate this with V3 #7 (OCR, ✅ Done)** — that item was Docling's built-in OCR for scanned *pages inside a PDF* (`do_ocr=False → True`, a config flip, now shipped). This is standalone image *files* as document sources, a new parser. Related mechanism (OCR is one branch of it), different scope.

**b. Chat-only image attachments (ephemeral, up to 5 per turn, never indexed into RAG)**

This is the cheapest of the three, but "thread an image through the existing `PromptContext`" (the original framing) undersold it. Confirmed: `PromptContext` and `GenerationRequest` are pure-text today with `extra="forbid"` — there is genuinely no field to carry an image, despite `vision`/`multimodal_input` capability flags already existing at the routing layer (model catalog, `RequiredCapability.VISION`). The real work:
1. Add an image-carrying field (e.g. `images: list[ImageReference]`, URL or storage-key based, not raw bytes in the schema) to `PromptContext` and thread it into `GenerationRequest`.
2. `ChatStreamRequest` (`schemas/chat.py`, also `extra="forbid"`) needs the same new field, capped at 5 per the requirement — a `Field(max_length=5)`-style validator, not new infrastructure.
3. Provider call sites need to actually pass the image content in the vision-capable-model-specific format (varies by provider — GPT-4o/Claude vision each have their own multipart message shape) — this is genuinely new per-provider code, not just schema plumbing.
4. Frontend: an upload/attach affordance in the chat composer, distinct from the existing document-upload flow (this one is turn-scoped, never touches `/documents`).

**Explicitly never persisted to the knowledge base** — this is a Chat-only, single-turn context addition, structurally similar to how web-search/paper-search results fold into a turn's context without becoming permanent RAG content.

**c. AI-generated charts/graphs/maps during Deep Research**

The most expensive of the three, and structurally different from (a)/(b) — this is image *generation* as an output, not image *understanding* as an input, and it should **not** be built by flipping `multimodal_output` on a provider config expecting an image-generation model (DALL-E-style). Research charts need to be **data-accurate**, not merely plausible-looking — the right shape is: the model produces or extracts structured data (via tool-calling/structured output), a deterministic charting library renders it, the resulting image gets embedded in the report. Confirmed this needs to follow the same **necessity-check → invoke → fold-in** shape already proven twice (Web Search, Paper Search — `WebSearchNecessityService.decide()` → `WebSearchService.search()` → fold into context), except the "fold-in" target is different: web/paper search folds *text* into `PromptContext.context`; a chart's natural home is the **report artifact**, not the LLM's context.

Two genuinely new pieces, not just wiring:
1. **A charting/plotting dependency** — confirmed **zero** charting library exists anywhere in this repo today (no matplotlib, plotly, or similar; not even numpy/pandas). This is real new infrastructure, not a config flip.
2. **Report embedding** — cheap once a chart image exists: `reportlab` (already a dependency, used for the PDF today) natively supports embedding images via its `Image` flowable, and the report's storage mechanism (`DocumentStorage`, S3-backed) is already content-type agnostic — the same `storage.upload(...)` call used for the PDF works unchanged for a PNG.

Maps: matching the necessity-check pattern, a location-bearing finding could trigger a map-generation tool the same way; genuinely lower priority than charts/graphs given Deep Research's current content is mostly literature synthesis, not geospatial data — worth deferring until there's a concrete use case, not building speculatively.

### Item 1 in detail — Voice: confirmed the largest genuinely-new build in this document (added 2026-08-10)

Real-time, two-way voice — both the researcher and the AI participating via speech, not just dictation-to-text — with a visible transcript in the same chat surface. Verified: this really is close to a blank page, more so than any other item here.

**What's confirmed absent, precisely:**
- No STT/TTS vendor dependency anywhere (`pyproject.toml` fully checked — no Whisper, Deepgram, ElevenLabs, AssemblyAI, or similar).
- `WS /chat/ws` — the one existing WebSocket in the product — is confirmed **text-JSON-frame-only**: it receives one JSON text frame, parses it as `ChatStreamRequest`, and streams `StreamEvent` JSON frames back. No binary/audio frame handling exists anywhere in that handler.

**What real-time (not batch) voice actually requires, none of which has any precedent in this codebase today:**
- Streaming STT (continuous partial transcription as the user speaks, not "record then transcribe") — a genuinely different integration shape than a single-shot API call.
- Streaming TTS synthesized in near-real-time as the model's response streams (the Generation Runtime already streams text tokens — TTS would need to consume that stream incrementally, not wait for a complete response).
- A new binary-audio-capable transport — extending `WS /chat/ws` to carry audio frames alongside/instead of JSON text frames, or a parallel WebSocket/WebRTC connection dedicated to audio.
- The transcript-visible-in-chat requirement is the one genuinely cheap part: it's just rendering the same STT/TTS text output through the chat surface's already-existing message rendering — no new UI concept, just a new source of message content.

**Scope question worth deciding before estimating, not assumed here:** which surfaces get voice? "Conduct research via voice" reads naturally onto Chat and possibly Linear Research (both are synchronous, single-turn-at-a-time). Deep Research's asynchronous, multi-approval-checkpoint, minutes-to-hours-long nature doesn't map onto a live voice conversation the same way — worth explicitly scoping voice to Chat/Linear Research first rather than assuming all three surfaces, unless there's a specific reason to include Deep Research's approval checkpoints as voice interactions too.

**Why Voice still sequences after Vision**: Vision's hardest sub-item (charts) needs one new dependency (a charting library); Voice needs a new real-time transport, a streaming STT vendor integration, and a streaming TTS vendor integration — three new pieces of infrastructure with no existing seam, versus Vision's one.

---

## Consolidated sequencing recommendation

Cross-referencing against [`PRODUCTION_READINESS_EVALUATION.md`](../PRODUCTION_READINESS_EVALUATION.md)'s
own P0/P1/P2 list so the two plans reinforce rather than compete:

1. **Do first (highest value, lowest risk, mostly independent of each other):**
   Part 1 steps 1–3 (golden set + Ragas, CI regression wiring, real `/feedback`
   endpoint) — these alone close production-readiness items 7 and 9, and most
   of 11.
2. **Cheap wins, pull forward regardless of phase:** V3 item 7 (OCR — config
   flip) is ✅ Done; V2 item 5's trace-attribution fix (readiness item 8 — one tag) is
   ✅ Done.
3. **Do next, building on step 1:** Part 1 steps 4–7 (online sampled eval,
   feedback→trace attachment, dashboard, golden-set promotion review),
   V2 item 2 (user-profile memory read-side — already fully scoped in its own
   todo doc).
4. **Evaluate before committing:** V3 item 3 (NeMo/LlamaGuard/Lakera vs.
   existing guardrails) — use the now-built eval platform to make this
   decision with data instead of assumption.
5. **Larger, sequence deliberately, and now explicitly linked:** V2 item 3
   (project workspace, scoped from day one as the anchor for the future
   typed research-object model — see `NORTH_STAR.md`) together with V2 item 6
   (Graph RAG, reframed as that model's relations substrate — sequence
   alongside item 3, not independently), both still after Part 1 so eval is
   in place to measure impact; V3 item 2 (Vision — three sub-items, sequence
   internally cheapest-first: chat attachments → image-to-RAG ingestion →
   AI-generated charts, the last of which needs a genuinely new charting
   dependency, see Item 2 in detail above).
6. **Dropped from this list (2026-08-10):** V3 item 6 (worker-evaluator) —
   confirmed the narrow reading already exists (`ResearchReviewService.
   _model_review`) and the broad reading is already tracked in
   `EVALUATION_PLAN.md` §10's Mature tier. No longer a separate scoping
   decision or a Phase 6 reopening — see Part 3's table row.
7. **Lowest priority, largest genuinely-new build in this document:** V3
   item 1 (Voice) — confirmed zero existing scaffold (no STT/TTS dependency,
   `WS /chat/ws` is text-only), needs three new pieces of infrastructure
   (real-time transport, streaming STT, streaming TTS) with no existing
   seam to build on, unlike every other item in this document. See Item 1
   in detail above.
8. **Runs in parallel, infra-only:** V2 item 7 (AWS deployment) — already has
   its own open-questions doc; doesn't block or get blocked by the product
   work above.

## The self-learning flywheel this plan builds toward

Once Part 1 is complete, the platform has a closed loop it doesn't have today:

```
Production answer generated
   -> user rates it (1c) + a sample gets scored automatically (1b)
   -> both land on the same LangSmith trace, queryable together
   -> confirmed failures get promoted into the golden set (1a)
   -> the golden set gates every future PR in CI (1a/step 2)
   -> the same scoring function that caught the regression also
      watches live production for the same failure mode recurring (1b)
```

That loop — not any single feature — is what turns "we shipped an evaluation
platform" into "the product gets measurably better over time without someone
having to notice a problem by hand first." Everything else in this document
(project workspaces, Graph RAG, voice/vision, NeMo guardrails) is a feature
that becomes *safer to ship* once this loop exists, because its quality impact
becomes visible instead of anecdotal — which is the whole point of building
the evaluation platform first.
