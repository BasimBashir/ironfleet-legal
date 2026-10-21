---
name: nz-solvency-assessor
description: 'Responsible lending compliance checks under the Credit Contracts and Consumer Finance Act 2003 (NZ), including affordability assessment and total cost of credit calculation. Use when: Use when assessing whether a loan meets responsible lending obligations, calculating affordability ratios, computing total cost of credit, or checking for potential borrower hardship.'
license: MIT
compatibility: Claude Code, Claude Desktop, Claude Cowork. Corpus tools need local Python 3.10+ and Ollama.
metadata:
  version: 1.0.0
  source_kernel: cccfa_2003.py
  function: check_compliance
  parameters:
    loan_details:
      type: object
      required: true
      description: 'Dict with required keys: borrower_annual_income (> 0), borrower_monthly_expenses (>= 0), loan_amount (> 0), annual_interest_rate (>= 0), loan_term_months (> 0). Optional: fees (>= 0, default 0).

        '
  returns:
    is_compliant:
      type: boolean
      description: Whether the loan passes all compliance checks.
    issues:
      type: array
      description: List of compliance issues found.
    monthly_repayment:
      type: number
      description: Monthly repayment amount (2 dp).
    total_interest:
      type: number
      description: Total interest over term (2 dp).
    total_cost_of_credit:
      type: number
      description: Total interest + fees (2 dp).
    total_repayment:
      type: number
      description: Total amount repaid (2 dp).
    affordability_ratio:
      type: number
      description: Repayment / disposable income ratio (null if no disposable income).
    monthly_surplus:
      type: number
      description: Disposable income minus repayment (2 dp).
    risk_level:
      type: string
      description: LOW, MEDIUM, HIGH, or CRITICAL.
  iron_logic: true
  mode: both
  permissions: []
  trust_tier_required: 2
---


# NZ Solvency Assessor (CCCFA 2003)

Responsible lending compliance checks under the **Credit Contracts and Consumer
Finance Act 2003**.

## CCCFA 2003 Requirements

- Lender must make reasonable inquiries into the borrower's financial position
  (s 9C)
- Loan must not cause substantial hardship
- Full disclosure of total cost of credit, interest, and fees

## Affordability Thresholds

| Ratio (repayment / disposable income) | Risk Level |
|---|---|
| <= 30% | LOW |
| 30% - 50% | MEDIUM — review for potential hardship |
| > 50% | HIGH — likely substantial hardship |
| No disposable income | CRITICAL |

## Calculation

Uses the standard amortisation formula with exact `Decimal` arithmetic:

```
M = P × r(1+r)^n / ((1+r)^n - 1)
```

## Example

```python
result = execute_skill("nz-solvency-assessor", {
    "loan_details": {
        "borrower_annual_income": 80000,
        "borrower_monthly_expenses": 3000,
        "loan_amount": 20000,
        "annual_interest_rate": 7.93,
        "loan_term_months": 36,
    }
})
# → {"is_compliant": True, "monthly_repayment": 625.47, ...}
```
