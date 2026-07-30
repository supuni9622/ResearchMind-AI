# RAG Evaluation — Current Implementation vs Industry Criteria

## Purpose and scope

This document evaluates ResearchMind AI's current RAG evaluation implementation against the concepts in the supplied reference images. The comparison is framework-neutral: it evaluates architecture, metric semantics, datasets, regression workflow, and production use rather than whether a particular library such as RAGAS is used.

The assessment is based on the current code and checked-in benchmark artifacts. It distinguishes:

- **Offline evaluation capability** — benchmarks that engineers can run intentionally.
- **Runtime validation** — checks performed while generating an answer.
- **Production evaluation operations** — continuously collecting representative examples, scoring them, detecting regressions, and exposing results.

These are related but are not interchangeable.

## Status legend

| Status | Meaning |
|---|---|
| **Aligned** | The concept is implemented and substantially matches the industry criterion. |
| **Partially aligned** | A useful implementation exists, but its scope, metric semantics, data, or operational integration is incomplete. |
| **Gap** | No effective current implementation was found. |
| **Not essential now** | Useful in some systems, but not required for the platform's present maturity or use cases. |

## Executive assessment

| Area | Assessment | Summary |
|---|---|---|
| Separation of retrieval and generation evaluation | **Aligned** | Retrieval and generation have separate datasets, benchmark implementations, metrics, and reports. Generation receives fixed context, correctly isolating generation behavior from retrieval. |
| Retrieval metric coverage | **Mostly aligned** | Recall@K, Precision@K, MRR, and nDCG@K are implemented. Explicit Hit Rate and semantic context relevancy are missing. Current judgments are document-level rather than chunk-level. |
| Generation metric coverage | **Partially aligned** | Faithfulness, groundedness, answer relevance, completeness, citation accuracy, hallucination rate, latency, and cost exist. Most quality metrics are lexical proxies and do not provide claim-level entailment or robust answer correctness. |
| Evaluation dataset design | **Partially aligned** | Datasets are structured, curated, versioned, and include queries and reference judgments. They are small, single-domain benchmark sets rather than representative production-derived golden sets. |
| End-to-end RAG evaluation | **Gap** | Retrieval and generation can be benchmarked independently, but the complete live RAG path is not registered as an end-to-end benchmark. |
| Regression detection | **Aligned offline; gap in automation** | Metric-specific thresholds, comparison reports, and non-zero failure exits are implemented. The check is opt-in and was not found in CI or a scheduled evaluation workflow. |
| Diagnosis and reporting | **Partially aligned** | Reports contain per-candidate metrics, provenance, latency, cost, and retrieval category breakdowns. They do not retain sufficiently rich per-example failure analysis for a full measure → diagnose → fix loop. |
| Production evaluation service | **Gap** | Evaluation API/runtime packages are scaffolded but not wired into the active API. The code explicitly states that no runtime emits or consumes evaluation artifacts today. |
| Overall industry alignment | **Moderate** | The platform has a strong engineering benchmark foundation. The main shortfall is operationalization: representative data, stronger metric semantics, end-to-end evaluation, CI gates, and production feedback loops. |

## Current evaluation architecture

