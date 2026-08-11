# ResearchMind — Prioritized Roadmap (V2/V3)

**Status:** canonical, ordered execution plan. **Source:** synthesizes
[`PHASE_2_3_ROADMAP.md`](PHASE_2_3_ROADMAP.md) (the detailed, code-verified
analysis of every item), [`NORTH_STAR.md`](NORTH_STAR.md) (the long-term
direction and architecture-fit assessment), and
[`PRODUCTION_READINESS_EVALUATION.md`](../PRODUCTION_READINESS_EVALUATION.md)
(the original gap scorecard) into one ranked sequence. Those three documents
remain the evidence and rationale layer — every claim here was established
there; this document only orders and re-prioritizes, it doesn't re-derive.
**Also folds in:** [`EVALUATION_PLAN.md`](EVALUATION_PLAN.md) and
[`GUARDRAILS_EVALUATION.md`](GUARDRAILS_EVALUATION.md). **Wave 1 execution
tracking:** [`EVALUATION_IMPLEMENTATION_TRACKER.md`](EVALUATION_IMPLEMENTATION_TRACKER.md)
breaks Wave 1 below into task/subtask detail with verified current code
state — check it before starting any Wave 1 item.

## How this is ordered

Every item is scored on two axes, then placed into a **Wave** (an execution
batch, not a calendar sprint):

- **Value** — impact on product trust, quality, or unblocking future work.
- **Ease** — how much is genuinely new engineering vs. reuse of an
  already-proven pattern/seam in this codebase (per this planning cycle's
  extensive code verification — nothing here is guessed).

Two explicit **overrides** to the value×ease ranking, both by direct
instruction, not derived:
1. **Guardrails is Wave 7, last, regardless of its score.** Its actual
   value×ease would place it mid-roadmap; it's placed last anyway.
2. **No external guardrail vendor.** This reverses
   `GUARDRAILS_EVALUATION.md`'s "evaluate-then-decide" conclusion into a
   firm decision: build in-house only, fill the gaps in the existing
   16-check system or add new checks of our own design. NeMo/Llama
   Guard/Lakera are no longer under consideration — see Wave 7 for what
   "fill the gaps" concretely means.

---

## Master sequence

