# Embeddings

## Dataset

- **Name:** research-papers
- **Documents:** 5
- **Generated:** `2026-07-07T06:45:56.914422+00:00`

---

## Comparison

| Metric | sentence_transformers | voyage_ai |
|---|---:|---:|
| Average Latency Ms | 9.45 | 52.42 |
| Dimensions | 384 | 512 |
| Documents | 5 | 1 |
| Duration Seconds | 13.9924 | 3.4071 |
| Throughput Embeddings Per Second | 105.84 | 19.08 |
| Total Chunks | 1481 | 65 |
| Total Embeddings | 1481 | 65 |

---

## sentence_transformers

Version: `1.0`

| Metric | Value |
|---|---:|
| Documents | 5 |
| Total Chunks | 1481 |
| Total Embeddings | 1481 |
| Dimensions | 384 |
| Duration Seconds | 13.9924 |
| Average Latency Ms | 9.45 |
| Throughput Embeddings Per Second | 105.84 |

### Notes

- **model**: all-MiniLM-L6-v2

## voyage_ai

Version: `1.0`

| Metric | Value |
|---|---:|
| Documents | 1 |
| Total Chunks | 65 |
| Total Embeddings | 65 |
| Dimensions | 512 |
| Duration Seconds | 3.4071 |
| Average Latency Ms | 52.42 |
| Throughput Embeddings Per Second | 19.08 |

### Notes

- **model**: voyage-3-lite
- **error**: You have not yet added your payment method in the billing page and will have reduced rate limits of 3 RPM and 10K TPM. To unlock our standard rate limits, please add a payment method in the billing page for the appropriate organization in the user dashboard (https://dashboard.voyageai.com/). Even with payment methods entered, the free tokens (200M tokens for Voyage series 3) will still apply. After adding a payment method, you should see your rate limits increase after several minutes. See our pricing docs (https://docs.voyageai.com/docs/pricing) for the free tokens for your model.
