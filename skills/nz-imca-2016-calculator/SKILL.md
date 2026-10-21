---
name: nz-imca-2016-calculator
description: 'Calculates simple daily interest under the Interest on Money Claims Act 2016 (NZ) using the Actual/365-Fixed convention and exact Decimal arithmetic. Use when: Use when computing interest on overdue debts, judgment debts, or contractual sums where the NZ prescribed rate (7.93% p.a.) or a specified rate applies. Required for any monetary claim that includes accrued interest.'
license: MIT
compatibility: Claude Code, Claude Desktop, Claude Cowork. Corpus tools need local Python 3.10+ and Ollama.
metadata:
  version: 1.0.0
  source_kernel: imca_2016.py
  function: calculate_interest
  parameters:
    principal:
      type: number
      required: true
      description: The sum of money on which interest accrues (>= 0).
    start_date:
      type: string
      format: date
      required: true
      description: ISO-8601 date from which interest begins (excluded from count).
    end_date:
      type: string
      format: date
      required: true
      description: ISO-8601 date to which interest is calculated (included).
    rate:
      type: number
      required: false
      default: 7.93
      description: Annual percentage rate. Defaults to NZ prescribed rate (7.93%).
  returns:
    principal:
      type: number
      description: Original sum (2 dp).
    rate:
      type: number
      description: Annual rate used.
    days:
      type: integer
      description: Calendar days in the period.
    daily_interest:
      type: number
      description: Per-day interest amount (2 dp).
    total_interest:
      type: number
      description: Accrued interest for the period (2 dp).
    total_amount:
      type: number
      description: Principal + total interest (2 dp).
  iron_logic: true
  mode: both
  permissions: []
  trust_tier_required: 2
---


# NZ IMCA 2016 Interest Calculator

Computes simple interest on a daily basis using the **Actual/365-Fixed**
convention, which is standard in New Zealand courts.

## Prescribed Rate

The default rate (7.93% p.a.) is set by the Interest on Money Claims Act 2016
and the Interest Rate Order.  Callers may supply a different contractual or
court-ordered rate.

## Formula

```
daily_interest = principal × rate / 100 / 365
total_interest = daily_interest × days
total_amount   = principal + total_interest
```

All values computed with exact `Decimal` arithmetic — no floating-point
estimates are ever produced (Iron Logic).

## Example

```python
result = execute_skill("nz-imca-2016-calculator", {
    "principal": 10000,
    "start_date": "2024-01-15",
    "end_date": "2025-01-15",
})
# → {"principal": 10000.0, "rate": 7.93, "days": 366, ...}
```