| Wave | Item | Value | Ease | Why here |
|---|---|---|---|---|
| 0 | ✅ **Make `owner_id` non-optional on the Qdrant search API** — Done | **Very High** | Very High | Readiness P0 — the one gap with real data-leak blast radius; a type-signature change, not new logic |
| 0 | ✅ Thread `chunk.score` into `Citation` — Done | Med | Very High | Already computed, one dropped field |
| 0 | ✅ Render `limitations`/`model_quality_score`/`gap_questions` in `draft-review.tsx` — Done | Med | Very High | Already returned by the API, frontend-only |
| 0 | ✅ Add `owner_id` as LangSmith trace tag — Done | Med | Very High | One tag, closes readiness item 8 |
| 0 | ✅ OCR: `do_ocr=True` in Docling config — Done | Med | Very High | Literally a config flip |
| 0 | ✅ Roll `ResearchReview.decision` into the eval dashboard — Done | Med | Very High | Already computed every run, zero new logic |
| 1 | ✅ Golden QA set + Ragas scoring function — Done, 115 examples (grown from 24) | Very High | Med | Foundation for everything eval-related |
| 1 | ✅ Wire `benchmarks/regression/` into CI — Done, smoke tier (live-service benchmark triggers still open) | Very High | Med | Tooling already built, just needs a workflow job |
| 1 | ✅ Real `POST /feedback` + thumbs up/down — Done, backend only | Very High | Med | Closes readiness item 7, feeds the self-learning loop |
| 1 | ✅ **Citation validator, cross-surface, release-blocking** — Done (checker built; CI/online-job wiring pending, see E2/E5) | Very High | High | Generalizes an already-proven check (`citation_integrity_score`) — best value-per-effort in the whole roadmap |
| 1 | ✅ Online risk-weighted scoring job — Done | High | Med | Reuses free signals (guardrail flags, review decision) |
| 1 | Feedback → trace attachment (`eval_scores` table itself already built by the scoring job above) | High | Med | Closes the loop between 1c and 1b |
| 1 | Internal dashboard + owner-scoped drill-down | High | Med | Read-only view over data Wave 1 already produces |
| 1 | ✅ Config fingerprint through `GenerationRequest`→`GenerationUsage` — Done | High | Med | Unlocks "what to improve" identification |
| 1 | Segment-analysis job | High | Med | Depends on the fingerprint above |
| 1 | Golden-set promotion review (both directions) | High | Med | Needs feedback volume first — sequenced late within this wave |
| 1 | Comment classification (objective/preference split) | Med-High | Med | Small bounded LLM call, reuses an existing codebase pattern |
| 1 | ✅ Ingestion fidelity checks (parse success + fixtures) — Done | Med | Med | New coverage, cheap, deterministic |
| 1 | ✅ Context-construction checks (provenance, token efficiency) — Done | Med | Med | New layer, deterministic |
| 1 | ✅ Retrieval metric completeness (Recall@K, Hit Rate@K) — Done | Med | High | Small extension of an already-real benchmark suite |
| 1 | ✅ Adversarial dataset (10-20 cases) — Done (18 cases) | Med | Med | Tests our own guardrails — feeds Wave 7 directly |
| 1 | LLM-as-judge metric (tone, completeness against a rubric) | Med | Med | Bolt-on to Ragas once the golden set exists — not a redesign |
| 1 | ✅ Latency-SLO alert rules — Done (Chat + Linear Research); ⬜ `eval_scores` Grafana panel — blocked on E6 | Med | High | Measurement infra already real; this is threshold definition + one alert rule + one panel |
| 1 | ✅ Cost forecast (rolling-average projection) — Done, CLI report | Low-Med | High | Derived entirely from the existing `GenerationUsage` ledger, no new data collection |
| 1 | ✅ Register golden dataset in LangSmith — Done | Med | High | Gap-closure follow-up to E1, surfaced by the 2026-08-11 cross-check — "Done" only covered the local dataset + scoring function |
| 1 | CI live-service benchmark triggers + citation-metric wiring | High | Med | Gap-closure follow-up to E2/E4 — the absolute regression gates E2 declared are still never populated by any benchmark run |
| 1 | ✅ Frontend thumbs up/down affordance — Done, all 3 surfaces (real browser click confirmed 2026-08-11) | High | Med-High | Gap-closure follow-up to E3 — backend is live but nothing in the product calls it yet |
| 1 | ✅ Mirror `POST /feedback` into LangSmith's own `create_feedback()` — Done | Med-High | Med | Gap-closure follow-up to E21, requested directly after the user noticed LangSmith's Feedback column stayed empty on a real click — correlates user feedback to its trace inside LangSmith's own UI |
| 2 | User-profile memory read-side wiring | High | Med | Turns "captured but inert" into real personalization |
| 2 | **Socratic Challenger node (pulled forward — see note below)** | High | High | Reuses `interrupt()`, proven 3x already — too cheap to defer |
| 2 | Preference feedback → `USER` memory write path | Med | Med | Depends on the read-side fix above |
| 2 | **Reject-with-revise, i.e. "edit interruption capability"** (plan/report approval) | Med-High | Med | Reuses `REVISE_SYNTHESIS` path; see expanded detail below — this is more than one line captures |
| 2 | Live cost/token visibility in Deep Research events | Med | High | Reuses an existing cost-lookup query pattern |
| 2 | HITL confirmation on memory deletion + gated document-delete endpoint design | Med-High | Med | Readiness P0/P1 item — reuses the same `interrupt()` mechanism this wave already uses twice, doesn't need to wait for Wave 7 |
| 3 | Project schema (expanded scope, anchors typed objects) | Very High | Med-Low | Foundational for North Star; scoped once to avoid rebuild |
| 3 | Project workspace UI (create/list/switch projects) | High | Med | Without this the schema has no way to be used at all — implied but not optional |
| 3 | "@document" inline mentioning (frontend affordance) | Med | Med | Explicitly named in `PHASE_2_3_ROADMAP.md` V2 #3, sits on top of the same grouping |
| 3 | Typed research-object domain model (Knowledge/Evidence/HumanInsight/Hypothesis) | High | Med | Builds on the already-scaffolded, unused `artifacts/research` category |
| 4 | Vision — chat-only image attachments (≤5/turn) | Med-High | Med | Needs a real schema addition, no new dependency |
| 4 | Vision — image-to-RAG ingestion | Med | Med | Pluggable parser architecture already supports this shape |
| 4 | Vision — AI-generated charts/graphs/maps | Med-High | Low | Needs a genuinely new charting dependency |
| 5 | Graph RAG (configurable, additive, fail-open) | High | Low | Full build from scratch — biggest genuine architecture gap |
| 5 | Interactive Thinking Canvas (frontend) | Very High (long-term) | Very Low | Most speculative/expensive; a view over data that must exist first |
| 6 | Voice (real-time STT/TTS, visible transcript) | Med | Very Low | Confirmed largest genuinely-new build, zero existing scaffold |
| 7 | Guardrails — in-house gap-filling (see below) | Med | Med | **Ordered last by explicit decision**, not by score |
| ∥ | AWS ECS Fargate deployment | High | Med | Runs in parallel — doesn't block or get blocked by anything above |

