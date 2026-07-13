# Retrieval

## Dataset

- **Name:** research-papers
- **Documents:** 5
- **Generated:** `2026-07-13T14:31:38.759902+00:00`

---

## Comparison

| Metric | dense | sparse |
|---|---:|---:|
| Avg Latency Ms | 322.44 | 11.65 |
| Mrr | 0.95 | 0.975 |
| P95 Latency Ms | 419.01 | 22.84 |
| P99 Latency Ms | 419.01 | 22.84 |
| Precision At 10 | 0.1 | 0.1 |
| Precision At 5 | 0.2 | 0.2 |
| Queries Evaluated | 20 | 20 |
| Recall At 10 | 1.0 | 1.0 |
| Recall At 20 | 1.0 | 1.0 |
| Recall At 5 | 1.0 | 1.0 |

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
| Avg Latency Ms | 322.44 |
| P95 Latency Ms | 419.01 |
| P99 Latency Ms | 419.01 |

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
| Avg Latency Ms | 11.65 |
| P95 Latency Ms | 22.84 |
| P99 Latency Ms | 22.84 |

### Notes

- **top_k_evaluated**: 20
- **cost_model**: FastEmbed SPLADE: local CPU inference, no marginal cost.
- **recall_at_10_by_category**: {'semantic': 1.0, 'acronym': 1.0, 'exact_keyword': 1.0, 'code_entity': 1.0}