| Stage | Current implementation | Evidence | Assessment |
|---|---|---|---|
| Curated benchmark corpus | Canonical research-paper documents and query sets live under `benchmarks/datasets/research-papers`. | [`benchmarks/datasets/README.md`](../../benchmarks/datasets/README.md), [`retrieval_queries.json`](../../benchmarks/datasets/research-papers/retrieval_queries.json), [`generation_queries.json`](../../benchmarks/datasets/research-papers/generation_queries.json) | **Aligned for an engineering baseline** |
| Retrieval evaluation | Builds an isolated benchmark index and compares dense, sparse, and hybrid retrieval using relevance judgments. | [`benchmarks/retrieval/benchmark.py`](../../benchmarks/retrieval/benchmark.py), [`metrics.py`](../../benchmarks/retrieval/metrics.py) | **Aligned** |
| Generation evaluation | Supplies known context directly to each provider and scores the generated answer, isolating generation from retrieval. | [`benchmarks/generation/benchmark.py`](../../benchmarks/generation/benchmark.py), [`dataset.py`](../../benchmarks/generation/dataset.py) | **Aligned** |
| Reports | Produces canonical JSON and Markdown reports with dataset and source-control provenance. | [`benchmarks/common/report_generator.py`](../../benchmarks/common/report_generator.py), [`benchmarks/models/report.py`](../../benchmarks/models/report.py) | **Aligned** |
| Regression comparison | Compares the current report with the prior report and applies per-metric thresholds. | [`benchmarks/regression/detector.py`](../../benchmarks/regression/detector.py), [`thresholds.py`](../../benchmarks/regression/thresholds.py) | **Aligned offline** |
| Runtime answer validation | Generation runtime includes guardrails and validation policies that can reject or regenerate weak output. | [`apps/api/app/ai/runtime/generation/validation`](../../apps/api/app/ai/runtime/generation/validation), [`apps/api/app/ai/guardrails`](../../apps/api/app/ai/guardrails) | **Complementary, not a replacement for evaluation** |
| Evaluation artifacts | Models, readers, writers, and builders exist for future persisted evaluation datasets and results. | [`apps/api/app/ai/artifacts/evaluation`](../../apps/api/app/ai/artifacts/evaluation) | **Scaffold only** |
| Evaluation service/API | `quality/evaluation` is empty, and the evaluation route is not included by the central API router. | [`apps/api/app/ai/quality/evaluation`](../../apps/api/app/ai/quality/evaluation), [`apps/api/app/api/v1/api.py`](../../apps/api/app/api/v1/api.py) | **Gap** |

## Retrieval-level evaluation

The reference criterion asks: **“Did we give the LLM the right material?”**

### Metric alignment

| Industry criterion | Current implementation | Alignment | Misalignment / gap | Importance |
|---|---|---|---|---|
| Recall@K / Context Recall | `recall_at_k` is calculated at K=5, 10, and 20. | **Aligned conceptually** | Relevance is judged at **document level**. Retrieving any chunk from a relevant document counts as a hit even if the chunk itself does not contain the needed evidence. This can overstate usable context recall. | **High** |
| Precision@K / Context Precision | `precision_at_k` is calculated at K=5 and 10. | **Aligned conceptually** | It measures relevant **unique source documents**, not the proportion of relevant chunks actually supplied to the LLM. In the current five-document corpus, one relevant document with K=5 mechanically produces `0.2`, making it a weak proxy for context noise. | **High** |
| MRR | Mean reciprocal rank is calculated from the first relevant document. | **Aligned** | The same document-level limitation applies. A high-ranked chunk from the right document may still be the wrong passage. | **Medium** |
| Hit Rate | Not emitted as a named metric. | **Gap** | It can be derived as the proportion of queries with Recall@K > 0, but it is not calculated, reported, thresholded, or trended explicitly. | **Medium** |
| Context Relevancy | Precision@K is the nearest current proxy. | **Partially aligned** | There is no semantic or judge-based assessment of whether each returned chunk is useful for the specific question. | **High** |
| Rank-sensitive retrieval quality | nDCG@5 and nDCG@10 are implemented. | **Aligned and exceeds the supplied baseline** | Judgments are binary and document-level; graded chunk relevance is not supported. | **Medium** |
| Query-slice analysis | Recall@10 is reported by semantic, acronym, exact-keyword, and code-entity categories. | **Aligned** | Only one domain is represented, and generation metrics are not similarly sliced by difficulty or failure type. | **Medium** |
| Retrieval latency | Average, p95, and p99 latency are measured. | **Aligned and production-relevant** | No throughput/concurrency or production traffic distribution is part of this RAG-quality benchmark. | **Medium** |
| Retrieval cost | Candidate cost model is described in report notes. | **Partially aligned** | Retrieval cost is descriptive rather than consistently measured and regression-thresholded. | **Low–medium** |

### Important semantic limitation

The retrieval benchmark currently answers:

