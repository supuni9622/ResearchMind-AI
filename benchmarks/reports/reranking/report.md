# Reranking

## Dataset

- **Name:** research-papers
- **Documents:** 50
- **Generated:** `2026-08-11T18:29:57.347929+00:00`

## Provenance

- **Git commit:** `aa6d110fee2fb8324fd2ec807586e6e4c7189a38`
- **Branch:** `researchmind-v2`
- **Dataset version:** `unknown`
- **Benchmark version:** `1.0.0`

---

## Comparison

| Metric | hybrid_only | hybrid_cross_encoder | hybrid_voyage |
|---|---:|---:|---:|
| Avg Latency Ms | 451.48 | 603.52 | 860.02 |
| Mrr | 0.9552 | 0.9719 | 0.976 |
| Ndcg At 5 | 0.943 | 0.9582 | 0.9582 |
| P95 Latency Ms | 624.12 | 815.42 | 1205.59 |
| P99 Latency Ms | 962.54 | 1275.35 | 1470.53 |
| Queries Evaluated | 160 | 160 | 160 |
| Recall At 5 | 0.9583 | 0.9703 | 0.9688 |

---

## hybrid_only

| Metric | Value |
|---|---:|
| Queries Evaluated | 160 |
| Recall At 5 | 0.9583 |
| Mrr | 0.9552 |
| Ndcg At 5 | 0.943 |
| Avg Latency Ms | 451.48 |
| P95 Latency Ms | 624.12 |
| P99 Latency Ms | 962.54 |

### Notes

- **final_k**: 5
- **pool_size**: 20
- **cost_model**: Voyage AI dense query embedding (paid, per-token) + FastEmbed SPLADE sparse embedding (local CPU, free); fused in-process via RRF.

## hybrid_cross_encoder

| Metric | Value |
|---|---:|
| Queries Evaluated | 160 |
| Recall At 5 | 0.9703 |
| Mrr | 0.9719 |
| Ndcg At 5 | 0.9582 |
| Avg Latency Ms | 603.52 |
| P95 Latency Ms | 815.42 |
| P99 Latency Ms | 1275.35 |

### Notes

- **final_k**: 5
- **pool_size**: 20
- **cost_model**: Voyage AI dense query embedding (paid, per-token) + FastEmbed SPLADE sparse embedding (local CPU, free); fused in-process via RRF. Reranked via BAAI/bge-reranker-base: local CPU inference, no marginal cost.

## hybrid_voyage

| Metric | Value |
|---|---:|
| Queries Evaluated | 160 |
| Recall At 5 | 0.9688 |
| Mrr | 0.976 |
| Ndcg At 5 | 0.9582 |
| Avg Latency Ms | 860.02 |
| P95 Latency Ms | 1205.59 |
| P99 Latency Ms | 1470.53 |

### Notes

- **final_k**: 5
- **pool_size**: 20
- **cost_model**: Voyage AI dense query embedding (paid, per-token) + FastEmbed SPLADE sparse embedding (local CPU, free); fused in-process via RRF. Reranked via Voyage AI rerank-2: paid, per-token API call.
