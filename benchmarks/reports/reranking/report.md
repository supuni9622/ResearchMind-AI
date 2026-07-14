# Reranking

## Dataset

- **Name:** research-papers
- **Documents:** 5
- **Generated:** `2026-07-14T09:47:56.583746+00:00`

---

## Comparison

| Metric | hybrid_only | hybrid_cross_encoder | hybrid_voyage |
|---|---:|---:|---:|
| Avg Latency Ms | 381.36 | 625.37 | 753.86 |
| Mrr | 0.925 | 1.0 | 0.95 |
| Ndcg At 5 | 0.9446 | 1.0 | 0.9631 |
| P95 Latency Ms | 547.83 | 1100.08 | 922.9 |
| P99 Latency Ms | 547.83 | 1100.08 | 922.9 |
| Queries Evaluated | 20 | 20 | 20 |
| Recall At 5 | 1.0 | 1.0 | 1.0 |

---

## hybrid_only

| Metric | Value |
|---|---:|
| Queries Evaluated | 20 |
| Recall At 5 | 1.0 |
| Mrr | 0.925 |
| Ndcg At 5 | 0.9446 |
| Avg Latency Ms | 381.36 |
| P95 Latency Ms | 547.83 |
| P99 Latency Ms | 547.83 |

### Notes

- **final_k**: 5
- **pool_size**: 20
- **cost_model**: Voyage AI dense query embedding (paid, per-token) + FastEmbed SPLADE sparse embedding (local CPU, free); fused in-process via RRF.

## hybrid_cross_encoder

| Metric | Value |
|---|---:|
| Queries Evaluated | 20 |
| Recall At 5 | 1.0 |
| Mrr | 1.0 |
| Ndcg At 5 | 1.0 |
| Avg Latency Ms | 625.37 |
| P95 Latency Ms | 1100.08 |
| P99 Latency Ms | 1100.08 |

### Notes

- **final_k**: 5
- **pool_size**: 20
- **cost_model**: Voyage AI dense query embedding (paid, per-token) + FastEmbed SPLADE sparse embedding (local CPU, free); fused in-process via RRF. Reranked via BAAI/bge-reranker-base: local CPU inference, no marginal cost.

## hybrid_voyage

| Metric | Value |
|---|---:|
| Queries Evaluated | 20 |
| Recall At 5 | 1.0 |
| Mrr | 0.95 |
| Ndcg At 5 | 0.9631 |
| Avg Latency Ms | 753.86 |
| P95 Latency Ms | 922.9 |
| P99 Latency Ms | 922.9 |

### Notes

- **final_k**: 5
- **pool_size**: 20
- **cost_model**: Voyage AI dense query embedding (paid, per-token) + FastEmbed SPLADE sparse embedding (local CPU, free); fused in-process via RRF. Reranked via Voyage AI rerank-2: paid, per-token API call.
