---
name: summariser
description: 'Use this skill whenever a case document, correspondence bundle, or legal matter requires summarisation for either practitioner review or client communication. Invoke when @CLERK or @STRAT needs a summary of case progress, when a client update is required, or when a practitioner needs a technical brief of a matter. Two levels: practitioner (technical, citations preserved) and client (plain English, no jargon). Always invoke with an explicit level parameter — never default silently.'
license: Apache-2.0
compatibility: Claude Code, Claude Desktop, Claude Cowork. Corpus tools need local Python 3.10+ and Ollama.
metadata:
  mode: GLASS
  version: 1.0.0
  permissions: []
  trust_tier_required: 1
  adapted_from: anthropics/knowledge-work-plugins
---


# summariser

## Purpose
Produces two-level summaries of NZ legal matters — practitioner level and
client level — from case documents, correspondence bundles, or @CLERK output.

Adapted from the anthropics/knowledge-work-plugins legal-risk-assessment
documentation standards pattern. The risk assessment memo format maps
directly to practitioner-level summary structure. The risk register entry
format (brief, structured, owner-assigned) maps to client-level output.

Feeds @CLERK (for client communications) and @STRAT (for strategy briefs).
Practitioner-level output preserves citations for downstream use by
@WARGAMER and @NEGOTIATOR.

## Input

| Field | Type | Required | Description |
|---|---|---|---|
| `content` | `str` | Yes | Document or bundle text to summarise |
| `level` | `str` | Yes | `"practitioner"` \| `"client"` |
| `matter_ref` | `str` | No | Matter reference number for header |
| `date` | `str` | No | Summary date ISO-8601 |
| `trust_tier` | `str` | Yes | T0–T3 |
| `operator_override` | `bool` | No | Required for T0. Default: false |
| `case_state` | `dict` | No | Read-only. Fields: case_number, parties |

## Processing

### Both levels
1. T0 gate — if trust_tier is T0 and operator_override not true, halt with
   ERROR MALFORMED_INPUT.
2. Validate level is exactly "practitioner" or "client" — if not, halt with
   ERROR MALFORMED_INPUT.
3. Validate content is not empty — if empty, halt with ERROR MALFORMED_INPUT.

### Practitioner level
4. Produce structured technical summary using the following format
   (adapted from anthropics/knowledge-work-plugins risk assessment memo):
   - **Matter**: reference + parties
   - **Status**: current procedural position
   - **Key Facts**: material facts with paragraph/document references
   - **Legal Issues**: issues identified with statutory/case law citations preserved
   - **Risks**: current risk profile (adapted from severity x likelihood framework)
   - **Next Steps**: action items with owner and deadline
5. Preserve all citations — case names, statutory references, rule numbers.
   Citations are consumed by @WARGAMER and @NEGOTIATOR downstream.
6. Flag any privileged material detected in content with
   [PRIVILEGE-DETECTED — REVIEW-BEFORE-DISTRIBUTION].

### Client level
4. Produce plain English summary — no legal jargon, no citations, no rule numbers.
5. Structure: what has happened, where things stand, what happens next,
   what the client needs to do (if anything).
6. Never include: privilege analysis, litigation strategy, risk scores,
   fee estimates, or practitioner opinions on merits.
7. Add disclaimer: "This summary is prepared by your legal team for
   information purposes. Please contact us if you have any questions."

## Confidence Signals

| Signal | Weight | How scored |
|---|---|---|
| `summary_completeness` | [GFU] | 1.0 if all required sections present; proportional if partial |
| `tone_match` | [GFU] | 1.0 if tone matches level (technical/plain); 0.0 if wrong tone |
| `citation_preservation` | [GFU] | 1.0 if citations preserved (practitioner) or absent (client); 0.0 if violated |
| `context_consistent` | [GFU] | 1.0 if summary consistent with source content |

*All weights marked [GFU] — to be set by GFU during spec review.*
*Awaiting GFU Step 12 two-level summary examples before script build.*

## Ambiguity Handling

If `level` is not exactly `"practitioner"` or `"client"`, output
`status: ERROR` with type `MALFORMED_INPUT` and halt.

