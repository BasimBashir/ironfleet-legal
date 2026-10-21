---
name: nz-statutory-demand-validator
description: 'Validates a statutory demand under s 289 of the Companies Act 1993 (NZ) and computes the compliance deadline using NZ working-day calendar. Use when: Use when preparing or reviewing a statutory demand for debt recovery against a company, checking prescribed minimum amounts, required fields, and computing compliance deadlines.'
license: MIT
compatibility: Claude Code, Claude Desktop, Claude Cowork. Corpus tools need local Python 3.10+ and Ollama.
metadata:
  version: 1.0.0
  source_kernel: companies_act.py
  function: validate_statutory_demand
  parameters:
    amount:
      type: number
      required: true
      description: Debt amount claimed (must be >= $1,000 prescribed minimum).
    debtor_company:
      type: string
      required: true
      description: Name of the debtor company.
    creditor:
      type: string
      required: true
      description: Name of the creditor.
    debt_details:
      type: string
      required: true
      description: Description of the debt (nature, basis, particulars).
    service_date:
      type: string
      format: date
      required: false
      default: today
      description: Date the demand was/will be served. Defaults to today.
    compliance_period:
      type: integer
      required: false
      default: 15
      description: Working days for company to comply (statutory minimum 15).
    region:
      type: string
      required: false
      description: NZ region for regional holidays in deadline calculation.
  returns:
    is_valid:
      type: boolean
      description: Whether the demand meets all statutory requirements.
    issues:
      type: array
      description: List of validation issues found.
    amount:
      type: number
      description: Debt amount (2 dp).
    debtor_company:
      type: string
      description: Debtor company name.
    creditor:
      type: string
      description: Creditor name.
    compliance_deadline:
      type: string
      description: Last day to comply (ISO-8601).
    compliance_period_working_days:
      type: integer
      description: Working days allowed.
    service_date:
      type: string
      description: Service date (ISO-8601).
  iron_logic: true
  mode: both
  permissions: []
  trust_tier_required: 1
---


# NZ Statutory Demand Validator

Validates a statutory demand under **s 289 of the Companies Act 1993** and
computes the compliance deadline per **s 241(4)(a)**.

## Requirements

- Debt must be due and owing
- Amount must meet the prescribed minimum (NZD $1,000)
- Demand must identify creditor, debtor company, and debt particulars
- Company has at least 15 working days to comply after service

## Compliance Deadline

The deadline is calculated using the NZ working-day calendar, which excludes
weekends and public holidays (national + regional).

## Example

```python
result = execute_skill("nz-statutory-demand-validator", {
    "amount": 5000,
    "debtor_company": "Acme Ltd",
    "creditor": "Smith & Co",
    "debt_details": "Unpaid invoice #1234 for consulting services",
    "service_date": "2026-02-06",
})
# → {"is_valid": True, "compliance_deadline": "2026-02-27", ...}
```
