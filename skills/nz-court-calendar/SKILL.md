---
name: nz-court-calendar
description: Use this skill whenever a NZ court deadline, filing date, or working-day period needs to be calculated for a High Court matter. Invoke when @MANAGER or @PLANNER needs to compute response deadlines, filing windows, or hearing countdowns from a service date or event date. Also invoke when the user mentions any statutory period ("28 days", "within 20 working days") in connection with NZ court proceedings. Delegates working-day arithmetic to helpers/nz_calendar.py — do not reimplement date logic.
license: MIT
compatibility: Claude Code, Claude Desktop, Claude Cowork. Corpus tools need local Python 3.10+ and Ollama.
metadata:
  mode: GLASS
  version: 1.0.0
  source_kernel: nz_court_calendar.py
  function: run
  permissions: []
  trust_tier_required: 0
---


# nz-court-calendar

## Purpose
Computes NZ court deadlines and working-day periods per:
- High Court Rules 2016 (HCR) — filing and response periods
- Holidays Act 2003 Schedule 1 — public holiday exclusions
- Interpretation Act 1999 s29 — period extension when deadline falls
  on a non-working day

Delegates all working-day arithmetic to `helpers/nz_calendar.py`
(which wraps `helpers/court_calendar.py`). BN-09 is the GLASS
interpretation layer — it parses structured input, delegates
calculation, and returns structured deadline objects consumed by
@MANAGER and future @DEADLINE agent.

Note: Live courts.govt.nz calendar scraping is deferred to Sprint 2
when an MCP tool is available per Annex §6.3. This skill provides
deterministic deadline computation from known event dates.

## Input

| Field | Type | Required | Description |
|---|---|---|---|
| `event_date` | `str` | Yes | ISO-8601 date — service date or triggering event |
| `period_days` | `int` | Yes | Statutory period in working days |
| `period_type` | `str` | Yes | `"working"` \| `"calendar"` |
| `rule_ref` | `str` | No | HCR rule reference e.g. "r5.50" |
| `region` | `str` | No | NZ region for regional holidays e.g. "auckland" |
| `description` | `str` | No | Human-readable label for the deadline |
| `trust_tier` | `str` | Yes | T0–T3 |
| `operator_override` | `bool` | No | Required for T0. Default: false |

## Processing

1. T0 gate — if trust_tier is T0 and operator_override not true, halt
   with ERROR MALFORMED_INPUT.

2. Validate required fields — halt with ERROR MALFORMED_INPUT if missing.

3. Parse event_date as ISO-8601. If unparseable, halt with ERROR
   MALFORMED_INPUT.

4. Validate period_days >= 1. If not, halt with ERROR MALFORMED_INPUT.

5. Validate period_type is "working" or "calendar". If not, halt with
   ERROR MALFORMED_INPUT.

6. Calculate deadline:
   - If period_type == "working": delegate to
     `helpers.nz_calendar.court_filing_deadline(event_date, period_days, region)`
   - If period_type == "calendar": add period_days calendar days to
     event_date, then apply Interpretation Act 1999 s29 extension if
     result falls on a non-working day.

7. Apply Interpretation Act 1999 s29 — if computed deadline falls on a
   weekend or public holiday, extend to next working day.

8. Return structured deadline object with all computed fields.

## Confidence Signals

| Signal | Weight | How scored |
|---|---|---|
| `date_parsed` | 0.50 | 1.0 if event_date parsed cleanly; 0.0 if ambiguous |
| `period_unambiguous` | 0.30 | 1.0 if period_days and period_type explicit; 0.5 if inferred |
| `region_known` | 0.20 | 1.0 if region in known list or not provided; 0.5 if unknown |

## Ambiguity Handling

If event_date cannot be parsed as ISO-8601, output `status: ERROR`
with type `MALFORMED_INPUT` and halt.

If period_days < 1, output `status: ERROR` with type `MALFORMED_INPUT`
and halt.

If period_type is not "working" or "calendar", output `status: ERROR`
with type `MALFORMED_INPUT` and halt.

If region is provided but not in the known NZ region list, output
`status: FLAGGED` with flag `[REGION-UNKNOWN — MANUAL REVIEW]` — compute
without regional holidays and flag for review.

If computed deadline year is outside 2024–2030 (holiday data coverage),
output `status: FLAGGED` with flag `[DEADLINE-OUTSIDE-HOLIDAY-DATA-RANGE — MANUAL REVIEW]`.

Never guess a deadline. Never silently ignore a region mismatch.

## Output Schema

**Success payload:**
```json
{
  "status": "SUCCESS",
  "result": {
    "event_date": "2024-03-01",
    "deadline": "2024-04-10",
    "period_days": 28,
    "period_type": "working",
    "region": "auckland",
    "rule_ref": "r5.50",
    "description": "Statement of defence due",
    "interpretation_act_applied": false,
    "working_day_count": 28
  },
  "confidence": 0.95,
  "flags": [],
  "trust_tier": "T1"
}
```

**Flagged payload:**
```json
{
  "status": "FLAGGED",
  "result": null,
  "confidence": 0.50,
  "flags": ["[REGION-UNKNOWN — MANUAL REVIEW]"],
  "trust_tier": "T1"
}
```

**Error payload:**
```json
{
  "status": "ERROR",
  "result": null,
  "confidence": null,
  "flags": ["[MALFORMED-DATE]"],
  "error": {
    "type": "MALFORMED_INPUT",
    "message": "event_date '2024-13-01' is not valid ISO-8601",
    "retry_recommended": false,
    "input_hash": "sha256-of-input"
  }
}
```

## Quality Checks

Before returning output, verify:
1. deadline >= event_date — deadline cannot precede the triggering event
2. If interpretation_act_applied is true, deadline must be a working day
3. deadline year is within 2024–2030 holiday data range

## Examples

**Example 1 — 20 working days from service:**
Input:
```json
{
  "event_date": "2024-03-01",
  "period_days": 20,
  "period_type": "working",
  "rule_ref": "r5.50",
  "description": "Statement of defence due",
  "region": "auckland",
  "trust_tier": "T1"
}
```
Expected output:
```json
{
  "status": "SUCCESS",
  "result": {
    "event_date": "2024-03-01",
    "deadline": "2024-03-29",
    "period_days": 20,
    "period_type": "working",
    "region": "auckland",
    "rule_ref": "r5.50",
    "description": "Statement of defence due",
    "interpretation_act_applied": false,
    "working_day_count": 20
  },
  "confidence": 0.95,
  "flags": [],
  "trust_tier": "T1"
}
```

**Example 2 — case reference not found:**
Input:
```json
{
  "event_date": "2024-03-01",
  "period_days": 28,
  "period_type": "working",
  "region": "southpole",
  "trust_tier": "T1"
}
```
Expected output:
```json
{
  "status": "FLAGGED",
  "result": null,
  "confidence": 0.65,
  "flags": ["[REGION-UNKNOWN — MANUAL REVIEW]"],
  "trust_tier": "T1"
}
```