If `content` is empty or whitespace only, output `status: ERROR` with
type `MALFORMED_INPUT` and halt.

If privileged material is detected in content being summarised for
client level, output `status: FLAGGED` with flag
`[PRIVILEGE-DETECTED — REVIEW-BEFORE-DISTRIBUTION]` and halt.

If confidence < 0.50, output `status: FLAGGED` with
`[ESCALATE-TO-IRON — SUMMARY-QUALITY-UNCERTAIN]` and halt.

If confidence >= 0.50 and < 0.75, output `status: FLAGGED` with
`[REVIEW-REQUIRED — SUMMARY-COMPLETENESS-UNCERTAIN]` and halt.

Never include litigation strategy or merits opinions in client-level output.
Never strip citations from practitioner-level output.

## Output Schema

**Success payload:**
```json
{
  "status": "SUCCESS",
  "result": {
    "level": "practitioner | client",
    "summary": "Full summary text",
    "sections": ["Status", "Key Facts", "Legal Issues", "Risks", "Next Steps"],
    "word_count": 320,
    "privilege_flag": false
  },
  "confidence": 0.88,
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
  "flags": ["[PRIVILEGE-DETECTED — REVIEW-BEFORE-DISTRIBUTION]"],
  "trust_tier": "T1"
}
```

**Error payload:**
```json
{
  "status": "ERROR",
  "result": null,
  "confidence": null,
  "flags": ["[MISSING-REQUIRED-FIELD]"],
  "error": {
    "type": "MALFORMED_INPUT",
    "message": "level must be 'practitioner' or 'client'",
    "retry_recommended": false,
    "input_hash": "sha256-of-input"
  }
}
```

## Quality Checks

Before returning output, verify:
1. Practitioner level: all citations from source content are preserved in output
2. Client level: no citations, rule numbers, or jargon in output
3. Client level: privilege flag checked — never distribute privileged analysis
   to client without review gate

## Examples

**Example 1 — practitioner summary:**
Input:
```json
{
  "content": "The plaintiff filed a statement of claim on 14 March 2024 under the Contract and Commercial Law Act 2017 s83. The defendant filed a statement of defence on 15 April 2024 denying all allegations. A case management conference is scheduled for 1 May 2024.",
  "level": "practitioner",
  "matter_ref": "OA-2024-001",
  "trust_tier": "T1"
}
```
Expected output:
```json
{
  "status": "SUCCESS",
  "result": {
    "level": "practitioner",
    "summary": "## Matter: OA-2024-001\n\n**Status:** Pleadings stage — defence filed, CMC pending\n\n**Key Facts:** SOC filed 14 March 2024 (CCLA 2017 s83). SOD filed 15 April 2024, full traverse.\n\n**Legal Issues:** Breach of contract under CCLA 2017 s83.\n\n**Next Steps:** CMC 1 May 2024 — confirm discovery timetable.",
    "sections": ["Status", "Key Facts", "Legal Issues", "Next Steps"],
    "word_count": 58,
    "privilege_flag": false
  },
  "confidence": 0.91,
  "flags": [],
  "trust_tier": "T1"
}
```

**Example 2 — client summary:**
Input:
```json
{
  "content": "The plaintiff filed a statement of claim on 14 March 2024 under the Contract and Commercial Law Act 2017 s83. The defendant filed a statement of defence on 15 April 2024 denying all allegations. A case management conference is scheduled for 1 May 2024.",
  "level": "client",
  "trust_tier": "T1"
}
```
Expected output:
```json
{
  "status": "SUCCESS",
  "result": {
    "level": "client",
    "summary": "We filed your claim in March 2024. The other side has responded denying your allegations, which is standard at this stage. There is a court meeting scheduled for 1 May 2024 where we will set out the timetable for the case. No action is required from you at this time.\n\nThis summary is prepared by your legal team for information purposes. Please contact us if you have any questions.",
    "sections": ["What has happened", "Where things stand", "What happens next"],
    "word_count": 72,
    "privilege_flag": false
  },
  "confidence": 0.90,
  "flags": [],
  "trust_tier": "T1"
}
```