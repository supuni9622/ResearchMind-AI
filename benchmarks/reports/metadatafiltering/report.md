# MetadataFiltering

## Dataset

- **Name:** research-papers
- **Documents:** 5
- **Generated:** `2026-07-14T08:00:10.305606+00:00`

---

## Comparison

| Metric | dense_unfiltered | dense_filtered | sparse_unfiltered | sparse_filtered | hybrid_unfiltered | hybrid_filtered |
|---|---:|---:|---:|---:|---:|---:|
| Avg Latency Ms | 316.87 | 300.55 | 11.34 | 10.55 | 351.21 | 361.93 |
| Leakage Rate | 0.21 | 0.0 | 0.1775 | 0.0 | 0.1575 | 0.0 |
| Mrr | 0.95 | 1.0 | 0.975 | 1.0 | 0.925 | 1.0 |
| P95 Latency Ms | 453.4 | 356.32 | 24.48 | 14.83 | 514.57 | 603.28 |
| P99 Latency Ms | 453.4 | 356.32 | 24.48 | 14.83 | 514.57 | 603.28 |
| Precision At 10 | 0.1 | 0.1 | 0.1 | 0.1 | 0.1 | 0.1 |
| Precision At 5 | 0.2 | 0.2 | 0.2 | 0.2 | 0.2 | 0.2 |
| Queries Evaluated | 20 | 20 | 20 | 20 | 20 | 20 |
| Recall At 10 | 1.0 | 1.0 | 1.0 | 1.0 | 1.0 | 1.0 |
| Recall At 20 | 1.0 | 1.0 | 1.0 | 1.0 | 1.0 | 1.0 |
| Recall At 5 | 1.0 | 1.0 | 1.0 | 1.0 | 1.0 | 1.0 |

---

## dense_unfiltered

| Metric | Value |
|---|---:|
| Queries Evaluated | 20 |
| Recall At 5 | 1.0 |
| Recall At 10 | 1.0 |
| Recall At 20 | 1.0 |
| Precision At 5 | 0.2 |
| Precision At 10 | 0.1 |
| Mrr | 0.95 |
| Avg Latency Ms | 316.87 |
| P95 Latency Ms | 453.4 |
| P99 Latency Ms | 453.4 |
| Leakage Rate | 0.21 |

### Notes

- **top_k_evaluated**: 20
- **filtered**: False

## dense_filtered

| Metric | Value |
|---|---:|
| Queries Evaluated | 20 |
| Recall At 5 | 1.0 |
| Recall At 10 | 1.0 |
| Recall At 20 | 1.0 |
| Precision At 5 | 0.2 |
| Precision At 10 | 0.1 |
| Mrr | 1.0 |
| Avg Latency Ms | 300.55 |
| P95 Latency Ms | 356.32 |
| P99 Latency Ms | 356.32 |
| Leakage Rate | 0.0 |

### Notes

- **top_k_evaluated**: 20
- **filtered**: True

## sparse_unfiltered

| Metric | Value |
|---|---:|
| Queries Evaluated | 20 |
| Recall At 5 | 1.0 |
| Recall At 10 | 1.0 |
| Recall At 20 | 1.0 |
| Precision At 5 | 0.2 |
| Precision At 10 | 0.1 |
| Mrr | 0.975 |
| Avg Latency Ms | 11.34 |
| P95 Latency Ms | 24.48 |
| P99 Latency Ms | 24.48 |
| Leakage Rate | 0.1775 |

### Notes

- **top_k_evaluated**: 20
- **filtered**: False

## sparse_filtered

| Metric | Value |
|---|---:|
| Queries Evaluated | 20 |
| Recall At 5 | 1.0 |
| Recall At 10 | 1.0 |
| Recall At 20 | 1.0 |
| Precision At 5 | 0.2 |
| Precision At 10 | 0.1 |
| Mrr | 1.0 |
| Avg Latency Ms | 10.55 |
| P95 Latency Ms | 14.83 |
| P99 Latency Ms | 14.83 |
| Leakage Rate | 0.0 |

### Notes

- **top_k_evaluated**: 20
- **filtered**: True

## hybrid_unfiltered

| Metric | Value |
|---|---:|
| Queries Evaluated | 20 |
| Recall At 5 | 1.0 |
| Recall At 10 | 1.0 |
| Recall At 20 | 1.0 |
| Precision At 5 | 0.2 |
| Precision At 10 | 0.1 |
| Mrr | 0.925 |
| Avg Latency Ms | 351.21 |
| P95 Latency Ms | 514.57 |
| P99 Latency Ms | 514.57 |
| Leakage Rate | 0.1575 |

### Notes

- **top_k_evaluated**: 20
- **filtered**: False

## hybrid_filtered

| Metric | Value |
|---|---:|
| Queries Evaluated | 20 |
| Recall At 5 | 1.0 |
| Recall At 10 | 1.0 |
| Recall At 20 | 1.0 |
| Precision At 5 | 0.2 |
| Precision At 10 | 0.1 |
| Mrr | 1.0 |
| Avg Latency Ms | 361.93 |
| P95 Latency Ms | 603.28 |
| P99 Latency Ms | 603.28 |
| Leakage Rate | 0.0 |

### Notes

- **top_k_evaluated**: 20
- **filtered**: True
