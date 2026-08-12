# ResearchMind Evaluation Cheatsheet

**What this is:** a practical, scan-first reference for everything the
Evaluation Platform (Wave 1, `EVALUATION_IMPLEMENTATION_TRACKER.md` E1-E23,
all shipped as of 2026-08-12) actually measures, where you go to see it, and
what to do when a number looks wrong. **What this isn't:** the design
rationale or the implementation detail — that's
[`EVALUATION_PLAN.md`](../EVALUATION_PLAN.md) (design) and
[`EVALUATION_IMPLEMENTATION_TRACKER.md`](../EVALUATION_IMPLEMENTATION_TRACKER.md)
(exact files/line numbers/verification). This doc exists so you don't have
to read either of those to answer "something looks off — where do I look,
and what do I do about it."

---

## 1. The big picture

```
OFFLINE (benchmarks/, before a release)          ONLINE (production traffic, after a release)
─────────────────────────────────────            ───────────────────────────────────────────
rag_answer_gold / production_failures       →     Every response
  ↓ real generation call                            ↓ 100% free deterministic checks
  ↓ Ragas + custom judges                            ↓ risk-weighted LLM-judge sample (5-10%+)
  ↓ pass/fail vs. thresholds                          ↓ user feedback (thumbs up/down)
CI regression gate (blocks/flags a release)       eval_scores table + LangSmith
                                                       ↓
                                     Confirmed thumbs-down → Promotion Review queue
                                       ↓ human confirms
                            Promoted into rag_answer_gold / production_failures.json
                                       ↓
                        Re-exercised by offline benchmarks on every future release
```

**One sentence version:** offline benchmarks gate what ships; online scoring
watches what's already live; the promotion loop turns a real production
miss into a permanent regression test, so the same mistake can't ship twice.

---

## 2. Offline evaluation — what runs before a release

| Layer | Metric(s) | Gate type | Benchmark / command | CI-wired? |
|---|---|---|---|---|
| Retrieval | Recall@K, Precision@K, MRR, NDCG@K, Hit Rate@K | Relative (no >5% drop) | `Retrieval` | ✅ manual-dispatch |
| Metadata filtering | Retrieval metrics + leakage rate | Relative | `MetadataFiltering` | ✅ manual-dispatch |
| Reranking | Recall@5, MRR, NDCG@5, latency | Relative | `Reranking` | ✅ manual-dispatch |
| Ingestion fidelity | parse_success_rate, heading/table preservation | Relative | `IngestionFidelity` | ✅ **every PR** (only benchmark cheap/safe enough) |
| Context construction | Provenance preservation, token efficiency | Relative | (unit-tested, no standalone benchmark run) | — |
| Generation quality | faithfulness, answer_relevancy, context_precision, context_recall (real Ragas) | Relative | `GoldenSetGeneration` | ✅ manual-dispatch |
| Rubric adherence | rubric_adherence (LLM-judge, tone/completeness) | Relative | bolted onto `GoldenSetGeneration` | ✅ (same job) |
| Citation validity | fabricated_citation_rate | **Absolute** (0% target) | bolted onto `GoldenSetGeneration` | ✅ (same job) |
| Schema validity | schema_validity_rate | **Absolute** (100% target) | `SchemaValidityRegression` | ✅ manual-dispatch |
| Abstention | abstention_pass_rate | **Absolute** (≥95% target) | `AbstentionRegression` | ✅ manual-dispatch |
| Confirmed-failure regression | Ragas + citation, on real past incidents | Relative + absolute | `ProductionFailuresRegression` | ✅ manual-dispatch |
| Adversarial / guardrails | pass/fail per case (18 cases) | Informational | `benchmarks/guardrails/` | Not CI-wired (manual) |

**Why "manual-dispatch" and not automatic:** the live-service jobs make real
Voyage AI / OpenAI calls, which cost real money — by direct decision, they
only run when someone explicitly checks the box on a `workflow_dispatch`.
Only the free `IngestionFidelity` smoke job runs on every PR automatically.

---

## 3. Online evaluation — what runs on live traffic