---

## Wave 0 — Ship this week

Six items, all near-zero-cost: already-computed data one dropped field
away from visible, a literal config flag, or a type-signature change. No
dependencies between them, no reason to sequence internally — **except that
the `owner_id` fix should genuinely go first**, since it's the one
production-readiness item flagged P0 for real data-leak risk
(`PRODUCTION_READINESS_EVALUATION.md` item 5: `owner_id: str | None = None`
on the Qdrant search API means an unscoped, cross-tenant query is possible
if any future caller forgets to pass it — making the parameter required
turns that into a type error instead of a possible bug). This item was
missing from the first draft of this roadmap entirely; it's the most
important fix in this whole wave despite being one of the cheapest. Full
detail: `PRODUCTION_READINESS_EVALUATION.md` item 5, `PHASE_2_3_ROADMAP.md`
1e, Part 2 item 5, Part 3 item 7; `EVALUATION_PLAN.md` §10.

## Wave 1 — The Evaluation Platform

The foundation everything else gets safer and more measurable on top of.
Internal order: golden set and CI wiring first (independent, parallelizable
with the feedback endpoint); citation validator can ship anytime in this
wave, independent of the rest — it's flagged separately because it's the
single best value-per-effort item here, not because it has to be first.
Online scoring, trace attachment, dashboard, and config fingerprint follow
in the dependency order `EVALUATION_PLAN.md` §16 already specifies.
Golden-set promotion needs real feedback volume, so it naturally lands
late in this wave regardless of build order. Three smaller items round out
this wave, all previously missing from this roadmap: **LLM-as-judge**
(`PHASE_2_3_ROADMAP.md` Part 3, item 4/10/11 — a bolt-on metric for
dimensions Ragas doesn't cover well, e.g. tone/completeness, once the
golden set exists), **latency-SLO alerts + an `eval_scores` Grafana panel**
(closes readiness item 2 and Part 3 item 5's "Observation improvements" —
the measurement infrastructure is already real, this is threshold
definition and one panel, not new plumbing), and **cost forecasting**
(readiness item 1, P2 — a rolling-average projection derived entirely from
the existing `GenerationUsage` ledger). Full detail: `EVALUATION_PLAN.md`
§§1–17, `PHASE_2_3_ROADMAP.md` Part 1 (1a–1g) and its sequencing table,
`PRODUCTION_READINESS_EVALUATION.md` items 1 and 2. **Task-level
breakdown, code-verified current state, and sequencing for every item in
this wave:** `EVALUATION_IMPLEMENTATION_TRACKER.md`.

**2026-08-11 cross-check finding:** the four items marked ✅ Done above
(golden set, CI wiring, feedback endpoint, citation validator) each had at
least one follow-up subtask still open underneath the checkmark — real
enough to warrant their own rows rather than staying buried in another
item's fine print: **register golden dataset in LangSmith**, **CI
live-service benchmark triggers + citation-metric wiring** (the absolute
regression gates E2 declared have no benchmark run populating them yet),
and **frontend thumbs up/down affordance** (the endpoint is live, nothing
in the product calls it). None of this changes the four parent items'
Done status — it means Done was correctly scoped narrower than "nothing
left in this area." Detail: `EVALUATION_IMPLEMENTATION_TRACKER.md` E19-E21.

**2026-08-11 same-day follow-up:** once the frontend affordance (E21)
went live and the user tried it for real, they noticed LangSmith's own
Feedback column stayed empty — our `feedback` table had the row, but
nothing told LangSmith about it, so a trace and the feedback on it
weren't visible together in LangSmith's UI. Wired `POST /feedback` to
also call LangSmith's `create_feedback()`, correlated to the trace via a
new `GenerationUsage.langsmith_run_id` column. Detail:
`EVALUATION_IMPLEMENTATION_TRACKER.md` E22.

## Wave 2 — Personalization, agency, and one pulled-forward North Star piece