> “Did the retriever return a chunk from a document known to be relevant?”

The industry criterion is stronger:

> “Did the retriever return the exact evidence chunks needed to answer the question, and rank them early enough to be used?”

The present implementation is a valid first-stage information-retrieval benchmark, but it should not be interpreted as proof that the final prompt contains complete and low-noise evidence. The dataset itself documents this limitation in [`benchmarks/retrieval/dataset.py`](../../benchmarks/retrieval/dataset.py).

### Retrieval strengths already present

| Strength | Why it matters |
|---|---|
| Real retrieval execution against an isolated vector index | Measures actual implementation behavior rather than mocked rankings. |
| Dense, sparse, and hybrid candidates use the same corpus and judgments | Enables fair architectural comparison. |
| Multiple K values | Exposes recall/precision trade-offs and supports tuning the amount of supplied context. |
| nDCG and MRR | Measures ordering, which is especially important before reranking and context truncation. |
| Category-level recall | Provides an initial diagnostic view of which query styles fail. |
| Reranking and metadata-filtering benchmarks | Allows retrieval components to be evaluated independently rather than treating RAG as one opaque score. |

## Generation-level evaluation

The reference criterion asks: **“Given the right material, did the LLM use it correctly?”**

### Metric alignment

| Industry criterion | Current implementation | Alignment | Misalignment / gap | Importance |
|---|---|---|---|---|
| Faithfulness | Each answer sentence is marked supported when enough significant words overlap with the context. | **Partially aligned** | Lexical overlap is not claim entailment. A sentence can reuse context words while reversing a fact, changing a number, or inventing a relationship. The metric also cannot reliably handle paraphrases. | **Critical** |
| Groundedness | Measures the fraction of significant answer words found in context. | **Partially aligned** | This is a reproducible grounding proxy, but it measures vocabulary provenance rather than factual support. It can reward copied yet incorrect statements and penalize correct paraphrases. | **High** |
| Answer Relevancy | Measures the fraction of significant query words appearing in the answer. | **Partially aligned** | Keyword coverage is much weaker than semantic question-answer relevance. Repeating query terms can score well without resolving the user's need. | **High** |
| Answer Correctness | `completeness` compares answer terms with `expected_answer`. | **Partial / substantial gap** | Completeness measures reference-term coverage and does not penalize incorrect extra claims. There is no explicit correctness metric combining factual agreement and semantic equivalence to a human reference answer. | **Critical for golden-set evaluation** |
| Context Utilization | No dedicated metric. | **Gap** | Current groundedness indicates word overlap, but not whether all relevant supplied evidence was used or whether the answer defaulted to generic knowledge. | **Medium–high** |
| Citation quality | `citation_accuracy` checks expected filenames against structured citations or answer text. | **Partially aligned** | This establishes source presence, not claim-level citation correctness, citation completeness, or whether the cited passage actually supports each claim. | **High for research output** |
| Hallucination rate | Defined as `1 - average(faithfulness)`. | **Partially aligned** | It inherits the lexical faithfulness proxy's limitations and is an aggregate inversion, not an independently validated hallucination rate. | **High** |
| Completeness | Reference-answer term coverage is measured explicitly. | **Aligned as a lightweight proxy** | It should remain named “completeness,” not be treated as full answer correctness. | **Medium** |
| Latency | Average and p95 generation latency are reported. | **Aligned** | p99 is thresholded generically but is not currently emitted by generation. | **Medium** |
| Cost | Average cost, cost/query, and projected cost/1K queries are reported. | **Aligned** | Provider failures currently appear as zero-cost/zero-quality candidates, which can distort comparisons unless failures are separated from valid scores. | **Medium** |

### What runtime validation adds

| Runtime capability | Contribution | Evaluation limitation |
|---|---|---|
| Faithfulness/evidence guardrails | Can stop or regenerate an unsupported response before returning it. | Does not produce a representative aggregate quality score across a controlled test set. |
| Structured output/schema validation | Improves format reliability. | Does not measure factual correctness or retrieval quality. |
| Citation validation | Protects citation integrity in a live response. | Does not replace offline claim-to-source evaluation and trend analysis. |
| Regeneration policies | Gives the system a correction path. | The evaluation suite still needs to measure first-pass quality, retry rate, final quality, latency, and cost. |

