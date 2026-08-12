# ResearchMind AI Evaluation Gap Analysis

**Reviewed:** 2026-08-05  
**Scope:** Offline benchmarks, datasets, metrics, regression controls, runtime signals, tests, API integration, and CI

**Historical, mostly superseded (2026-08-12 note, not a 2026-08-05
correction).** This document's own point-in-time findings below are kept
as-is for the record — this note only says what changed since. Every P0
gap this doc identified (no end-to-end golden QA, no CI evaluation gate,
tiny single-domain dataset, lexical-only generation proxies, no
citation/schema/abstention gates) and every "Missing" row in the
Evaluation Coverage table (end-to-end RAG, safety/security, human/product
quality, evaluation API/dashboard) has since shipped — see
[`EVALUATION_PLAN.md`](../EVALUATION_PLAN.md) for the current design and
[`EVALUATION_IMPLEMENTATION_TRACKER.md`](../EVALUATION_IMPLEMENTATION_TRACKER.md)
for verified current status of every item (E1-E23 as of 2026-08-12). The
"Final implementation plan" section at the bottom of this file already
carries its own, earlier (2026-08-10) supersession note for the same
reason — this banner extends that same fact to the rest of the document,
which had no equivalent notice even though it's just as out of date in
substance. One genuine gap this pass' cross-doc audit found — not
something this 2026-08-05 doc called out either — was `EVALUATION_PLAN.md`
§10's "tool-invocation rate & success rate" metric, never previously
tracked at all; built same day for Chat as E23 (Deep Research/Linear
Research explicitly excluded, see that item's own entry).

## Executive assessment

| Area | Assessment | Evidence |
|---|---|---|
| Overall maturity | ResearchMind has a functional engineering benchmark foundation, but not a complete product-quality evaluation system. | Six benchmark categories, canonical reports, and a regression detector exist under `benchmarks/`. |
| What works | The project can compare chunking, embedding, retrieval, metadata-filtering, reranking, and generation candidates. It also measures ingestion performance. | Implemented benchmark modules and existing reports under `benchmarks/reports/`. |
| Main limitation | The system cannot reliably establish whether the final research answer is correct, useful, safe, and better than the previous release. | No end-to-end golden QA, human evaluation, semantic or LLM judge, or CI evaluation gate. |
| Risk | Quality-regression confidence is low; engineering-comparison value is moderate. | Runs are manual, datasets are small and single-domain, scoring relies heavily on proxies, and baselines are latest-only. |

## How evaluation works today

| Stage | Implementation | Current behavior | Output or decision |
|---|---|---|---|
| Invocation | `benchmarks/runner.py` | An engineer selects a benchmark and dataset. Regression checking is optional through `--check-regression`. | Manual local execution. |
| Composition | `benchmarks/factory.py`, `benchmarks/registry.py` | Constructs production chunking, embedding, retrieval, reranking, and generation services. | Real providers and dedicated benchmark infrastructure. |
| Dataset loading | `benchmarks/datasets/research-papers/` | Loads five processed research papers, 20 retrieval queries, and 13 generation queries. | Versioned local inputs; upload and parsing are excluded. |
| Execution | Suite-specific `benchmark.py` files | Runs candidate implementations against shared inputs. The ingestion benchmark uses a separate CLI. | Candidate metrics, metadata, notes, and errors. |
| Retrieval scoring | `benchmarks/retrieval/metrics.py` | Compares ranked document filenames against binary document-level relevance judgments. | Recall@K, Precision@K, MRR, and NDCG@K. |
| Generation scoring | `benchmarks/generation/metrics.py` | Uses significant-word overlap between answer, query, context, and expected answer. | Faithfulness, groundedness, relevance, completeness, citation accuracy, and hallucination proxy. |
| Performance scoring | Suite benchmark implementations | Measures latency, throughput, cost, memory, storage, and output counts where applicable. | Engineering trade-off metrics. |
| Reporting | `benchmarks/common/report_generator.py` | Serializes the current run. | `report.json` and `report.md` under `benchmarks/reports/<suite>/`. |
| Regression detection | `benchmarks/regression/` | Compares matching candidates and configured metrics against the previous report. | Non-zero exit when a configured threshold is exceeded. |
| Runtime signals | Generation guardrails, Prometheus, `ResearchReviewService` | Live generation emits some quality signals outside the benchmark framework. | Operational signals are not unified with offline evaluation. |

## Evaluation coverage

| Evaluation surface | Status | What is measured | Main limitation |
|---|---|---|---|
| Chunking | Partial | Counts and average/minimum/maximum chunk sizes, words, and token estimates. | No coherence, boundary quality, semantic preservation, or downstream retrieval impact. |
| Embeddings | Partial | Latency, throughput, dimensions, and output counts. | No similarity quality or downstream retrieval comparison by embedding model. |
| Retrieval | Implemented | Recall@5/10/20, Precision@5/10, MRR, NDCG@5/10, latency, and category slices. | 160 queries over 50 documents (up from 20/5, 2026-08-11) — no longer saturated, but still binary document-level relevance, not chunk-level. |
| Metadata filtering | Implemented | Retrieval metrics and leakage rate for filtered and unfiltered candidates. | No adversarial or multi-tenant stress dataset. |
| Reranking | Implemented | Recall@5, MRR, NDCG@5, and latency across baseline, CrossEncoder, and Voyage. | Uses the same 50-document/160-query corpus as Retrieval above (no longer saturated) but still has no graded relevance. |
| Generation | Partial | Lexical faithfulness, groundedness, relevance, completeness, citation accuracy, hallucination proxy, latency, and cost. | Word overlap can mis-score paraphrases, contradictions, and unsupported claims. |
| Ingestion pipeline | Partial | Stage latency, throughput, memory, artifact size, vector counts, and success rate. | Excludes upload/PDF parsing and does not measure answer quality. |
| End-to-end RAG/research | Missing | None. | No query → retrieval → synthesis → citation-correctness golden evaluation. |
| Safety and security | Missing | Production guardrail unit tests exist. | Jailbreak and prompt-injection evaluation files are empty; no attack corpus or release gate. |
| Human/product quality | Missing | None. | No rubric, pairwise comparison, reviewer calibration, or feedback linkage. |
| Evaluation API/dashboard | Missing | Evaluation artifacts support storage round trips. | `api/v1/evaluation.py` and `ai/quality/evaluation/` are empty scaffolds. |

## Prioritized gaps

| Priority | Gap | Impact | Recommended action | Acceptance signal |
|---|---|---|---|---|
| P0 | No end-to-end golden QA | Final-answer correctness and release confidence cannot be established. | Create versioned cases containing queries, evidence, expected claims, citations, and abstention expectations. Run the production retrieval and synthesis path. | Results distinguish retrieval failures from generation failures. |
| P0 | Benchmarks are absent from CI | Quality regressions can merge undetected. | Add a credential-free PR smoke suite and scheduled full-provider benchmarks. Promote stable metrics to blocking gates. | CI publishes artifacts and fails on agreed thresholds. |
| P0 | Dataset is tiny and single-domain | Results are unstable and unrepresentative; Recall@5 is saturated at `1.0`. | Expand by domain, difficulty, answer type, corpus size, negative cases, and no-answer cases. Split development and held-out sets. | Coverage is documented and key metrics are not universally saturated. |
| P0 | Generation metrics are lexical proxies | Paraphrases can be penalized, while contradictions containing matching words can pass. | Combine deterministic checks with semantic entailment/claim matching and a calibrated LLM judge. | Automated scores meet a documented human-agreement target. |
| P0 | Provider failures become zero-valued candidates | Quota or connection failures can be mistaken for quality results. | Add explicit status, retries, minimum completion rate, invalid-run behavior, and exclusion from rankings. | Failed or partial candidates cannot produce a valid passing comparison. |
| P1 | No human evaluation workflow | Automated scores are not calibrated against usefulness, clarity, or research rigor. | Define rubrics and blinded pairwise review; measure inter-rater agreement. | A human baseline and periodic calibration report exist. |
| P1 | Baselines are mutable and latest-only | Historical trends and provenance are weak because `report.json` is overwritten. | Store immutable run IDs with commit, dataset hash, prompt, model, configuration, and environment. Maintain a promoted baseline pointer. | Runs are reproducible and trendable. |
| P1 | Dataset compatibility is not enforced | Different datasets can be compared as if directly compatible. | Reject or mark comparisons incompatible when dataset versions or hashes differ. | Regression reports identify incompatible datasets. |
| P1 | Missing/new candidates are skipped | A disappeared provider or missing metric can escape the gate. | Define policies for required, missing, and new candidates and metrics. | Missing coverage is reported and can fail the gate. |
| P1 | Thresholds do not model uncertainty | Small-sample variance creates false confidence or noisy gates. | Add quality floors, confidence intervals/bootstrap tests, repeated-run variance, and segment gates. | Thresholds have documented statistical justification. |
| P1 | Runtime evaluation is fragmented | Offline scores, guardrails, report review, feedback, and artifacts cannot be analyzed together. | Define a canonical result schema and shared run IDs across benchmarks, runtime, artifacts, and feedback. | One record links inputs, outputs, scores, configuration, and feedback. |
| P1 | Security evaluation placeholders are empty | Jailbreak and prompt-injection resistance lack systematic evidence. | Build adversarial suites for prompts, retrieved documents, tools, leakage, and citation spoofing. | Security suites run regularly with severity-based gates. |
| P1 | No prompt/experiment evaluation | Prompt and configuration changes cannot be compared systematically. | Add experiment manifests, paired runs, prompt-version capture, and statistical comparison. | Prompt/model changes include an evaluation delta. |
| P2 | Chunking/embedding metrics are disconnected from task quality | Fast or well-sized outputs may retrieve poorly. | Evaluate chunker/embedding pairs using downstream retrieval and citation outcomes. | Reports show downstream quality, latency, and cost trade-offs. |
| P2 | Documentation contradicts code | Engineers may misunderstand what is implemented. | Update `docs/evaluation/strategy.md` and related status documentation. | Documentation matches executable behavior and has a verified date. |

## Recommended implementation sequence

| Phase | Timebox | Deliverables | Exit criterion |
|---|---:|---|---|
| 1 — Stabilize | 1–2 weeks | Failure semantics, immutable run metadata, dataset compatibility, documentation fixes, and CI smoke benchmark. | Failed, partial, or incomparable runs cannot silently pass. |
| 2 — Golden RAG evaluation | 2–4 weeks | Held-out dataset and production-path runner covering retrieval, claims, citations, abstention, latency, and cost. | Reports decompose failures by pipeline stage. |
| 3 — Calibrate scoring | 2–3 weeks | Semantic/entailment scoring, LLM-judge rubric, blinded human review, and agreement analysis. | Automated scores demonstrate acceptable reviewer agreement. |
| 4 — Operationalize | 2–4 weeks | Scheduled runs, evaluation history/API, dashboards, production sampling, feedback linkage, and security suites. | Release decisions use traceable evaluation evidence. |

## Evidence reviewed

| Repository evidence | Observation |
|---|---|
| `benchmarks/runner.py`, `factory.py`, and `registry.py` | A manual generic benchmark runner and registered component suites exist; ingestion uses a separate runner. |
| `benchmarks/*/benchmark.py` and metric modules | Production services are used with deterministic quality proxies, performance metrics, and cost metrics. |
| `benchmarks/datasets/research-papers/` | Five processed papers, 20 retrieval queries in four categories, and 13 generation queries. |
| `benchmarks/reports/*` | Latest-report examples exist; some providers record quota or connection failures as zero metrics. |
| `benchmarks/regression/*` | Threshold comparison exists; missing candidates/metrics are skipped and dataset compatibility is not enforced. |
| `.github/workflows/ci.yml` | CI has formatting, linting, typing, tests, and coverage—but no evaluation job. |
| `tests/evaluation/` and `tests/security/` | Evaluation and security placeholder modules are empty; benchmark metric unit tests exist elsewhere. |
| `apps/api/app/api/v1/evaluation.py` and `app/ai/quality/*` | Application evaluation services and API remain empty scaffolds. |
| `docs/workflows/evaluation-pipeline.md` and `docs/evaluation/*` | Pipeline documentation describes implemented benchmarks, while `strategy.md` incorrectly says evaluation logic is absent. |

## Bottom line

ResearchMind can compare individual AI components and detect selected metric changes during manually initiated benchmark runs. The highest-value next step is a small, versioned, end-to-end golden evaluation suite that scores actual research answers and citations, handles failed runs explicitly, and executes automatically in CI.

---

## Final implementation plan: streamlined production evaluation

**Superseded (2026-08-10) by [`docs/EVALUATION_PLAN.md`](../EVALUATION_PLAN.md).**
The architecture below (a new bespoke `apps/api/app/ai/quality/evaluation/`
service, a new `EvaluationRecord` schema, 7 new REST endpoints, and a
4-view admin frontend) was written before a fuller review of what
LangSmith already provides — datasets, experiments, trace storage,
feedback attachment, and online evaluators. `EVALUATION_PLAN.md` reaches a
different conclusion: wire into LangSmith as the control plane instead of
building a parallel bespoke service, API, and dashboard, per its explicit
"don't rebuild what already exists as a product" principle. Building both
would mean two overlapping API surfaces and schemas doing the same job.
This section's specific ideas aren't wasted — the record-level field list
below (`prompt_version`, `latency_ms`, `cost_usd`, etc.) is a reasonable
shape for the `eval_scores` table `EVALUATION_PLAN.md` already calls for —
but treat the service/API/frontend architecture here as historical, not a
build target. Also note: this section assumes user feedback capture
already exists ("Existing feedback capability") — confirmed false as of
2026-08-10, `apps/api/app/api/v1/feedback.py` is a 0-byte stub, not
registered in the router. That gap is real and still open, tracked in
`EVALUATION_PLAN.md` phase 3 / `PHASE_2_3_ROADMAP.md` 1c.

The production version should cover two evaluation paths through one shared service:

```text
Offline benchmarks ─┐
                    ├─ Evaluation Service ─ Database ─ Evaluation API ─ Frontend
Real-time answers ──┘
```

The objective is to provide useful production visibility without building a general-purpose experimentation platform.

### 1. Core evaluation service

Implement the shared evaluation capability under:

```text
apps/api/app/ai/quality/evaluation/
  models.py
  service.py
  metrics.py
  ragas_adapter.py
  repository.py
```

The service should accept benchmark and real-time results through one common record.

| Field | Purpose |
|---|---|
| `evaluation_id` | Unique evaluation identifier |
| `source` | `benchmark` or `realtime` |
| `source_id` | Benchmark run, generation, or research-run identifier |
| `query` | User question |
| `answer` | Generated answer |
| `contexts` | Retrieved chunks supplied to generation |
| `citations` | Citations returned with the answer |
| `reference_answer` | Optional reference, normally available for benchmarks |
| `metrics` | Calculated metric results |
| `status` | Pending, running, completed, failed, or skipped |
| `model` | Generation model |
| `prompt_version` | Prompt version used |
| `latency_ms` | End-to-end latency |
| `cost_usd` | Generation cost |
| `created_at` | Evaluation timestamp |

PostgreSQL should store searchable evaluation records and aggregates. Detailed traces or large payloads can use the existing evaluation artifact storage.

### 2. Initial metric set

Start with the main quality and operational dimensions rather than every metric offered by Ragas.

| Metric | Benchmarks | Real-time answers | Method |
|---|:---:|:---:|---|
| Faithfulness | Yes | Yes | Ragas |
| Answer relevance | Yes | Yes | Ragas |
| Context precision | Yes | Yes | Ragas |
| Context recall | Yes | When a reference exists | Ragas |
| Citation correctness | Yes | Yes | ResearchMind custom evaluator |
| Answer correctness | Yes | When a reference exists | Ragas or custom evaluator |
| Latency | Yes | Yes | Existing generation statistics |
| Cost | Yes | Yes | Existing generation statistics |
| Error rate | Yes | Yes | Deterministic |
| User feedback | No | Yes | Existing feedback capability |

Context recall and answer correctness must be marked as unavailable when no reference exists. The system must not create artificial zero scores for unavailable metrics.

For real-time monitoring, an optional composite score can be calculated as:

```text
Live quality score =
  40% faithfulness
  25% answer relevance
  20% context precision
  15% citation correctness
```

The frontend must also show the individual metrics so the composite score does not hide the cause of a low result.

### 3. Benchmark integration

Keep the existing benchmark platform and add the evaluation service after each benchmark result.

```text
Run benchmark candidate
    ↓
Capture query, answer, contexts, citations, and reference
    ↓
EvaluationService.evaluate(...)
    ↓
Persist case-level scores
    ↓
Aggregate by benchmark and candidate
    ↓
Compare with the promoted baseline
```

The current deterministic metrics should remain as inexpensive engineering signals. Ragas metrics should supplement them rather than replace them.

Each benchmark run should expose:

| Result | Requirement |
|---|---|
| Candidate results | Model/provider and configuration under test |
| Quality metrics | Aggregate and case-level results |
| Operational metrics | Latency, cost, completion rate, and errors |
| Coverage | Evaluated, failed, and skipped case counts |
| Comparison | Change from the current baseline |
| Failure detail | Cases responsible for regressions |

A provider, quota, network, or evaluator failure must produce an explicit failed or partial status. It must not be represented as a valid quality score of zero.

### 4. Real-time answer evaluation

Ragas evaluation should not delay the answer shown to the user. Evaluation should run asynchronously after generation or research synthesis completes.

```text
User receives the answer
    ↓
Generation or research runtime submits an evaluation job
    ↓
Worker evaluates the answer asynchronously
    ↓
Results are persisted
    ↓
Frontend retrieves the evaluation status and scores
```

The runtime evaluation job should capture:

| Input | Source |
|---|---|
| Query | Generation or research request |
| Answer | Generation result or synthesized report |
| Contexts | Retrieved chunks used during generation |
| Citations | Structured citations returned to the user |
| Model and prompt | Generation metadata |
| Latency and cost | Existing generation statistics |
| Guardrail result | Existing guardrail report, when available |
| Feedback | Existing user-feedback record, when available |

Use the project's existing queue and worker infrastructure. Evaluation sampling should be configurable.

Recommended initial policy:

| Answer category | Evaluation policy |
|---|---|
| Development and staging | Evaluate all answers |
| Normal production traffic | Evaluate a configurable sample, initially 10–20% |
| Negative user feedback | Always evaluate |
| Guardrail-flagged answer | Always evaluate |
| Deep-research report | Evaluate all when volume and cost permit |

### 5. Evaluation API

Implement the currently empty `apps/api/app/api/v1/evaluation.py`.

| Endpoint | Purpose |
|---|---|
| `GET /evaluations/summary` | Benchmark and real-time quality overview |
| `GET /evaluations/trends` | Metric trends over a requested period |
| `GET /evaluations` | Paginated and filterable evaluation list |
| `GET /evaluations/{id}` | Case-level result, contexts, citations, and score explanations |
| `GET /evaluations/benchmarks` | Benchmark runs and candidate comparisons |
| `POST /evaluations/{id}/retry` | Retry a failed evaluation |
| `POST /evaluations/{id}/review` | Record a human review or correction |

The list and trend endpoints should support filters for source, model, status, metric threshold, feedback rating, research run, and date range.

Evaluation access should be restricted to authorized admin or engineering roles because records may include private queries, retrieved document content, and generated answers.

### 6. Frontend

Add an admin-only **Evaluation** section with three main views.

#### Evaluation overview

| Widget | Content |
|---|---|
| Overall quality | Current composite score and change |
| Faithfulness | Average and trend |
| Answer relevance | Average and trend |
| Citation correctness | Average and trend |
| Evaluation coverage | Evaluated answers divided by eligible answers |
| Failures | Failed, partial, and skipped evaluations |
| Cost and latency | Current values and trends |

#### Benchmark results

Display benchmark runs, dataset versions, candidate comparisons, regressions, and failed cases.

| Candidate | Faithfulness | Relevance | Citations | Latency | Cost | Result |
|---|---:|---:|---:|---:|---:|---|
| Candidate A | 0.91 | 0.84 | 0.96 | 850 ms | $0.0010 | Pass |
| Candidate B | 0.88 | 0.86 | 0.93 | 420 ms | $0.0003 | Warning |

#### Real-time quality

Display:

- Quality trends by day
- Scores grouped by model
- Low-scoring answers
- Negative-feedback correlation
- Evaluation coverage
- Guardrail flags
- Latency and cost trends

#### Evaluation details

Each evaluation should show:

- User question
- Generated answer
- Retrieved contexts
- Citations
- Individual scores and explanations
- Model and prompt version
- Latency and cost
- Guardrail results
- User feedback
- Retry and human-review actions

### 7. Scope intentionally deferred

The first release should not include:

| Deferred capability | Reason |
|---|---|
| General-purpose experiment orchestration | Not required for benchmark and runtime visibility |
| Multiple evaluation vendors | One Ragas adapter plus custom metrics is sufficient initially |
| Complex statistical testing | Add after the dataset and baselines stabilize |
| Synthetic knowledge-graph generation | Useful later for dataset expansion, not required for the MVP |
| Automated baseline promotion | Baseline changes should initially require an explicit human decision |
| Custom evaluation DSL | Typed Python models and configuration are sufficient |
| Full distributed trace viewer | Existing trace identifiers and detail pages cover the initial need |
| Evaluation of all production traffic indefinitely | Sampling controls cost and data exposure |

### 8. Delivery plan

| Phase | Work | Estimated effort |
|---|---|---:|
| 1 — Evaluation foundation | Database models, common schema, Ragas adapter, core metrics, and failure semantics | 3–5 days |
| 2 — Benchmark integration | Connect existing benchmark runners and persist case-level and aggregate results | 2–3 days |
| 3 — Real-time integration | Add asynchronous jobs, worker execution, sampling, and forced-evaluation rules | 3–5 days |
| 4 — API | Implement summary, trends, list, detail, benchmark, retry, and review endpoints | 3–4 days |
| 5 — Frontend | Build overview, benchmark, real-time, and detail views | 5–7 days |
| 6 — Production hardening | Tests, access control, data redaction, configuration, and deployment validation | 3–5 days |

The expected MVP is approximately three to five development weeks, depending on the reusable frontend chart and admin infrastructure already available.

### 9. MVP completion criteria

The initial production evaluation system is complete when:

| Criterion | Expected result |
|---|---|
| Shared evaluation service | Benchmarks and real-time answers use the same service and result schema |
| Ragas integration | Core RAG metrics run through a replaceable adapter |
| Benchmark visibility | Existing benchmarks persist results and appear in the frontend |
| Real-time visibility | Sampled answers are evaluated asynchronously and appear in the frontend |
| Failure integrity | Failed or unavailable evaluations are never reported as valid zero scores |
| API coverage | Summary, trends, list, detail, benchmark, retry, and review operations are available |
| Frontend coverage | Overview, benchmark, real-time, and evaluation-detail views are available |
| Security | Evaluation data is restricted to authorized roles |
| Operational safety | Sampling and judge-cost configuration can be changed without code changes |

This scope provides the main evaluation capabilities ResearchMind needs: benchmark comparison, real-time answer monitoring, RAG-quality metrics, operational metrics, failure analysis, and frontend visibility—without introducing a large experimentation platform.
