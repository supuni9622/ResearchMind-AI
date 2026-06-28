Status

Accepted

Context

ResearchMind AI requires a production-grade document processing pipeline capable of ingesting diverse document formats and transforming them into structured representations suitable for downstream AI tasks.

The document processing layer is the foundation of the Knowledge Platform and directly impacts:

Chunking quality
Metadata extraction
Retrieval accuracy
Citation quality
Agent reasoning
Evaluation

Several document parsing approaches were evaluated before implementing Milestone 2.2.

Requirements

The parser should support:

PDF
DOCX
Markdown
TXT

Future support:

HTML
EPUB
PPTX
Images (OCR)
Scanned PDFs
Web pages

The solution should:

Preserve document structure
Preserve reading order
Extract metadata
Support tables
Support figures
Support headings
Be suitable for RAG
Be extensible
Remain replaceable behind an abstraction
Options Evaluated
Option 1 — Individual Libraries

Examples

PyMuPDF
python-docx
markdown-it-py
Advantages
Lightweight
Mature
Fast
Full low-level control
Minimal dependencies
Disadvantages
Different API for every format
Manual normalization
Manual metadata extraction
Limited semantic structure
Tables require custom handling
Difficult to maintain as supported formats increase
Suitable For
Traditional backend applications
Simple text extraction
Lightweight ingestion pipelines
Option 2 — Unstructured
Advantages
Mature ecosystem
Excellent LangChain integration
Supports many document types
Good OCR ecosystem
Widely adopted
Disadvantages
Heavy dependency tree
Larger installation footprint
Slower processing
Less structured document model than Docling
More difficult to customize internally
Suitable For
Enterprise ingestion pipelines
Existing LangChain projects
Large heterogeneous datasets
Option 3 — Docling
Advantages
Designed specifically for AI and RAG workflows
Rich document object model
Preserves headings, sections, tables, lists and figures
Maintains reading order
Supports Markdown export
Extensible parser architecture
Active open-source development
Well suited for future chunking strategies
Disadvantages
Larger dependency footprint
Newer ecosystem
Less low-level control than specialized libraries
API may evolve as the project matures
Suitable For
AI applications
Research assistants
Knowledge platforms
Production RAG systems
Agentic workflows
Comparison
Capability	Individual Libraries	Unstructured	Docling
Plain text extraction	Excellent	Excellent	Excellent
Document structure	Limited	Good	Excellent
Tables	Manual	Good	Excellent
Reading order	Limited	Good	Excellent
Metadata extraction	Manual	Good	Excellent
AI / RAG readiness	Low	High	Excellent
OCR integration	External	Excellent	Good
Multiple document formats	Multiple libraries	Single framework	Single framework
Extensibility	Moderate	High	High
Decision

ResearchMind will adopt the following strategy.

Primary Architecture

The application will depend on an abstract parser interface.

ProcessingService

↓

DocumentParser (interface)

↓

Parser Implementation

Business logic must never depend directly on Docling or any other parsing library.

Default Parser

Docling will be used as the default parser implementation.

Reasons:

Better preservation of document semantics.
Richer metadata extraction.
Higher quality input for chunking.
Better retrieval context.
Cleaner support for future AI capabilities.
Alternative Parsers

The architecture intentionally allows additional implementations.

Possible future implementations include:

PyMuPDFParser
UnstructuredParser
Amazon Textract Parser
Azure Document Intelligence Parser
Google Document AI Parser

These can be introduced without changing the processing service.

Consequences
Positive
Better document understanding
Improved chunk quality
Better retrieval performance
Easier metadata extraction
Future-ready for agents and research workflows
Cleaner processing pipeline
Negative
Larger dependency footprint
Increased installation time
Dependency on a newer framework
Slightly higher implementation complexity
Future Evaluation

The parser implementation is not permanently fixed.

Future benchmarking may compare:

Parsing latency
Metadata quality
Table extraction accuracy
Reading order preservation
Retrieval quality after chunking
End-to-end RAG accuracy

If another implementation demonstrates measurable production benefits, it may replace Docling without affecting the application architecture.

Architectural Principles Reinforced

This decision reinforces several project principles:

AI-first engineering
Provider independence
Separation of concerns
Replaceable infrastructure
Evaluation-driven engineering
Production-quality architecture
Decision Summary

ResearchMind adopts a parser abstraction architecture with Docling as the default implementation.

The architectural commitment is not to Docling itself, but to a modular processing layer where parser implementations are replaceable and selected based on measurable quality.

Architecture
                   Upload (Completed)
                           │
                           ▼
                  ProcessingService
                           │
                           ▼
                  DocumentParser (Interface)
                           │
         ┌─────────────────┼──────────────────┐
         │                 │                  │
         ▼                 ▼                  ▼
   DoclingParser     FutureParser      FutureParser
    (Default)      (Unstructured)    (Textract/Azure)
         │
         ▼
   ProcessedDocument
         │
         ▼
  Chunking Platform (2.3)