Runtime validation and offline evaluation are therefore **complementary controls**. The platform has useful runtime controls, but they should not be counted as complete RAG evaluation coverage.

## Dataset and test-set alignment

### Dataset fields

| Reference field | Retrieval dataset | Generation dataset | Assessment |
|---|---|---|---|
| `question` | `query` | `query` | **Aligned** |
| Retrieved `contexts` | Produced by live retrieval during retrieval benchmark, but not stored as a canonical per-example evaluation field | Fixed `context` supplied directly | **Partially aligned** |
| Generated `answer` | Not applicable | Produced during execution | **Aligned during run** |
| Human reference / `ground_truth` | Relevant document filenames | `expected_answer` and expected citations | **Partially aligned** |
| Query/category metadata | Semantic, acronym, exact keyword, code entity | Query ID only | **Partial** |
| Dataset version | Explicit `version` field | Explicit `version` field | **Aligned** |

### Dataset quality and representativeness

| Criterion | Current state | Assessment | Gap |
|---|---|---|---|
| Curated and deterministic | Inputs and relevance/reference judgments are checked into source control. | **Aligned** | None for baseline engineering comparison. |
| Versioned rather than silently edited | Dataset guidance explicitly requires new versions instead of modifying historical inputs. | **Aligned** | A formal dataset registry/changelog could improve enforcement. |
| Real user query sampling | The sets contain authored research-paper questions. | **Gap** | No pipeline was found for sampling and de-identifying production queries. |
| Human/domain-expert verification | References appear curated, but reviewer identity, review status, and adjudication are not modeled. | **Partial** | Add provenance for who verified judgments and when. |
| Sufficient breadth | 20 retrieval queries and 13 generation queries over five research documents. | **Gap for production confidence** | Too small and too narrow to represent ambiguity, follow-ups, multi-hop research, citation edge cases, access filtering, empty retrieval, adversarial inputs, and long contexts. |
| Topic-area slices | Retrieval categories exist. | **Partial** | No separate domain/topic test suites or generation slices. |
| Hard negatives | Not explicitly labeled. | **Gap** | Add confusable passages and near-match documents to test precision and ranking. |
| Chunk-level relevance | Relevance is document-level. | **Gap** | Add exact relevant chunk IDs or evidence spans, optionally with graded relevance. |
| End-to-end examples | Retrieval and generation sets are deliberately isolated. | **Gap** | Add question → actual retrieved chunks → final answer → ground truth examples for complete pipeline evaluation. |

## Regression, continuous evaluation, and diagnosis

| Industry criterion | Current implementation | Alignment | Gap |
|---|---|---|---|
| Compare against a baseline | `RegressionDetector` compares current and previous canonical reports. | **Aligned** | Baseline lifecycle and promotion are file-based rather than governed. |
| Metric-specific thresholds | Retrieval quality, generation quality, hallucination, latency, and cost thresholds are defined. | **Aligned** | Hit rate, context utilization, answer correctness, and citation faithfulness have no thresholds because they are not measured. |
| Fail a build on regression | Runner exits non-zero when `--check-regression` detects a breach. | **Aligned in capability** | No CI workflow invocation was found, so it is not an enforced quality gate. |
| Run after model/prompt/embedding/chunking changes | Can be run manually against current code and provider versions. | **Partial** | No automatic change-aware or per-PR execution was found. |
| Scheduled production evaluation | No active evaluation runtime/service was found. | **Gap** | Add scheduled evaluation and alerting based on stable production-derived samples. |
| Version results with code/model/data provenance | Reports include Git commit/branch, dataset version, benchmark version, and model versions where available. | **Aligned** | Prompt/config/index versions should also be captured consistently. |
| Diagnose failures per example | Aggregate metrics and some category slices are reported. | **Partial** | Canonical reports do not provide a rich per-example record containing query, retrieved chunks/ranks, answer, references, individual metric verdicts, and failure classification. |
| Measure → diagnose → fix → remeasure loop | Manual benchmark/regression workflow supports the loop. | **Partial** | No issue workflow, dashboard, owner/SLO, or automated re-evaluation closes the loop operationally. |

