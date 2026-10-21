---
name: pagination-index-mapper
description: Use this skill whenever an electronic hearing bundle or common bundle requires exhibit tab positions to be mapped to absolute PDF page numbers before @CITATION can apply bounding-box highlights or before hearing-bundle-assembler (BN-04) assembles the final bundle. Invoke when any PDF bundle is ingested that contains an exhibit tab index, even if the user has not explicitly requested pagination mapping. Do not pass bundle documents to @CITATION without running this skill first.
license: MIT
compatibility: Claude Code, Claude Desktop, Claude Cowork. Corpus tools need local Python 3.10+ and Ollama.
metadata:
  mode: GLASS
  version: 1.0.0
  source_kernel: pagination_index_mapper.py
  function: run
  dependencies:
  - exhibit-numberer
  permissions: []
  trust_tier_required: 1
---


# pagination-index-mapper

## Purpose
Maps exhibit tab labels to printed page numbers and absolute PDF page
positions within an electronic hearing bundle per HCR r9.4(5)(b–c) and
the Electronic Bundle Practice Note 2019 (HCPN 2019/1).

Produces a page map consumed by hearing-bundle-assembler (BN-04) and
@CITATION for bounding-box highlight positioning. Without this skill,
@CITATION cannot locate exhibit pages within a multi-document bundle and
BN-04 cannot assemble a consecutively paginated bundle.

## Input

| Field | Type | Required | Description |
|---|---|---|---|
| `pdf_path` | `str` | Yes | Absolute path to the bundle PDF file |
| `exhibit_schedule` | `list` | Yes | Output from exhibit-numberer (BN-01): `[{label, id, filename, date}]` |
| `trust_tier` | `str` | Yes | T0–T3. Refuse T0 without operator_override |
| `operator_override` | `bool` | No | Required for T0. Default: false |
| `case_state` | `dict` | No | Read-only. Fields: case_number |

## Processing

1. T0 gate — if trust_tier is T0 and operator_override not true, halt with
   ERROR MALFORMED_INPUT.

2. Validate required fields — if pdf_path or exhibit_schedule missing,
   halt with ERROR MALFORMED_INPUT.

3. Validate PDF exists at pdf_path — if not found, halt with
   ERROR DEPENDENCY_UNAVAILABLE.

4. Open PDF with pdfplumber. Extract total page count.

5. For each exhibit in exhibit_schedule, attempt mapping via three strategies
   in order:

   **Strategy 1 — Direct printed index match (confidence 1.0):**
   Scan each PDF page for printed index text matching the exhibit label
   (e.g. "TAB A", "Exhibit A", "A"). If found, record:
   - `printed_page`: the page number as printed in the document
   - `pdf_page`: the absolute 0-based PDF page index
   - `method`: "direct"

   **Strategy 2 — Sequential inference (confidence 0.7):**
   If direct match fails but adjacent exhibits are mapped, infer position
   from sequence. Record method: "inferred".

   **Strategy 3 — Metadata corroboration (confidence 0.5):**
   Cross-reference filename from exhibit_schedule against PDF metadata
   or bookmarks. Record method: "metadata".

6. If no strategy succeeds for an exhibit, do NOT guess. Output FLAGGED
   with `[PAGINATION-UNMAPPED — MANUAL REVIEW]` for that exhibit.

7. If ANY exhibit is unmapped, the overall status is FLAGGED — do not
   return a partial map as SUCCESS. A partial map would corrupt BN-04
   bundle assembly and @CITATION positioning.

8. Calculate confidence using weighted signals per Annex §3.2.1.

9. Return page map for all exhibits.

## Confidence Signals

| Signal | Weight | How scored |
|---|---|---|
| `direct_match` | 0.70 | Proportion of exhibits mapped via Strategy 1 |
| `inferred_from_sequence` | 0.20 | Proportion mapped via Strategy 2 |
| `metadata_corroboration` | 0.10 | Proportion mapped via Strategy 3 |

## Ambiguity Handling

If any exhibit in exhibit_schedule cannot be mapped by any strategy,
output `status: FLAGGED` with flag `[PAGINATION-UNMAPPED — MANUAL REVIEW]`
and halt. Include which exhibit labels failed in the flag detail.

If PDF cannot be opened or is corrupted, output `status: ERROR` with
type `DEPENDENCY_UNAVAILABLE` and halt.

If exhibit_schedule is empty, output `status: ERROR` with type
`MALFORMED_INPUT` and halt.

If confidence < 0.50, output `status: FLAGGED` with
`[ESCALATE-TO-IRON — PAGINATION-MAPPING-UNCERTAIN]` and halt.

If confidence >= 0.50 and < 0.75, output `status: FLAGGED` with
`[PAGINATION-MAPPING-UNCERTAIN — MANUAL REVIEW]` and halt.

Never guess a page position. Never return a partial map as SUCCESS.

## Output Schema

**Success payload:**
```json
{
  "status": "SUCCESS",
  "result": {
    "page_map": [
      {
        "label": "A",
        "id": "doc-001",
        "filename": "contract.pdf",
        "printed_page": 3,
        "pdf_page": 2,
        "method": "direct | inferred | metadata"
      }
    ],
    "total_pdf_pages": 45,
    "mapped_count": 5,
    "unmapped_count": 0
  },
  "confidence": 0.94,
  "flags": [],
  "trust_tier": "T1"
}
```

**Flagged payload:**
```json
{
  "status": "FLAGGED",
  "result": null,
  "confidence": 0.60,
  "flags": ["[PAGINATION-UNMAPPED — MANUAL REVIEW]"],
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
    "message": "PDF not found at path: /case/bundle.pdf",
    "retry_recommended": false,
    "input_hash": "sha256-of-input"
  }
}
```

## Quality Checks

Before returning output, verify:
1. mapped_count + unmapped_count == len(exhibit_schedule)
2. No two exhibits share the same pdf_page value — duplicate positions
   indicate a mapping error
3. All pdf_page values are within range 0 to total_pdf_pages - 1

## Examples

**Example 1 — clean sequential bundle:**
Input:
```json
{
  "pdf_path": "/case/bundle.pdf",
  "exhibit_schedule": [
    {"label": "A", "id": "doc-001", "filename": "contract.pdf", "date": "2024-01-10"},
    {"label": "B", "id": "doc-002", "filename": "invoice.pdf", "date": "2024-02-14"}
  ],
  "trust_tier": "T1"
}
```
Expected output:
```json
{
  "status": "SUCCESS",
  "result": {
    "page_map": [
      {"label": "A", "id": "doc-001", "filename": "contract.pdf", "printed_page": 1, "pdf_page": 0, "method": "direct"},
      {"label": "B", "id": "doc-002", "filename": "invoice.pdf", "printed_page": 8, "pdf_page": 7, "method": "direct"}
    ],
    "total_pdf_pages": 20,
    "mapped_count": 2,
    "unmapped_count": 0
  },
  "confidence": 0.94,
  "flags": [],
  "trust_tier": "T1"
}
```

**Example 2 — missing printed index → FLAGGED:**
Input:
```json
{
  "pdf_path": "/case/bundle_no_index.pdf",
  "exhibit_schedule": [
    {"label": "A", "id": "doc-001", "filename": "contract.pdf", "date": "2024-01-10"}
  ],
  "trust_tier": "T1"
}
```
Expected output:
```json
{
  "status": "FLAGGED",
  "result": null,
  "confidence": 0.30,
  "flags": ["[PAGINATION-UNMAPPED — MANUAL REVIEW]"],
  "trust_tier": "T1"
}
```