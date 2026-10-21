---
name: nz-nutrient-processor
description: Use this skill whenever @CLERK needs to redact PII from discovery documents, digitally sign affidavits or correspondence, convert DOCX outputs to PDF/A for HCR-compliant bundle assembly, perform OCR on scanned documents where kreuzberg's Tesseract path is insufficient, or programmatically fill NZ court forms. Only invoke for OPEN-classified documents — never route WP or WPSATC documents through this skill. Adapted from PSPDFKit-labs/nutrient-agent-skill — Iron Fleet contextualised for NZ legal workflows, privilege-safe cloud routing, and ENABLE_PRIVILEGE_GUARD enforcement.
license: MIT-0
compatibility: Claude Code, Claude Desktop, Claude Cowork. Corpus tools need local Python 3.10+ and Ollama.
metadata:
  mode: IRON
  version: 1.0.0
  source_kernel: nz_nutrient_processor.py
  function: run
  permissions:
  - api_access
  trust_tier_required: 1
  adapted_from: PSPDFKit-labs/nutrient-agent-skill
  egress_warning: Body references the Nutrient cloud API (api.nutrient.io) - never use on privileged documents.
---


# nz-nutrient-processor

## Purpose
Cloud-based document processing for Iron Fleet @CLERK pipeline. Adapted from
PSPDFKit-labs/nutrient-agent-skill (Nutrient DWS API).

## CRITICAL — Privilege Guard

⚠️ This skill calls an external cloud API. All documents transit Nutrient's
servers. This must be treated as an LLM-equivalent external call under Iron
Fleet's privilege architecture.

**NEVER route WP or WPSATC documents through this skill.**

Before any API call, the privilege guard check is MANDATORY:
```python
from helpers.privilege_protection import PrivilegeProtection

guard = PrivilegeProtection()
result = guard.scan_for_privilege(document_text)
if result.privilege_class in ("WP", "WPSATC"):
    raise PrivilegeViolationError("WP/WPSATC document must not go to Nutrient API")
```

Only OPEN-classified documents may use this skill.

## What nutrient provides for Iron Fleet

| Capability | Iron Fleet Application |
|---|---|
| AI-mode PII redaction | Redact names, addresses, IRD numbers before T0 classification |
| Pattern redaction | IRD numbers, account numbers, credit card patterns from financial statements |
| Digital signatures (PAdES) | Sign affidavits and correspondence — @CLERK filing workflow |
| OCR (20+ languages) | Fallback OCR for multilingual exhibits, handwritten annotations |
| PDF/DOCX conversion | Convert @CLERK DOCX outputs to PDF/A for HCR bundle assembly |
| Form filling | Programmatically complete NZ court forms — statutory demand workflow |

## Security Requirements

- `NUTRIENT_DWS_API_KEY` must be managed via varlock — never in plain .env
- Key must be rotated immediately if exposed in any session
- All API calls must be logged to the Iron Fleet audit trail
- Basim must sign off on any code touching the Nutrient API call path
- Use MCP server variant (`@nutrient-sdk/dws-mcp-server`) — not HTTP direct

## Input

| Field | Type | Required | Description |
|---|---|---|---|
| `document_path` | `str` | Yes | Path to OPEN-classified document |
| `operation` | `str` | Yes | `"redact_pii"` \| `"sign"` \| `"ocr"` \| `"convert_pdf"` \| `"fill_form"` |
| `privilege_class` | `str` | Yes | Must be `"OPEN"` — skill rejects all others |
| `redaction_patterns` | `list` | No | Additional regex patterns for redaction |
| `signature_field` | `str` | No | Field name for digital signature |
| `form_data` | `dict` | No | Key-value pairs for form filling |
| `trust_tier` | `str` | Yes | T0–T3 |
| `operator_override` | `bool` | No | Required for T0. Default: false |

## Processing

### Step 1 — Privilege gate (MANDATORY)
Check privilege_class field. If not "OPEN", halt immediately with ERROR.
This is non-negotiable — no exceptions.

### Step 2 — API key check
Confirm NUTRIENT_DWS_API_KEY is available in environment.
If missing, output ERROR with DEPENDENCY_UNAVAILABLE.

### Step 3 — Operation routing
Route to appropriate Nutrient DWS endpoint:
- `redact_pii` → POST /api/build with redaction instructions
- `sign` → POST /api/build with PAdES digital signature
- `ocr` → POST /api/build with OCR action
- `convert_pdf` → POST /api/build with PDF/A conversion
- `fill_form` → POST /api/build with form field values

### Step 4 — Audit log
Log: document hash, operation, timestamp, API response status.
Never log document content or API key.

## Confidence Signals

| Signal | Weight | How scored |
|---|---|---|
| `privilege_gate_passed` | 0.50 | 1.0 if OPEN confirmed; 0.0 if WP/WPSATC |
| `api_key_available` | 0.30 | 1.0 if key present; 0.0 if missing |
| `operation_valid` | 0.20 | 1.0 if known operation; 0.0 if unknown |

## Ambiguity Handling

If privilege_class is not explicitly "OPEN", output `status: ERROR` with
`[PRIVILEGE-GUARD-BLOCKED — WP/WPSATC DOCUMENT]` and halt immediately.

If NUTRIENT_DWS_API_KEY not in environment, output `status: ERROR` with
`[NUTRIENT-API-KEY-MISSING — CHECK VARLOCK]`.

If operation is unknown, output `status: ERROR` with `MALFORMED_INPUT`.

Never proceed if privilege gate has not explicitly passed.

## Output Schema
```json
{
  "status": "SUCCESS | FLAGGED | ERROR",
  "result": {
    "operation": "redact_pii",
    "document_path": "docs/affidavit.pdf",
    "output_path": "docs/affidavit_redacted.pdf",
    "privilege_gate_passed": true,
    "audit_entry": {
      "doc_sha256": "abc123...",
      "operation": "redact_pii",
      "timestamp": "2024-03-01T09:00:00",
      "api_status": 200
    }
  },
  "confidence": 0.92,
  "flags": [],
  "trust_tier": "T1"
}
```

## New Flags

- `[PRIVILEGE-GUARD-BLOCKED — WP/WPSATC DOCUMENT]`
- `[NUTRIENT-API-KEY-MISSING — CHECK VARLOCK]`
- `[NUTRIENT-API-ERROR — MANUAL REVIEW]`
- `[REDACTION-INCOMPLETE — MANUAL REVIEW]`