## End-to-end and production alignment

| Component | Current status | Industry alignment |
|---|---|---|
| Offline retrieval benchmark | Implemented and has checked-in reports. | **Strong** |
| Offline generation benchmark | Implemented and has checked-in reports. | **Moderate**, because scorer semantics are lightweight lexical proxies. |
| Offline end-to-end RAG benchmark | `PipelineBenchmark` is left under “Future benchmarks” and is not registered by the benchmark factory. | **Gap** |
| Production evaluation API | An evaluation module/file exists but is not included by the central router. | **Gap** |
| Evaluation runtime | Quality/evaluation is an empty package. Evaluation artifact documentation says no runtime emits or consumes it. | **Gap** |
| Persisted evaluation artifacts | Generic artifact models/readers/writers/builders exist. | **Foundation only** |
| User feedback as an evaluation signal | No active feedback route was found in the central API. | **Gap** |
| Online quality monitoring | General observability and LangSmith metric feedback adapters exist. | **Partial foundation**, not a RAG-quality monitoring loop. |
| Failure replay | Generation artifacts and replay-oriented infrastructure provide a useful debugging base. | **Partial alignment** |

## Misalignments that can lead to false confidence

| Risk | Why it matters | Current exposure |
|---|---|---|
| Document-level relevance reported as context precision/recall | A hit from the correct PDF does not prove the answer-bearing chunk was retrieved. | **High** |
| Lexical overlap reported as faithfulness | Contradictions and altered numbers can still share most words with context. | **High** |
| Completeness treated as correctness | An answer can include expected terms and still make incorrect additional claims. | **High** |
| Small single-domain test set | High scores may not generalize to the platform's real research workflows. | **High** |
| Aggregate-only reports | Averages hide systematic failures in a query type, document type, or provider. | **Medium–high** |
| Failed providers represented by zero metrics | Availability failures become mixed with quality measurements, making candidate comparison harder to interpret. | **Medium** |
| Optional regression execution | A regression detector that is not in CI or scheduled operations does not prevent release regressions. | **High** |
| No complete-path benchmark | Individually good retrieval and generation scores do not prove the composed RAG pipeline works. | **Critical** |

## Gap prioritization

Not every reference capability needs to be implemented immediately. The following sequence covers the important industry-standard controls without overbuilding.

### Priority 0 — Required for trustworthy RAG evaluation

| Improvement | Why this is the next important step | Suggested acceptance condition |
|---|---|---|
| Add an end-to-end RAG golden-set benchmark | This is the largest architectural gap; it measures the composed system users actually experience. | Each example records query, actual ranked chunks, final answer, citations, ground truth, and per-stage metrics. |
| Move retrieval judgments to chunk/evidence-span level | Makes Recall@K, Precision@K, MRR, Hit Rate, and context relevancy reflect usable evidence. | Relevant chunk IDs or evidence spans exist for every golden query; document-level metrics remain only as secondary diagnostics. |
| Add explicit Hit Rate@K | Provides the baseline sanity check from the reference criteria. | Report and regression threshold for Hit@5/10, including category slices. |
| Add robust faithfulness and answer-correctness evaluation | Lexical proxies are not sufficient for production confidence. | Claim-level support/contradiction checking and correctness against a human reference; retain deterministic scorers as cheap secondary signals. |
| Build a representative, reviewed golden set | Prevents benchmark overfitting to five research papers. | Versioned set includes real, de-identified query patterns, domain review metadata, difficult negatives, failure cases, and expected evidence. |
| Enforce regression checks in CI | Turns the existing detector into an actual release control. | Relevant changes run a stable offline subset; breaches fail the check and publish a comparison report. |

### Priority 1 — Strong production maturity

