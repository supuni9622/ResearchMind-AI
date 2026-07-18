# Retrieval

## Dataset

- **Name:** research-papers
- **Documents:** 5
- **Generated:** `2026-07-18T10:04:24.556794+00:00`

---

## Comparison

| Metric | dense | sparse | hybrid |
|---|---:|---:|---:|
| Avg Latency Ms | 318.38 | 11.53 | 342.94 |
| Mrr | 0.95 | 0.975 | 0.925 |
| Ndcg At 10 | 0.9631 | 0.9815 | 0.9446 |
| Ndcg At 5 | 0.9631 | 0.9815 | 0.9446 |
| P95 Latency Ms | 446.87 | 21.15 | 494.23 |
| P99 Latency Ms | 446.87 | 21.15 | 494.23 |
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
| Ndcg At 5 | 0.9631 |
| Ndcg At 10 | 0.9631 |
| Mrr | 0.95 |
| Avg Latency Ms | 318.38 |
| P95 Latency Ms | 446.87 |
| P99 Latency Ms | 446.87 |

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
| Ndcg At 5 | 0.9815 |
| Ndcg At 10 | 0.9815 |
| Mrr | 0.975 |
| Avg Latency Ms | 11.53 |
| P95 Latency Ms | 21.15 |
| P99 Latency Ms | 21.15 |

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
| Ndcg At 5 | 0.9446 |
| Ndcg At 10 | 0.9446 |
| Mrr | 0.925 |
| Avg Latency Ms | 342.94 |
| P95 Latency Ms | 494.23 |
| P99 Latency Ms | 494.23 |

### Notes

- **top_k_evaluated**: 20
- **cost_model**: Voyage AI + FastEmbed SPLADE (dense API cost plus local sparse inference), fused in-process via RRF.
- **recall_at_10_by_category**: {'semantic': 1.0, 'acronym': 1.0, 'exact_keyword': 1.0, 'code_entity': 1.0}
