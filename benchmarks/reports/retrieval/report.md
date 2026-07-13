# Retrieval

## Dataset

- **Name:** research-papers
- **Documents:** 5
- **Generated:** `2026-07-13T15:28:46.813776+00:00`

---

## Comparison

| Metric | dense | sparse | hybrid |
|---|---:|---:|---:|
| Avg Latency Ms | 316.84 | 10.53 | 324.42 |
| Mrr | 0.95 | 0.975 | 0.925 |
| P95 Latency Ms | 440.41 | 29.28 | 522.82 |
| P99 Latency Ms | 440.41 | 29.28 | 522.82 |
| Precision At 10 | 0.1 | 0.1 | 0.1 |
| Precision At 5 | 0.2 | 0.2 | 0.2 |
| Queries Evaluated | 20 | 20 | 20 |
| Recall At 10 | 1.0 | 1.0 | 1.0 |
| Recall At 20 | 1.0 | 1.0 | 1.0 |
| Recall At 5 | 1.0 | 1.0 | 1.0 |

---

## dense

| Metric | Value |
|---|---:|
| Queries Evaluated | 20 |
| Recall At 5 | 1.0 |
| Recall At 10 | 1.0 |
| Recall At 20 | 1.0 |
| Precision At 5 | 0.2 |
| Precision At 10 | 0.1 |
| Mrr | 0.95 |
| Avg Latency Ms | 316.84 |
| P95 Latency Ms | 440.41 |
| P99 Latency Ms | 440.41 |

### Notes

- **top_k_evaluated**: 20
- **cost_model**: Voyage AI query embedding: paid, per-token API call.
- **recall_at_10_by_category**: {'semantic': 1.0, 'acronym': 1.0, 'exact_keyword': 1.0, 'code_entity': 1.0}

## sparse

| Metric | Value |
|---|---:|
| Queries Evaluated | 20 |
| Recall At 5 | 1.0 |
| Recall At 10 | 1.0 |
| Recall At 20 | 1.0 |
| Precision At 5 | 0.2 |
| Precision At 10 | 0.1 |
| Mrr | 0.975 |
| Avg Latency Ms | 10.53 |
| P95 Latency Ms | 29.28 |
| P99 Latency Ms | 29.28 |

### Notes

- **top_k_evaluated**: 20
- **cost_model**: FastEmbed SPLADE: local CPU inference, no marginal cost.
- **recall_at_10_by_category**: {'semantic': 1.0, 'acronym': 1.0, 'exact_keyword': 1.0, 'code_entity': 1.0}

## hybrid

| Metric | Value |
|---|---:|
| Queries Evaluated | 20 |
| Recall At 5 | 1.0 |
| Recall At 10 | 1.0 |
| Recall At 20 | 1.0 |
| Precision At 5 | 0.2 |
| Precision At 10 | 0.1 |
| Mrr | 0.925 |
| Avg Latency Ms | 324.42 |
| P95 Latency Ms | 522.82 |
| P99 Latency Ms | 522.82 |

### Notes

- **top_k_evaluated**: 20
- **cost_model**: Voyage AI + FastEmbed SPLADE (dense API cost plus local sparse inference), fused in-process via RRF.
- **recall_at_10_by_category**: {'semantic': 1.0, 'acronym': 1.0, 'exact_keyword': 1.0, 'code_entity': 1.0}