| Improvement | Value | Suggested scope |
|---|---|---|
| Persist per-example evaluation traces | Enables root-cause analysis rather than only viewing averages. | Store route/config, retrieved IDs and ranks, prompt/context, answer, citations, metric verdicts, latency, cost, and errors. |
| Add context utilization and claim-level citation metrics | Detects generic answers and unsupported attribution. | Measure evidence coverage, citation correctness, citation completeness, and unsupported-claim rate. |
| Introduce topic, difficulty, and workflow slices | Prevents healthy aggregate scores from hiding weak cohorts. | At minimum: simple factual, ambiguous/follow-up, multi-document, multi-hop, no-answer, citation-heavy, and access-filtered queries. |
| Add human evaluation workflow | Needed for nuanced usefulness and research quality that automated metrics miss. | Rubrics for correctness, completeness, usefulness, citation quality, and reasoning quality with reviewer provenance. |
| Operationalize evaluation artifacts and API | Connects existing scaffolding to scheduled and on-demand runs. | Evaluation job lifecycle, dataset/version selection, persisted results, comparisons, and access-controlled result APIs. |
| Monitor production quality trends | Detects drift after deployment. | Scheduled samples, quality dashboards, alert thresholds, and links from aggregate changes to example traces. |

### Priority 2 — Valuable but can wait

| Improvement | Why it is not mandatory immediately |
|---|---|
| Multiple independent judge models | Useful for reducing judge bias, but a strong golden set and claim-level scorer should come first. |
| Pairwise model/prompt preference evaluation | Valuable for model selection after core correctness and grounding gates are reliable. |
| Statistical confidence intervals and significance testing | Important as datasets grow; less meaningful with the current 13–20-example sets. |
| Fully automated production-query labeling | High operational complexity; begin with reviewed sampling and active-learning queues. |
| Dedicated RAGAS integration | Framework choice is secondary. Equivalent metric semantics and good evaluation data matter more. |

## Recommended target evaluation model

| Evaluation layer | Required inputs | Core metrics | Primary diagnosis |
|---|---|---|---|
| Retrieval | Query, ranked chunk IDs, relevant chunk/evidence IDs, metadata | Hit@K, Recall@K, Precision@K, MRR, nDCG@K, context relevancy, latency | Missing evidence, noisy context, poor ranking, filtering failure |
| Generation with fixed context | Query, controlled context, answer, human reference, expected citations | Faithfulness, answer relevancy, answer correctness, completeness, context utilization, citation correctness | Prompt/model failed despite correct evidence |
| End-to-end RAG | Query, actual retrieved chunks, final answer, ground truth/evidence | All retrieval and generation metrics plus task success, latency, cost, fallback/retry rate | Whether failure originated in retrieval, context construction, generation, or validation |
| Production/online | De-identified sampled traces, user feedback, evaluator verdicts | Quality trends by slice, failure rate, no-answer rate, citation defects, latency/cost, user outcome | Drift, regressions, new query classes, operational failures |

## Final conclusion

ResearchMind AI is **well aligned with the foundational structure of industry RAG evaluation**:

- retrieval and generation are evaluated separately;
- core retrieval metrics and rank-sensitive metrics exist;
- generation quality, latency, cost, and citations have baseline measurements;
- datasets and reports are versioned with useful provenance;
- regression thresholds and failure behavior are implemented.

The platform is **not yet fully aligned with production RAG evaluation standards** because:

- retrieval relevance is document-level rather than evidence-chunk-level;
- generation quality relies on lightweight lexical proxies;
- explicit Hit Rate, answer correctness, and context utilization are missing;
- the benchmark corpus is small and not representative of production traffic;
- no registered end-to-end RAG benchmark exists;
- regression checks are not visibly enforced in CI;
- evaluation runtime/API/artifact integration remains scaffolded.

The correct next move is not to implement every metric or adopt a particular framework. It is to operationalize the important controls already implied by the architecture: **a reviewed end-to-end golden set, chunk-level evidence judgments, trustworthy faithfulness/correctness scoring, per-example diagnostics, and enforced regression gates**.