| Signal | Sampling | Cost | Source |
|---|---|---|---|
| Request success/error, latency, cost, routing | 100% | Free | Prometheus + `GenerationUsage` |
| Citation validity | 100% | Free (deterministic) | `OnlineScoringJob`, every Chat/Linear/Deep Research response |
| Web search invoked + succeeded | 100% (Chat when toggled on; Deep Research when enabled) | Free (deterministic) | `OnlineScoringJob` (E23) |
| Paper search invoked + succeeded | 100% (Chat only, when toggled on) | Free (deterministic) | `OnlineScoringJob` (E23) |
| Guardrail-flagged request | 100% (always scored) | — | Risk-weighted rule |
| Deep Research non-`PASS` review decision | 100% (always scored) | — | Risk-weighted rule |
| Faithfulness / answer_relevancy (Ragas judges) | 5-10% baseline, oversampled around flags/canaries | LLM calls | `OnlineScoringJob` |
| Rubric adherence | Same sample as above, opt-in | LLM calls | `Settings.eval_online_rubric_judge_enabled` (default **off**) |
| User rating (thumbs up/down) | 100% of submitted feedback | Free | `POST /feedback`, all 3 surfaces |
| Comment classification (objective vs. preference) | 100% of feedback with a comment | Cheap LLM call | E11 |

All of the above lands in one table, `eval_scores`, one row per metric per
generation — this is the single source of truth the dashboard, LangSmith
sync, and promotion review all read from.

---

## 4. Where to look

| I want to... | Go to |
|---|---|
| See a specific user/owner's recent scores | `/eval-dashboard` → **Owner** tab (search by owner id) |
| See the latest offline golden-set run, per example | `/eval-dashboard` → **Offline** tab |
| See raw engineering-benchmark reports (retrieval, reranking, etc.) | `/eval-dashboard` → **Engineering Benchmarks** tab |
| Slice a metric by config version (e.g. did `prompt_version` "chat-v2" regress `faithfulness`?) | `/eval-dashboard` → **Segment Analysis** tab → "By Config Fingerprint (Online)" |
| Slice a metric by query type / difficulty / failure category | `/eval-dashboard` → **Segment Analysis** tab → "By Content Segment (Offline)" |
| Review confirmed thumbs-up/down candidates for promotion into the golden set | `/eval-dashboard` → **Promotion Review** tab |
| See a trace end-to-end (what was retrieved, what was generated, why) | LangSmith → the run itself (linked from Promotion Review, or via `GenerationUsage.langsmith_run_id`) |
| Compare successive `GoldenSetGeneration` runs over time | LangSmith → **Experiments** tab on the `rag_answer_gold` dataset (after `langsmith_experiment.py`) |
| See a user's thumbs up/down next to the trace it was left on | LangSmith → the run's **Feedback** column |
| Watch latency SLOs / alert state | Grafana → Prometheus alert rules (`ResearchMindChatLatencyHigh`, `...LinearResearchLatencyHigh`) |
| Watch `eval_scores` trends (avg score, pass rate, by source) | Grafana → `researchmind-eval-scores` dashboard (5 panels) |
| See whether a release candidate's regression gates passed | GitHub Actions → `generation-regression` job artifacts (`regression.json`/`regression_report.md`) |

Dashboard access requires your email in `EVAL_DASHBOARD_ADMIN_EMAILS`
(`.env`) — there's no role/admin column, this is the whole gate.

---

## 5. From signal to action

| Signal | What happens automatically | What a human needs to do |
|---|---|---|
| An **absolute gate** fails in CI (citation, schema, abstention) | `benchmarks.runner --check-regression` exits non-zero, `generation-regression` job fails | Don't merge/ship until fixed — these have zero tolerance by design |
| A **relative gate** regresses beyond threshold | Same — job fails, `regression_report.md` names the metric and the drop | Investigate before shipping; small regressions may be an intentional tradeoff, needs a judgment call |
| A user hits thumbs-down | Written to `feedback` + mirrored to LangSmith `create_feedback()`, classified objective/preference (E11) | If objective and confirmed real: mark it in **Promotion Review** |
| A Promotion Review candidate is confirmed as a genuine failure | Written to `promotion_reviews` (not yet in the dataset file) | Run `sync_promoted_examples.py` — appends to `production_failures.json`, tagged with a `failure_category` |
| A confirmed failure is synced | Nothing automatic yet | Next `ProductionFailuresRegression`/`AbstentionRegression` run (CI or manual) re-exercises it forever — the same mistake can never silently ship again |
| A Promotion Review candidate is confirmed as genuinely good | Written to `promotion_reviews` | `sync_promoted_examples.py` appends to `rag_answer_gold.json` — grows the golden set with real, not synthetic, examples |
| Online score for a metric looks bad in aggregate (Segment Analysis) | Nothing automatic | Drill into individual `eval_scores` rows (via dashboard or LangSmith trace) to find *which* requests, then decide: prompt fix, retrieval fix, or a genuine one-off |

