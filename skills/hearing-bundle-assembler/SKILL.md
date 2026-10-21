---
name: hearing-bundle-assembler
description: Use this skill whenever an electronic hearing bundle or common bundle needs to be assembled from individual exhibit PDFs into a single consecutively paginated document per HCR r9.4 and Electronic Bundle Practice Note 2019 (HCPN 2019/1). Invoke when @CLERK or @PLANNER triggers bundle assembly, even if the user has not explicitly requested PDF merging. Requires pagination-index-mapper (BN-05) output as input — do not invoke without a confirmed page_map.
license: MIT
compatibility: Claude Code, Claude Desktop, Claude Cowork. Corpus tools need local Python 3.10+ and Ollama.
metadata:
  mode: GLASS
  version: 1.0.0
  source_kernel: hearing_bundle_assembler.py
  function: run
  dependencies:
  - pagination-index-mapper
  - exhibit-numberer
  permissions:
  - file_write
  trust_tier_required: 1
---


# hearing-bundle-assembler

## Purpose
Assembles individual exhibit PDFs into a single consecutively paginated
electronic hearing bundle per HCR r9.4 and Practice Note HCPN 2019/1.

Produces:
1. A single merged PDF with consecutive page numbers across all documents
2. A cover index page listing all exhibits with their bundle page positions

Feeds @CITATION (for bounding-box positioning in the assembled bundle) and
the filing gate. Output must be reviewed by @CLERK before filing.

## Input

| Field | Type | Required | Description |
|---|---|---|---|
| `page_map` | `list` | Yes | Output from BN-05: `[{label, id, filename, pdf_page, printed_page, method}]` |
| `exhibit_schedule` | `list` | Yes | Output from BN-01: `[{label, id, filename, date}]` |
| `pdf_dir` | `str` | Yes | Directory containing individual exhibit PDFs |
| `output_path` | `str` | Yes | Absolute path for assembled bundle output PDF |
| `matter_ref` | `str` | No | Matter reference for cover index header |
| `trust_tier` | `str` | Yes | T0–T3 |
| `operator_override` | `bool` | No | Required for T0. Default: false |

## Processing

1. T0 gate — if trust_tier is T0 and operator_override not true, halt with
   ERROR MALFORMED_INPUT.

2. Validate required fields — halt with ERROR MALFORMED_INPUT if missing.

3. Validate page_map and exhibit_schedule are not empty.

4. Validate all exhibit PDF files exist in pdf_dir. If any missing, halt
   with ERROR DEPENDENCY_UNAVAILABLE listing missing files.

5. Sort exhibits chronologically by date from exhibit_schedule per HCR r9.4
   — bundle must be in date order. If dates are identical, preserve
   label order (A before B).

6. Build cover index page listing:
   - Matter reference (if provided)
   - Column headers: Label | Document | Date | Bundle Page
   - One row per exhibit with bundle page number

7. Assemble PDF using pypdfium2:
   - Page 1: cover index
   - Subsequent pages: exhibit PDFs in chronological order
   - Consecutive pagination across entire bundle

8. Write assembled PDF to output_path.

9. Calculate confidence using weighted signals.

10. Return assembly report with page count and bundle map.

## Confidence Signals

| Signal | Weight | How scored |
|---|---|---|
| `all_files_found` | 0.60 | 1.0 if all exhibit PDFs found; 0.0 if any missing |
| `page_map_complete` | 0.30 | 1.0 if page_map covers all exhibits; proportional if partial |
| `chronological_valid` | 0.10 | 1.0 if all dates parseable; 0.5 if some missing |

## Ambiguity Handling

If any exhibit PDF file is missing from pdf_dir, output `status: ERROR`
with type `DEPENDENCY_UNAVAILABLE` listing missing files and halt.

If page_map does not cover all exhibits in exhibit_schedule, output
`status: FLAGGED` with flag `[BUNDLE-PAGE-MAP-INCOMPLETE — MANUAL REVIEW]`
and halt.

If any exhibit date cannot be parsed for chronological sorting, output
`status: FLAGGED` with flag `[BUNDLE-SORT-AMBIGUOUS — MANUAL REVIEW]`
and halt.