**Note on the Socratic Challenger node:** `NORTH_STAR.md` §8 originally
sequenced this *after* the typed research-object domain model, so a
human's response to a provoking question would have a proper `HumanInsight`
object to land in. Given ease is now an explicit ranking factor, and this
node is genuinely cheap (a new LangGraph node + prompt template reusing a
pattern already proven 3 times), it's pulled forward here — with an
explicit MVP simplification: log the human's response as a **plain
research-memory note** first, not a full typed `HumanInsight`, and upgrade
it once Wave 3's domain model exists. This is a deliberate, disclosed
deviation from `NORTH_STAR.md`'s original sequencing, not an oversight.

The rest of this wave closes real gaps on already-shipped Deep Research
features: user-profile memory (fully diagnosed already, just needs the
read-side wired), and live cost/token events (reuses an existing query
pattern).

**"Edit interruption capability" — reject-with-revise, in full,** since
compressing this to one line loses real decisions already made:
- Today, rejecting at either the plan- or report-approval checkpoint is a
  dead end — it discards the run's progress instead of letting the human
  redirect it. The fix reuses the exact `REVISE_SYNTHESIS` repair-loop
  machinery already built for automatic model-driven revisions, just
  triggered by a human's rejection text instead.
- **Decided:** human-triggered revision gets its own small budget
  allowance, tracked separately from the automatic repair loop's counter —
  not shared with it — so a human is never blocked from asking for one
  revision just because the automatic reviewer already spent the shared
  budget. Cost/duration ceilings stay exactly as enforced as they are today
  — only the iteration-count dimension is decoupled.
- **Open scoping question, not yet decided:** if the human's edit implies
  *new evidence is needed*, not just a different angle on what's already
  gathered, that's a different shape — matching the existing `RESEARCH_GAPS`
  path instead of `REVISE_SYNTHESIS`. Whether v1 supports only the
  no-new-evidence case (simpler, ships faster) or both is still open.

**HITL confirmation on irreversible actions** (readiness items 5/6) is
folded into this wave rather than deferred to Wave 7: memory deletion
(`forget_memory`) has no confirmation step today, and there's no
document-delete endpoint at all yet (so it should be designed gated from
day one, not retrofitted). This doesn't need to wait for Wave 7's guardrails
work — it reuses the same `interrupt()` mechanism this wave already
applies twice (Socratic node, reject-with-revise), so there's no reason to
gate it behind the guardrails-vendor decision, which is a different kind
of question entirely.