---

## 6. Real-world scenarios

### Scenario: "Users are saying the assistant makes up sources"

| Step | What to do |
|---|---|
| 1. Confirm it's real, not anecdotal | `/eval-dashboard` → Segment Analysis → online, `metric_name = citation_validity` (the online-traffic version of the same check `fabricated_citation_rate` runs offline) — check its pass rate by `surface` |
| 2. Find specific bad responses | Drill into `eval_scores` rows where `metric_name = citation_validity`, `passed = false` — each has a `reason` and a `generation_id` |
| 3. See the actual trace | Follow `GenerationUsage.langsmith_run_id` → LangSmith run → see exactly what was retrieved and what was cited |
| 4. Confirm as a real failure | Promotion Review tab (once a user has flagged it, or manually via the same review queue) — tag `failure_category = wrong_citation` or `hallucination` |
| 5. Lock in the regression test | `sync_promoted_examples.py` → `production_failures.json` → re-checked by `ProductionFailuresRegression` on every future release |
| 6. Verify the fix worked | Re-run `ProductionFailuresRegression --check-regression` — the specific example that used to fail must now pass |

### Scenario: "We shipped a new prompt version — did it help or hurt?"

| Step | What to do |
|---|---|
| 1. Compare before/after | Segment Analysis → online, slice `faithfulness`/`answer_relevancy`/`rubric_adherence` by `prompt_version` |
| 2. Check the offline release-candidate score too | Run `GoldenSetGeneration --check-regression` locally or via manual CI dispatch before shipping, not just after |
| 3. If it regressed | `regression_report.md` names the exact metric and delta — decide whether to revert or accept the tradeoff |

### Scenario: "Is Deep Research actually citing its evidence correctly?"

| Step | What to do |
|---|---|
| 1. Deep Research already had this covered pre-Wave-1 | `ResearchReview.citation_integrity_score` (deterministic, runs on every draft) |
| 2. See it in aggregate | Rolled into the dashboard as a workflow-health metric (E7) — `ResearchReview.decision` distribution |
| 3. See it cross-surface (Chat/Linear too) | `citation_validity` in `eval_scores` — this is the generalized version of the same check |

### Scenario: "Did the assistant search the web when it should have — or search when it shouldn't have?"

| Step | What to do |
|---|---|
| 1. Chat and Deep Research web search | Segment Analysis → online → `metric_name = web_search_invoked` / `web_search_success`, sliceable by `surface` — same two metric names for both |
| 2. Chat paper search | Same view, `metric_name = paper_search_invoked` / `paper_search_success` |
| 3. Check a specific conversation/run | Query `eval_scores` for that `generation_id`, or check the LangSmith trace's Feedback column |
| 4. Deep Research paper search — known gap | Not tracked at all — no event/state exists for it, unlike Deep Research web search |

### Scenario: "A user says the assistant confidently answered something it had no business answering"

| Step | What to do |
|---|---|
| 1. This is an abstention failure | Confirm via Promotion Review, tag `failure_category = abstention_failure` |
| 2. Lock in the regression test | Synced into `production_failures.json`, re-checked by `AbstentionRegression` forever |
| 3. Check the aggregate rate | `abstention_pass_rate` — an **absolute gate** (≥95%), fails CI if the controlled unanswerable subset starts getting confidently wrong answers |

### Scenario: "Is a retrieval/reranking change from a PR actually better?"

| Step | What to do |
|---|---|
| 1. Run the benchmark locally | `uv run python -m benchmarks.runner Retrieval --dataset benchmarks/datasets/research-papers --check-regression` (same for `Reranking`/`MetadataFiltering`) |
| 2. Or trigger it in CI | `workflow_dispatch` → check the `full_regression_suite` box |
| 3. Read the verdict | `regression_report.md` — Recall@K/NDCG@K/etc. vs. the last committed baseline, 5% drop tolerance |

### Scenario: "Are we within our latency budget?"

| Step | What to do |
|---|---|
| 1. Chat / Linear Research | Grafana alert rules fire on real P95 breach (15s / 45s thresholds) |
| 2. Deep Research | A different kind of alert, not a tight SLO — `ResearchMindDeepResearchRunAbnormallySlow` fires on P95 > 2h, since wall-clock duration legitimately includes human-approval wait time; it's a stuck-run/anomaly detector, not a performance target |
| 3. Cost | `uv run python -m app.services.cost_forecast` (rolling-average projection off the real `GenerationUsage` ledger) |

