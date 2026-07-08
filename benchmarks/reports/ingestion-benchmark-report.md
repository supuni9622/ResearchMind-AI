# ResearchMind Ingestion Benchmark

**Date:** 2026-07-08T10:01:35.290019+00:00
**Commit:** `cd6da38`

## Environment

| Key | Value |
|---|---|
| Python Version | 3.12.13 |
| Platform | macOS-26.5.2-arm64-arm-64bit |
| Chunking Strategy | markdown |
| Embedding Provider | voyage_ai |
| Vector Store Provider | qdrant |
| Owner Id | benchmark-ingestion-pipeline |
| Embedding Model | voyage-3-lite |
| Qdrant Collection | researchmind_knowledge |
| Sparse Embedding Model | prithivida/Splade_PP_en_v1 |

## Dataset

- **Name:** research-papers
- **Directory:** `benchmarks/datasets/research-papers`
- **Documents:** 5
- **Note:** documents were loaded from pre-processed `processed_document.json` artifacts. Upload and Processing (PDF parsing) were not re-executed; 'File Size' reflects the size of that source JSON, not the original PDF.

### Dataset Summary

| Metric | Total | Average per Document |
|---|---:|---:|
| Pages | 118 | 23.6 |
| Characters | 498,683 | 99,737 |
| Words | 66,624 | 13,325 |

## Individual Document Results

| Document | Pages | Chars | Words | Chunks | Avg Chunk | Largest | Smallest | Chunking (ms) | Embeddings | Dims | Embedding (ms) | Dense Vectors | Sparse Vectors | Indexing (ms) | Collection | Total (ms) | Peak Mem (MB) | Artifact Size |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|---:|---:|---:|
| 151__CRC.pdfrevised.pdf | 11 | 22,201 | 3,024 | 62 | 373 | 499 | 40 | 1.7 | 62 | 512 | 22.4 | 62 | 62 | 3590.6 | researchmind_knowledge | 7425.5 | 3919.6 | 1.17 MB |
| LLM_RESEARCH.pdf | 47 | 345,335 | 45,514 | 999 | 351 | 499 | 1 | 165.9 | 999 | 512 | 156.0 | 999 | 999 | 30203.3 | researchmind_knowledge | 63104.6 | 4139.3 | 18.65 MB |
| Noise_is_Signal_Density-Based_Outliers_as_Leading_.pdf | 10 | 41,483 | 6,129 | 130 | 342 | 499 | 12 | 5.6 | 130 | 512 | 35.0 | 130 | 130 | 5303.8 | researchmind_knowledge | 9516.6 | 3046.5 | 2.43 MB |
| Loop_Engineering_Revised.pdf | 36 | 78,455 | 10,376 | 252 | 334 | 499 | 3 | 12.5 | 252 | 512 | 53.4 | 252 | 252 | 9184.4 | researchmind_knowledge | 11611.5 | 3639.3 | 4.70 MB |
| data engineering .pdf | 14 | 11,209 | 1,581 | 57 | 230 | 499 | 11 | 2.2 | 57 | 512 | 10.5 | 57 | 57 | 2525.9 | researchmind_knowledge | 6412.3 | 3905.4 | 1.04 MB |

## Aggregate Statistics

| Metric | Average | Minimum | Maximum | Median | P95 |
|---|---:|---:|---:|---:|---:|
| Chunk Count | 300.0 | 57.0 | 999.0 | 130.0 | 849.6 |
| Embedding Count | 300.0 | 57.0 | 999.0 | 130.0 | 849.6 |
| Sparse Vector Count | 300.0 | 57.0 | 999.0 | 130.0 | 849.6 |
| Artifact Size (bytes) | 5869570.8 | 1091719.0 | 19560027.0 | 2549647.0 | 16632648.6 |

## Pipeline Timing

| Stage | Average (ms) | Minimum | Maximum | Median | P95 |
|---|---:|---:|---:|---:|---:|
| Total Pipeline | 19614.1 | 6412.3 | 63104.6 | 9516.6 | 52806.0 |
| Processing (skipped) | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 |
| Chunking | 37.6 | 1.7 | 165.9 | 5.6 | 135.2 |
| Embedding | 55.4 | 10.5 | 156.0 | 35.0 | 135.4 |
| Indexing | 10161.6 | 2525.9 | 30203.3 | 5303.8 | 25999.5 |

## Storage Report

| Metric | Value |
|---|---:|
| Average storage per document | 5.60 MB |
| Average storage per chunk | 1.66 KB |
| Average storage per embedding | 16.79 KB |
| Total storage generated | 27.99 MB |
| Avg processed_document.json | 198.18 KB |
| Avg chunks.json | 496.69 KB |
| Avg embeddings.json | 4.92 MB |
| Avg indexing.json | 593.20 B |

## Throughput

| Metric | Value |
|---|---:|
| Documents / minute | 3.06 |
| Chunks / second | 15.29 |
| Embeddings / second | 15.29 |
| Vectors / second | 15.29 |

## Memory Usage

| Metric | Value (MB) |
|---|---:|
| Average peak memory | 3730.0 |
| Minimum peak memory | 3046.5 |
| Maximum peak memory | 4139.3 |

## Success Report

| Metric | Value |
|---|---:|
| Documents processed | 5 |
| Successful | 5 |
| Failed | 0 |
| Success Rate | 100% |

## Observations

- **Slowest document:** LLM_RESEARCH.pdf (63.10s)
- **Fastest document:** data engineering .pdf (6.41s)
- **Largest artifact:** LLM_RESEARCH.pdf / embeddings.json (16.37 MB)
- **Smallest artifact:** data engineering .pdf / indexing.json (587.00 B)
- **Average pipeline time:** 19.61s
- **Average dense vectors generated:** 300
- **Average sparse vectors generated:** 300
- **Average chunks generated:** 300

## Production Readiness

✔ Complete ingestion pipeline functional
✔ 5/5 documents successfully processed
✔ 100% embedding success
✔ 100% indexing success
✔ All artifacts generated
✔ Average pipeline time: 19.61 s
✔ Average dense vectors indexed: 300
✔ Average sparse vectors indexed: 300
✔ Hybrid indexing functional (dense + sparse vectors in the same collection)
✔ No failures observed

### Recommendations

- Optimize indexing latency (largest contributor)
- Artifact storage per document is large; consider compression.
- Ready to proceed to Retrieval Platform

