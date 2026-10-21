---
name: exhibit-numberer
description: 'Use this skill whenever an affidavit or hearing bundle requires sequential exhibit labels to be assigned to a list of documents. Invoke when @SCRIBE is assembling an affidavit and a document list is present, even if the user has not explicitly requested exhibit numbering. Also invoke when hearing-bundle-assembler (BN-04) requires a pre-labelled exhibit schedule. Trigger on any input containing documents: list with filename and date fields in an affidavit assembly context.'
license: MIT
compatibility: Claude Code, Claude Desktop, Claude Cowork. Corpus tools need local Python 3.10+ and Ollama.
metadata:
  iron_logic: true
  version: 1.0.0
  source_kernel: exhibit_numberer.py
  function: run
  mode: both
  permissions: []
  trust_tier_required: 0
---


# exhibit-numberer

## Purpose
Assigns sequential exhibit labels (A, B, C… or 1, 2, 3…) to a list of documents
per HCR r9.76 and returns a numbered schedule ready for affidavit annexure.
Feeds directly into affidavit-formatter (BN-02) and hearing-bundle-assembler (BN-04).
Without this skill, @SCRIBE produces exhibit references that conflict with HCR
formatting requirements, creating a filing-stage rework cycle.

## Input

| Field | Type | Required | Description |
|---|---|---|---|
| `documents` | `list[dict]` | Yes | Each dict: `{id: str, filename: str, date: ISO8601 str}` |
| `label_style` | `str` | Yes | `"alpha"` (A, B, C…) or `"numeric"` (1, 2, 3…) |
| `deponent_name` | `str` | Yes | Name of the deponent for schedule header |
| `starting_label` | `str` | No | Override starting label. Default: `"A"` (alpha) or `"1"` (numeric) |

## Processing

1. Validate `label_style` is exactly `"alpha"` or `"numeric"`. If neither, halt immediately
   with ERROR MALFORMED_INPUT — do not attempt to infer intent from a bad value.

2. Validate `documents` is not empty. If empty, output FLAGGED with
   `[EXHIBIT-LIST-EMPTY — MANUAL REVIEW]` and halt. An empty list cannot produce
   a valid schedule and must be reviewed by the practitioner.

3. Determine starting label:
   - If `starting_label` provided, use it as the sequence start.
   - If not provided, use `"A"` for alpha style or `"1"` for numeric style.

4. Generate sequential labels for each document in order:
   - Alpha style: A, B, C… Z, then AA, AB… AZ, BA… (26+ document rule).
     The transition to two-character labels at document 27 is intentional and
     declared — @SCRIBE must be aware so the affidavit body references match.
   - Numeric style: 1, 2, 3… (no upper limit).

5. Build the schedule — for each document produce:
   `{label: str, id: str, filename: str, date: ISO8601 str}`
   preserving the original input order. Order is the practitioner's responsibility —
   this skill does not reorder documents.

6. Return SUCCESS with the completed schedule.

## Ambiguity Handling

If `documents` is empty, output `status: FLAGGED` with flag
`[EXHIBIT-LIST-EMPTY — MANUAL REVIEW]` and halt.

If `label_style` is not `"alpha"` or `"numeric"`, output `status: ERROR` with
type `MALFORMED_INPUT` and halt.

If any document dict is missing `id`, `filename`, or `date`, output `status: ERROR`
with type `MALFORMED_INPUT`, include the index of the malformed entry in the
error message, and halt.

Never infer. Never default on malformed input. Always halt and surface the error.

## Output Schema

**Success payload:**
```json
{
  "status": "SUCCESS",
  "result": {
    "schedule": [
      {
        "label": "A",
        "id": "doc-001",
        "filename": "invoice_2024_001.pdf",
        "date": "2024-03-15"
      }
    ],
    "label_style": "alpha",
    "deponent_name": "John Smith",
    "total_exhibits": 1
  },
  "flags": []
}
```

**Flagged payload:**
```json
{
  "status": "FLAGGED",
  "result": null,
  "flags": ["[EXHIBIT-LIST-EMPTY — MANUAL REVIEW]"]
}
```

**Error payload:**
```json
{
  "status": "ERROR",
  "result": null,
  "flags": ["[ERROR-TYPE]"],
  "error": {
    "type": "MALFORMED_INPUT",
    "message": "label_style must be 'alpha' or 'numeric' — received: 'sequential'",
    "retry_recommended": false,
    "input_hash": "sha256-of-input"
  }
}
```

## Quality Checks

Before returning output, verify:
1. Label sequence has no gaps and no duplicates — iterate the schedule and confirm
   each label is exactly one step ahead of the previous.
2. Total exhibits in result matches length of input documents list.
3. All original document fields (id, filename, date) are preserved unchanged in output —
   this skill labels, it does not transform.

## Examples

**Example 1 — alpha style, 3 documents:**
Input:
```json
{
  "documents": [
    {"id": "doc-001", "filename": "contract.pdf", "date": "2024-01-10"},
    {"id": "doc-002", "filename": "invoice.pdf", "date": "2024-02-14"},
    {"id": "doc-003", "filename": "email.pdf", "date": "2024-03-01"}
  ],
  "label_style": "alpha",
  "deponent_name": "Jane Doe"
}
```
Expected output:
```json
{
  "status": "SUCCESS",
  "result": {
    "schedule": [
      {"label": "A", "id": "doc-001", "filename": "contract.pdf", "date": "2024-01-10"},
      {"label": "B", "id": "doc-002", "filename": "invoice.pdf", "date": "2024-02-14"},
      {"label": "C", "id": "doc-003", "filename": "email.pdf", "date": "2024-03-01"}
    ],
    "label_style": "alpha",
    "deponent_name": "Jane Doe",
    "total_exhibits": 3
  },
  "flags": []
}
```

**Example 2 — empty list → FLAGGED:**
Input:
```json
{
  "documents": [],
  "label_style": "alpha",
  "deponent_name": "Jane Doe"
}
```
Expected output:
```json
{
  "status": "FLAGGED",
  "result": null,
  "flags": ["[EXHIBIT-LIST-EMPTY — MANUAL REVIEW]"]
}
```