### Scenario: "Someone tried a prompt injection / jailbreak — would we catch it?"

| Step | What to do |
|---|---|
| 1. Check the adversarial suite | `benchmarks/guardrails/`, `datasets/adversarial/adversarial_cases.json` (18 hand-built cases) |
| 2. Current detection rate | 13/18 detected as of the last run — 5 known-evasive cases (paraphrase, Unicode homoglyphs, spelled-out PII) are **documented gaps**, feeding Wave 7's guardrails work, not silently passing |
| 3. If a real injection succeeds in production | Confirm via Promotion Review, tag `failure_category = injection_success` — re-scored by `ProductionFailuresRegression` via the same rubric-judge path as citation checks |

### Scenario: "Is our release candidate safe to ship at all?"

| Step | What to do |
|---|---|
| 1. Run the full release-candidate suite | `workflow_dispatch` with `full_regression_suite: true` → runs `Retrieval`/`Reranking`/`MetadataFiltering`/`GoldenSetGeneration`/`ProductionFailuresRegression`/`AbstentionRegression`/`SchemaValidityRegression` |
| 2. Any absolute gate fails | **Do not ship** — citation/schema/abstention gates have zero tolerance by design |
| 3. Any relative gate regresses | Read `regression_report.md`, make the call |
| 4. All green | Ship — the same suite re-checks every previously-confirmed production failure automatically |

---

## 7. Quick command reference

```bash
# Release-candidate generation quality (real Ragas judge)
uv run python -m benchmarks.runner GoldenSetGeneration --dataset datasets/golden --check-regression

# Re-check all previously-confirmed production failures still stay fixed
uv run python -m benchmarks.runner ProductionFailuresRegression --dataset datasets/production_failures --check-regression

# Abstention pass rate (unanswerable-question handling)
uv run python -m benchmarks.runner AbstentionRegression --dataset datasets/golden --check-regression

# Schema validity (structured-output contract, via the research planner)
uv run python -m benchmarks.runner SchemaValidityRegression --dataset datasets/schema_validity --check-regression

# Retrieval / reranking / metadata-filtering
uv run python -m benchmarks.runner Retrieval --dataset benchmarks/datasets/research-papers --check-regression
uv run python -m benchmarks.runner Reranking --dataset benchmarks/datasets/research-papers --check-regression
uv run python -m benchmarks.runner MetadataFiltering --dataset benchmarks/datasets/research-papers --check-regression

# Persist a golden-set run's per-example scores into eval_scores (so it's queryable in the dashboard)
uv run python -m benchmarks.generation.persist_golden_set_scores --report benchmarks/reports/goldensetgeneration/report.json

# Log a run as a LangSmith Experiment (comparable against prior runs, in-UI)
uv run python -m benchmarks.generation.langsmith_experiment --report benchmarks/reports/goldensetgeneration/report.json

# Sync confirmed Promotion Review candidates into the dataset files
uv run python -m benchmarks.generation.sync_promoted_examples

# Register/refresh the golden dataset in LangSmith
uv run python -m benchmarks.generation.langsmith_sync

# Start the online scoring worker (production traffic → eval_scores)
python -m apps.worker.eval_scoring_main
```

---

## 8. Known gaps (so nothing here overclaims)

| Gap | Why | Where tracked |
|---|---|---|
| Live-service CI jobs don't auto-block every merge | Manual-dispatch-only by direct instruction — real Voyage AI/OpenAI cost | E20 |
| Deep Research paper-search invocation rate not measured | No event/state tracking exists for it at all, unlike Deep Research web search (which is now covered) | E23 |
| 3 of 8 `failure_category` values never re-exercised (`workflow_loop`, `schema_violation`, `unnecessary_tool_use`) | Architecturally infeasible for a single-generation-call benchmark design | E10 |
| Citation entailment (does the source *actually* support the claim, not just exist) | Deterministic existence/provenance checks catch the highest-severity failures cheaply; entailment needs a judge per citation — Mature tier, deferred | `EVALUATION_PLAN.md` §8/§17 |
| Judge calibration against human labels | Needs real production volume to calibrate against — premature pre-launch | `EVALUATION_PLAN.md` §17/§18 |

Full detail on any of the above: `EVALUATION_IMPLEMENTATION_TRACKER.md`'s
own entry for that item.
