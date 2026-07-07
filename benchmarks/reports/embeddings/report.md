# Embeddings

## Dataset

- **Name:** research-papers
- **Documents:** 5
- **Generated:** `2026-07-07T06:57:45.057705+00:00`

---

## Comparison

| Metric | sentence_transformers | voyage_ai | openai |
|---|---:|---:|---:|
| Average Latency Ms | 10.26 | 28.03 | 16.77 |
| Dimensions | 384 | 512 | 1536 |
| Documents | 5 | 5 | 5 |
| Duration Seconds | 15.1887 | 41.5105 | 24.8303 |
| Throughput Embeddings Per Second | 97.51 | 35.68 | 59.64 |
| Total Chunks | 1481 | 1481 | 1481 |
| Total Embeddings | 1481 | 1481 | 1481 |

---

## sentence_transformers

Version: `1.0`

| Metric | Value |
|---|---:|
| Documents | 5 |
| Total Chunks | 1481 |
| Total Embeddings | 1481 |
| Dimensions | 384 |
| Duration Seconds | 15.1887 |
| Average Latency Ms | 10.26 |
| Throughput Embeddings Per Second | 97.51 |

### Notes

- **model**: all-MiniLM-L6-v2

## voyage_ai

Version: `1.0`

| Metric | Value |
|---|---:|
| Documents | 5 |
| Total Chunks | 1481 |
| Total Embeddings | 1481 |
| Dimensions | 512 |
| Duration Seconds | 41.5105 |
| Average Latency Ms | 28.03 |
| Throughput Embeddings Per Second | 35.68 |

### Notes

- **model**: voyage-3-lite

## openai

Version: `1.0`

| Metric | Value |
|---|---:|
| Documents | 5 |
| Total Chunks | 1481 |
| Total Embeddings | 1481 |
| Dimensions | 1536 |
| Duration Seconds | 24.8303 |
| Average Latency Ms | 16.77 |
| Throughput Embeddings Per Second | 59.64 |

### Notes

- **model**: text-embedding-3-small