Full detail: `PHASE_2_3_ROADMAP.md` V2 items 2 and 5 (including "Item 5 in
detail"), `docs/todo/user-memory-profile-injection-gap.md`,
`PRODUCTION_READINESS_EVALUATION.md` items 5 and 6.

## Wave 3 — North Star foundations, including the full Project/workspace setup

**Project workspace, in full — three parts, not one.** Schema alone isn't
usable and was the whole item in earlier drafts of this roadmap; all three
belong together:
1. **`Project` schema** — scoped from day one to anchor typed objects and
   research paths (Knowledge/Evidence/HumanInsight/Hypothesis), so it isn't
   rebuilt once canvas work starts. This is the backend foundation.
2. **Project workspace UI** — create/list/switch between projects. Without
   this, the schema has nothing that lets a user actually use it — implied
   by the schema's existence, not optional, and easy to silently drop if a
   roadmap only tracks the backend piece.
3. **"@document" inline mentioning** — a frontend affordance referencing
   documents inline within a project, explicitly named alongside the
   Project item in `PHASE_2_3_ROADMAP.md` V2 #3, sitting on top of the same
   grouping as (1) and (2).

The typed research-object domain model itself is built inside the
already-scaffolded-but-unused `artifacts/research` category — zero blast
radius on anything live today. Full detail: `NORTH_STAR.md` §§5, 7, 8;
`PHASE_2_3_ROADMAP.md` V2 item 3.

## Wave 4 — Vision

Three sub-capabilities, sequenced cheapest-first internally: chat
attachments (schema addition, no new dependency) → image-to-RAG ingestion
(the parser architecture already supports this shape, needs a new parser +
an upload-validator fix) → charts/graphs/maps (needs a genuinely new
charting library — the most expensive of the three). Full detail:
`PHASE_2_3_ROADMAP.md` "Item 2 in detail."

## Wave 5 — Graph RAG and the Canvas

Graph RAG is a full build from scratch (no graph store, no entity
extraction exists anywhere today) — but it's a real prerequisite for the
Canvas, since the Canvas visualizes exactly the relations Graph RAG would
produce. Must ship **configurable (default off) and strictly additive** —
the existing vector/hybrid retrieval path must behave identically when the
flag is off; see `PHASE_2_3_ROADMAP.md` "Item 6 in detail" for the four
guardrails that make this safe. The Canvas itself stays last within this
wave — it's a view over data that needs to already exist, and building it
before the domain model/Graph RAG produce real content would mean
visualizing nothing. Full detail: `NORTH_STAR.md` §4, §8.

## Wave 6 — Voice

Confirmed the largest genuinely-new build in this entire roadmap: zero
STT/TTS dependency anywhere, the one existing WebSocket is text-only, no
real-time audio precedent to build on. Needs three new pieces of
infrastructure (transport, streaming STT, streaming TTS) with no existing
seam — unlike every other item above. Full detail: `PHASE_2_3_ROADMAP.md`
"Item 1 in detail," including the open scoping question (which surfaces
get voice — Chat/Linear Research most naturally, Deep Research's
async/multi-approval nature doesn't map onto live conversation the same
way).

## Wave 7 — Guardrails (last, in-house only)

**Decided:** no NeMo Guardrails, Llama Guard, or Lakera integration.
`GUARDRAILS_EVALUATION.md`'s "evaluate-then-decide" recommendation is
superseded by this direct decision — the existing 16-check custom system
is judged strong enough to extend rather than replace or augment with a
vendor. What "fill the gaps" means concretely, using that document's own
audit as the task list:

| Gap | Current state | In-house fix |
|---|---|---|
| Toxicity check | Stub — `return []` unconditionally | Build a cheap in-house classifier reusing the Generation Runtime — same cheap-bounded-LLM-call pattern already used by `WebSearchNecessityService`, not a rules-only approach |
| Content moderation | Stub — always-allow provider only | Same pattern as toxicity — an in-house LLM-judge check, not a vendor API |
| Access control | Stub — permissive always-allow, no tenant/ACL model | Real fix ties naturally to Wave 3's `Project` schema — access boundaries have a real home once Projects exist |
| Approval gate (`ESCALATE`) | Dead code — no implementation, unreachable | **Now cheap**, unlike when this was first scoped: wire it to a LangGraph `interrupt()`, the exact mechanism Wave 2's Socratic node and `PHASE_2_3_ROADMAP.md`'s reject-with-revise already use — reuse, not new infrastructure |
| Runtime stage (budget/loop enforcement) | Real, working logic — `BudgetGuardrail`/`LoopDetectionGuardrail` — but **never invoked in production on any surface** | Not a gap in the logic, a gap in wiring — call `evaluate_runtime()` with real `ExecutionState`/`BudgetPolicy` from the two production call sites that currently omit them. Cheapest, highest-value fix in this entire wave, since the logic already works and is tested |
| Rate-limit guardrail (this specific stub) | Stub — no request-counting state | Lower priority than it looks: a **real** rate limiter already exists elsewhere in the app (Valkey-based, wired into Chat/Research routes) — this specific guardrail-package stub may not need filling at all, just documented as superseded |
| Prompt injection / PII (already real, regex-only) | Working, but pure regex — evadable by paraphrase or unicode obfuscation | Optional strengthening: layer a cheap in-house LLM-classifier check on top of the existing regex (belt-and-suspenders), reusing the same cheap-call pattern as toxicity/moderation above — not required to ship this wave, worth scoping once the rest of this table is done |

The adversarial dataset from Wave 1 (`EVALUATION_PLAN.md` §9) is what
validates this work — run it against the filled-in system the same way it
would have run against a vendor, just with no vendor in the comparison.

## Parallel track — Deployment

AWS ECS Fargate + RDS + ElastiCache, per
`docs/todo/aws-ecs-fargate-production-deployment.md`. Explicitly doesn't
block or get blocked by anything above — infrastructure work with its own
open questions (L2 semantic-cache module gap, NAT Gateway cost, worker
scaling, Qdrant persistence, secrets management), runs whenever capacity
allows alongside any wave.

---

## Resolved — no longer an open roadmap item

**Worker-evaluator pattern.** Originally a V3 item with real ambiguity
about scope. Resolved during this planning cycle: `ResearchReviewService.
_model_review` is already a genuine second-LLM-call evaluator, live today,
judging Deep Research's synthesized draft against its evidence bundle. The
narrower reading of "worker-evaluator pattern" is therefore already done.
The broader reading (plan quality, tool-call accuracy in hindsight,
workflow efficiency judging) was never built and remains open — but it's
already captured as `EVALUATION_PLAN.md` §10's Mature-tier item, not a
separate Phase-6-reopening decision. No line item for it in the waves
above; it's absorbed into Wave 1's eval-platform work once that tier is
reached.
