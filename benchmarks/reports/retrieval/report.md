# Retrieval

## Dataset

- **Name:** research-papers
- **Documents:** 50
- **Generated:** `2026-08-11T18:59:16.154337+00:00`

## Provenance

- **Git commit:** `aa6d110fee2fb8324fd2ec807586e6e4c7189a38`
- **Branch:** `researchmind-v2`
- **Dataset version:** `1.0`
- **Benchmark version:** `1.0.0`

---

## Comparison

| Metric | dense | sparse | hybrid |
|---|---:|---:|---:|
| Avg Latency Ms | 359.18 | 12.21 | 422.91 |
| Hit Rate At 10 | 0.9875 | 0.9938 | 1.0 |
| Hit Rate At 5 | 0.975 | 0.9938 | 1.0 |
| Mrr | 0.942 | 0.9677 | 0.9615 |
| Ndcg At 10 | 0.9462 | 0.9712 | 0.9683 |
| Ndcg At 5 | 0.9425 | 0.9712 | 0.9683 |
| P95 Latency Ms | 520.77 | 14.22 | 745.23 |
| P99 Latency Ms | 992.53 | 17.87 | 933.07 |
| Precision At 10 | 0.1175 | 0.12 | 0.12 |
| Precision At 5 | 0.2325 | 0.24 | 0.24 |
| Queries Evaluated | 160 | 160 | 160 |
| Recall At 10 | 0.9792 | 0.9906 | 0.9953 |
| Recall At 20 | 0.9792 | 0.9906 | 0.9953 |
| Recall At 5 | 0.9667 | 0.9906 | 0.9953 |

---

## dense

| Metric | Value |
|---|---:|
| Queries Evaluated | 160 |
| Recall At 5 | 0.9667 |
| Recall At 10 | 0.9792 |
| Recall At 20 | 0.9792 |
| Precision At 5 | 0.2325 |
| Precision At 10 | 0.1175 |
| Ndcg At 5 | 0.9425 |
| Ndcg At 10 | 0.9462 |
| Hit Rate At 5 | 0.975 |
| Hit Rate At 10 | 0.9875 |
| Mrr | 0.942 |
| Avg Latency Ms | 359.18 |
| P95 Latency Ms | 520.77 |
| P99 Latency Ms | 992.53 |

### Notes

- **top_k_evaluated**: 20
- **cost_model**: Voyage AI query embedding: paid, per-token API call.
- **recall_at_10_by_category**: {'semantic': 0.9801, 'acronym': 0.9615, 'exact_keyword': 0.9773, 'code_entity': 1.0}

## sparse

| Metric | Value |
|---|---:|
| Queries Evaluated | 160 |
| Recall At 5 | 0.9906 |
| Recall At 10 | 0.9906 |
| Recall At 20 | 0.9906 |
| Precision At 5 | 0.24 |
| Precision At 10 | 0.12 |
| Ndcg At 5 | 0.9712 |
| Ndcg At 10 | 0.9712 |
| Hit Rate At 5 | 0.9938 |
| Hit Rate At 10 | 0.9938 |
| Mrr | 0.9677 |
| Avg Latency Ms | 12.21 |
| P95 Latency Ms | 14.22 |
| P99 Latency Ms | 17.87 |

### Notes

- **top_k_evaluated**: 20
- **cost_model**: FastEmbed SPLADE: local CPU inference, no marginal cost.
- **recall_at_10_by_category**: {'semantic': 0.9776, 'acronym': 1.0, 'exact_keyword': 1.0, 'code_entity': 1.0}

## hybrid

| Metric | Value |
|---|---:|
| Queries Evaluated | 160 |
| Recall At 5 | 0.9953 |
| Recall At 10 | 0.9953 |
| Recall At 20 | 0.9953 |
| Precision At 5 | 0.24 |
| Precision At 10 | 0.12 |
| Ndcg At 5 | 0.9683 |
| Ndcg At 10 | 0.9683 |
| Hit Rate At 5 | 1.0 |
| Hit Rate At 10 | 1.0 |
| Mrr | 0.9615 |
| Avg Latency Ms | 422.91 |
| P95 Latency Ms | 745.23 |
| P99 Latency Ms | 933.07 |

### Notes

- **top_k_evaluated**: 20
- **cost_model**: Voyage AI + FastEmbed SPLADE (dense API cost plus local sparse inference), fused in-process via RRF.
- **recall_at_10_by_category**: {'semantic': 0.9888, 'acronym': 1.0, 'exact_keyword': 1.0, 'code_entity': 1.0}
