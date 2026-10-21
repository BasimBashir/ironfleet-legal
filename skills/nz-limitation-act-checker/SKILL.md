---
name: nz-limitation-act-checker
description: 'Determines whether a claim is time-barred under the Limitation Act 2010 (NZ) based on the cause of action date and claim type. Use when: Use when assessing whether a legal claim can still be filed, checking statutory deadlines, or advising on limitation periods for contracts, torts, debts, defamation, personal injury, land, judgments, or equitable claims.'
license: MIT
compatibility: Claude Code, Claude Desktop, Claude Cowork. Corpus tools need local Python 3.10+ and Ollama.
metadata:
  version: 1.0.0
  source_kernel: limitation_act.py
  function: check_limitation
  parameters:
    cause_of_action_date:
      type: string
      format: date
      required: true
      description: ISO-8601 date the cause of action accrued.
    claim_type:
      type: string
      required: true
      description: 'One of: contract, tort, negligence, debt, defamation, personal_injury, land, judgment, equity.'
    reference_date:
      type: string
      format: date
      required: false
      default: today
      description: Date to assess against. Defaults to today.
  returns:
    is_barred:
      type: boolean
      description: True if the limitation period has expired.
    limitation_period_years:
      type: integer
      description: Statutory period for this claim type.
    expiry_date:
      type: string
      description: Last date to file (ISO-8601).
    days_remaining:
      type: integer
      description: Days until expiry (negative if barred).
    claim_type:
      type: string
      description: Normalised claim type.
    cause_of_action_date:
      type: string
      description: As supplied (ISO-8601).
    reference_date:
      type: string
      description: The date assessed against (ISO-8601).
  iron_logic: true
  mode: both
  permissions: []
  trust_tier_required: 0
---


# NZ Limitation Act 2010 Checker

Determines whether a claim is time-barred based on the date the cause of
action accrued and the type of claim.

## Key Limitation Periods

| Claim Type | Period | Section |
|---|---|---|
| Contract, tort, debt | 6 years | s 11(1) |
| Personal injury | 3 years | s 11(2) |
| Defamation | 2 years | s 14 |
| Recovery of land | 12 years | s 11(3) |
| Judgment enforcement | 6 years | — |
| Equitable claims | 12 years | — |

## Example

```python
result = execute_skill("nz-limitation-act-checker", {
    "cause_of_action_date": "2020-03-15",
    "claim_type": "contract",
    "reference_date": "2026-02-06",
})
# → {"is_barred": True, "limitation_period_years": 6, ...}
```