If confidence < 0.50, output `status: FLAGGED` with
`[ESCALATE-TO-IRON — BUNDLE-ASSEMBLY-UNCERTAIN]` and halt.

Never assemble a partial bundle. Never proceed without a complete page_map.

## Output Schema

**Success payload:**
```json
{
  "status": "SUCCESS",
  "result": {
    "output_path": "/case/bundle_final.pdf",
    "total_pages": 47,
    "exhibit_count": 5,
    "bundle_map": [
      {
        "label": "A",
        "filename": "contract.pdf",
        "date": "2024-01-10",
        "bundle_page_start": 2,
        "bundle_page_end": 8
      }
    ],
    "cover_index_page": 1
  },
  "confidence": 0.90,
  "flags": [],
  "trust_tier": "T1"
}
```

**Flagged payload:**
```json
{
  "status": "FLAGGED",
  "result": null,
  "confidence": 0.45,
  "flags": ["[BUNDLE-PAGE-MAP-INCOMPLETE — MANUAL REVIEW]"],
  "trust_tier": "T1"
}
```

**Error payload:**
```json
{
  "status": "ERROR",
  "result": null,
  "confidence": null,
  "flags": ["[DEPENDENCY-UNAVAILABLE]"],
  "error": {
    "type": "DEPENDENCY_UNAVAILABLE",
    "message": "Missing exhibit PDFs: contract.pdf, invoice.pdf",
    "retry_recommended": false,
    "input_hash": "sha256-of-input"
  }
}
```

## Quality Checks

Before returning output, verify:
1. total_pages matches actual page count of assembled PDF
2. bundle_map covers all exhibits — no exhibit missing from map
3. Cover index is page 1 — exhibit content starts at page 2

## Examples

**Example 1 — 3-document bundle:**
Input:
```json
{
  "page_map": [
    {"label": "A", "id": "doc-001", "filename": "contract.pdf", "pdf_page": 0, "printed_page": 1, "method": "direct"},
    {"label": "B", "id": "doc-002", "filename": "invoice.pdf", "pdf_page": 0, "printed_page": 1, "method": "direct"},
    {"label": "C", "id": "doc-003", "filename": "email.pdf", "pdf_page": 0, "printed_page": 1, "method": "direct"}
  ],
  "exhibit_schedule": [
    {"label": "A", "id": "doc-001", "filename": "contract.pdf", "date": "2024-01-10"},
    {"label": "B", "id": "doc-002", "filename": "invoice.pdf", "date": "2024-02-14"},
    {"label": "C", "id": "doc-003", "filename": "email.pdf", "date": "2024-03-01"}
  ],
  "pdf_dir": "/case/exhibits/",
  "output_path": "/case/bundle.pdf",
  "trust_tier": "T1"
}
```
Expected output:
```json
{
  "status": "SUCCESS",
  "result": {
    "output_path": "/case/bundle.pdf",
    "total_pages": 4,
    "exhibit_count": 3,
    "bundle_map": [
      {"label": "A", "filename": "contract.pdf", "date": "2024-01-10", "bundle_page_start": 2, "bundle_page_end": 2},
      {"label": "B", "filename": "invoice.pdf", "date": "2024-02-14", "bundle_page_start": 3, "bundle_page_end": 3},
      {"label": "C", "filename": "email.pdf", "date": "2024-03-01", "bundle_page_start": 4, "bundle_page_end": 4}
    ],
    "cover_index_page": 1
  },
  "confidence": 0.90,
  "flags": [],
  "trust_tier": "T1"
}
```

**Example 2 — missing BN-05 dependency:**
Input:
```json
{
  "page_map": [],
  "exhibit_schedule": [{"label": "A", "id": "doc-001", "filename": "contract.pdf", "date": "2024-01-10"}],
  "pdf_dir": "/case/exhibits/",
  "output_path": "/case/bundle.pdf",
  "trust_tier": "T1"
}
```
Expected output:
```json
{
  "status": "ERROR",
  "result": null,
  "confidence": null,
  "flags": ["[EMPTY-PAGE-MAP]"],
  "error": {
    "type": "DEPENDENCY_UNAVAILABLE",
    "message": "page_map is empty — run pagination-index-mapper (BN-05) first",
    "retry_recommended": false,
    "input_hash": "sha256-of-input"
  }
}
```