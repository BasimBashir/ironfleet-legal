---
name: nz-kreuzberg-ingestor
description: Use this skill whenever @INGESTOR needs to extract text, tables, or metadata from any document entering the Iron Fleet corpus. Invoke when processing PDFs, DOCX, XLSX, images, HTML, email, or any of the 88+ supported formats. Especially invoke for scanned NZ High Court affidavits requiring OCR, discovery sets requiring batch extraction, and financial statements requiring table extraction for @CITATION. Also invoke when classifying documents by Trust Tier using extracted metadata. Adapted from kreuzberg-dev/kreuzberg — Iron Fleet contextualised for Category A deterministic extraction, SHA-256 integrity, and NZ legal corpus ingestion.
license: MIT
compatibility: Claude Code, Claude Desktop, Claude Cowork. Corpus tools need local Python 3.10+ and Ollama.
metadata:
  mode: GLASS
  version: 1.0.0
  source_kernel: nz_kreuzberg_ingestor.py
  function: run
  permissions: []
  trust_tier_required: 0
  adapted_from: kreuzberg-dev/kreuzberg
---


# nz-kreuzberg-ingestor

## Purpose
Document extraction layer for Iron Fleet @INGESTOR pipeline. Adapted from
kreuzberg-dev/kreuzberg — Rust-core document intelligence library.

Category A (Iron Logic) skill — pure deterministic extraction, no LLM call,
fully reproducible output. SHA-256 hash-verifiable against manifest.lock.
No privilege concern — extraction runs locally, no data leaves environment.

## What kreuzberg provides for Iron Fleet

| Capability | Iron Fleet Application |
|---|---|
| 88+ format extraction | PDF, DOCX, XLSX, images, HTML, email — any document entering @INGESTOR |
| `batch_extract_files()` | Batch-ingest entire discovery sets or HCR bundles in one call |
| Built-in OCR (Tesseract) | Scanned NZ High Court affidavits and judgments — no external dependency |
| Table extraction | Financial statements, schedules, discovery indexes → @CITATION |
| Metadata extraction | Author, created date, modified date → Trust Tier classification |

## Integration Pattern
```python
# In @INGESTOR ingestion handler
from kreuzberg import batch_extract_files, ExtractionConfig

config = ExtractionConfig(
    ocr=OcrConfig(language="eng"),  # English — NZ legal documents
)

results = await batch_extract_files(document_paths, config=config)
for r in results:
    chunk_and_store(
        content=r.content,
        metadata=r.metadata,
        tables=r.tables,
        trust_tier=classify(r),
    )
```

## Input

| Field | Type | Required | Description |
|---|---|---|---|
| `document_paths` | `list[str]` | Yes | Paths to documents to extract |
| `ocr_language` | `str` | No | OCR language code. Default: `"eng"` |
| `extract_tables` | `bool` | No | Extract tables. Default: `true` |
| `extract_metadata` | `bool` | No | Extract metadata. Default: `true` |
| `trust_tier` | `str` | Yes | T0–T3 |
| `operator_override` | `bool` | No | Required for T0. Default: false |

## Processing

### Step 1 — Validate paths
Confirm all document_paths exist and are readable.
If any path missing, output ERROR with type MALFORMED_INPUT.

### Step 2 — Format detection
kreuzberg auto-detects MIME type from file content — no manual override needed.
Flag unsupported formats with [UNSUPPORTED-FORMAT — MANUAL REVIEW].

### Step 3 — Extraction
Call `batch_extract_files()` with ExtractionConfig.
OCR runs automatically for scanned PDFs and images.
Tables extracted as structured objects for @CITATION.

### Step 4 — Metadata → Trust Tier signal
Extracted metadata fields for Trust Tier classification:
- `author` — known counsel or court officer → T1 signal
- `created` — date within matter window → T1 signal
- `modified` — modified after creation → flag for review
- `encrypted` — encrypted PDF → T0 until decrypted with password

### Step 5 — SHA-256 integrity
Compute SHA-256 of extracted content for manifest.lock registration.
Per Iron Fleet skill integrity model — all ingested documents must be
hash-registered before chunking.

## Confidence Signals

| Signal | Weight | How scored |
|---|---|---|
| `extraction_complete` | 0.50 | 1.0 if all paths extracted; proportional if partial |
| `ocr_quality` | 0.30 | 1.0 if text > 100 chars per page; 0.5 if sparse |
| `metadata_present` | 0.20 | 1.0 if author + created present; 0.5 if partial |

## Ambiguity Handling

If kreuzberg is not installed, output `status: ERROR` with type
`DEPENDENCY_UNAVAILABLE` — install with `pip install kreuzberg`.

If extraction returns empty content for a non-empty file, output
`status: FLAGGED` with `[EMPTY-EXTRACTION — MANUAL REVIEW]` — may be
encrypted or corrupt.

If document appears encrypted, output `[ENCRYPTED-DOCUMENT — MANUAL REVIEW]`.

Never proceed to chunking if extraction confidence < 0.50.

## Output Schema
```json
{
  "status": "SUCCESS | FLAGGED | ERROR",
  "result": {
    "extracted": [
      {
        "path": "docs/affidavit_smith.pdf",
        "content_length": 11249,
        "table_count": 2,
        "metadata": {
          "author": "J. Smith",
          "created": "2024-03-01",
          "modified": null
        },
        "sha256": "abc123...",
        "trust_tier_signal": "T1",
        "ocr_applied": false
      }
    ],
    "failed": [],
    "total_documents": 3,
    "total_chars": 45000
  },
  "confidence": 0.92,
  "flags": [],
  "trust_tier": "T1"
}
```