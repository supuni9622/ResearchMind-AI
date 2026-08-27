# MetadataFiltering

## Dataset

- **Name:** research-papers
- **Documents:** 50
- **Generated:** `2026-08-11T18:43:33.866561+00:00`

## Provenance

- **Git commit:** `aa6d110fee2fb8324fd2ec807586e6e4c7189a38`
- **Branch:** `researchmind-v2`
- **Dataset version:** `unknown`
- **Benchmark version:** `1.0.0`

---

## Comparison

| Metric | dense | sparse | hybrid |
|---|---:|---:|---:|
| Avg Latency Ms | 360.73 | 11.85 | 370.59 |
| Leakage Rate | 0.0 | 0.0 | 0.0 |
| Mrr | 1.0 | 1.0 | 1.0 |
| P95 Latency Ms | 513.47 | 14.53 | 500.96 |
| P99 Latency Ms | 614.08 | 16.2 | 917.97 |
| Precision At 10 | 0.1 | 0.1 | 0.1 |
| Precision At 5 | 0.2 | 0.2 | 0.2 |
| Queries Evaluated | 137 | 137 | 137 |
| Recall At 10 | 1.0 | 1.0 | 1.0 |
| Recall At 20 | 1.0 | 1.0 | 1.0 |
| Recall At 5 | 1.0 | 1.0 | 1.0 |

---

## dense

| Metric | Value |
|---|---:|
| Queries Evaluated | 137 |
| Recall At 5 | 1.0 |
| Recall At 10 | 1.0 |
| Recall At 20 | 1.0 |
| Precision At 5 | 0.2 |
| Precision At 10 | 0.1 |
| Mrr | 1.0 |
| Avg Latency Ms | 360.73 |
| P95 Latency Ms | 513.47 |
| P99 Latency Ms | 614.08 |
| Leakage Rate | 0.0 |

### Notes

- **top_k_evaluated**: 20

## sparse

| Metric | Value |
|---|---:|
| Queries Evaluated | 137 |
| Recall At 5 | 1.0 |
| Recall At 10 | 1.0 |
| Recall At 20 | 1.0 |
| Precision At 5 | 0.2 |
| Precision At 10 | 0.1 |
| Mrr | 1.0 |
| Avg Latency Ms | 11.85 |
| P95 Latency Ms | 14.53 |
| P99 Latency Ms | 16.2 |
| Leakage Rate | 0.0 |

### Notes

- **top_k_evaluated**: 20

## hybrid

| Metric | Value |
|---|---:|
| Queries Evaluated | 137 |
| Recall At 5 | 1.0 |
| Recall At 10 | 1.0 |
| Recall At 20 | 1.0 |
| Precision At 5 | 0.2 |
| Precision At 10 | 0.1 |
| Mrr | 1.0 |
| Avg Latency Ms | 370.59 |
| P95 Latency Ms | 500.96 |
| P99 Latency Ms | 917.97 |
| Leakage Rate | 0.0 |

### Notes

- **top_k_evaluated**: 20
