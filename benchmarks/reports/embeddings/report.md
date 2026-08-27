# Embeddings

## Dataset

- **Name:** research-papers
- **Documents:** 50
- **Generated:** `2026-08-11T18:15:47.113745+00:00`

## Provenance

- **Git commit:** `aa6d110fee2fb8324fd2ec807586e6e4c7189a38`
- **Branch:** `researchmind-v2`
- **Dataset version:** `unknown`
- **Benchmark version:** `1.0.0`

---

## Comparison

| Metric | sentence_transformers | voyage_ai | openai |
|---|---:|---:|---:|
| Average Latency Ms | 4.42 | 17.94 | 16.43 |
| Dimensions | 384 | 512 | 1536 |
| Documents | 50 | 50 | 50 |
| Duration Seconds | 58.536 | 237.4047 | 217.48 |
| Throughput Embeddings Per Second | 226.12 | 55.75 | 60.86 |
| Total Chunks | 13236 | 13236 | 13236 |
| Total Embeddings | 13236 | 13236 | 13236 |

---

## sentence_transformers

Version: `1.0`

| Metric | Value |
|---|---:|
| Documents | 50 |
| Total Chunks | 13236 |
| Total Embeddings | 13236 |
| Dimensions | 384 |
| Duration Seconds | 58.536 |
| Average Latency Ms | 4.42 |
| Throughput Embeddings Per Second | 226.12 |

### Notes

- **model**: all-MiniLM-L6-v2

## voyage_ai

Version: `1.0`

| Metric | Value |
|---|---:|
| Documents | 50 |
| Total Chunks | 13236 |
| Total Embeddings | 13236 |
| Dimensions | 512 |
| Duration Seconds | 237.4047 |
| Average Latency Ms | 17.94 |
| Throughput Embeddings Per Second | 55.75 |

### Notes

- **model**: voyage-3-lite

## openai

Version: `1.0`

| Metric | Value |
|---|---:|
| Documents | 50 |
| Total Chunks | 13236 |
| Total Embeddings | 13236 |
| Dimensions | 1536 |
| Duration Seconds | 217.48 |
| Average Latency Ms | 16.43 |
| Throughput Embeddings Per Second | 60.86 |

### Notes

- **model**: text-embedding-3-small
