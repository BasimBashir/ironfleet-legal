---
name: nz-penalty-clause-analyzer
description: 'Quantitative assessment of whether a contractual clause is likely to be held unenforceable as a penalty under the CCLA 2017 / Cavendish test. Use when: Use when assessing whether a liquidated damages or default clause in a contract may be struck down as a penalty.  Computes the ratio of stipulated amount to actual loss and classifies risk level.'
license: MIT
compatibility: Claude Code, Claude Desktop, Claude Cowork. Corpus tools need local Python 3.10+ and Ollama.
metadata:
  version: 1.0.0
  source_kernel: ccla_2017.py
  function: analyze_penalty_clause
  parameters:
    clause_text:
      type: string
      required: true
      description: The text of the clause under analysis.
    actual_loss:
      type: number
      required: true
      description: Genuine pre-estimate of loss or actual loss suffered (>= 0).
    stipulated_amount:
      type: number
      required: true
      description: Amount the clause requires the breaching party to pay (>= 0).
  returns:
    is_likely_penalty:
      type: boolean
      description: True if risk level is HIGH.
    ratio:
      type: number
      description: Stipulated / actual_loss ratio (null if actual_loss is 0).
    risk_level:
      type: string
      description: LOW, MEDIUM, or HIGH.
    analysis:
      type: array
      description: List of analysis findings.
    clause_text:
      type: string
      description: Clause text (trimmed).
    actual_loss:
      type: number
      description: Actual loss (2 dp).
    stipulated_amount:
      type: number
      description: Stipulated amount (2 dp).
    excess_amount:
      type: number
      description: Amount by which stipulated exceeds actual loss (2 dp).
  iron_logic: true
  mode: both
  permissions: []
  trust_tier_required: 2
---


# NZ Penalty Clause Analyzer

Quantitative assessment of whether a contractual clause is likely to be held
unenforceable as a penalty under the **Contract and Commercial Law Act 2017**.

## Test Applied

The modern test (following *Cavendish Square Holding v Makdessi* [2015] UKSC 67,
adopted in NZ) asks whether the stipulated sum is **out of all proportion to
any legitimate interest** the innocent party has in the enforcement of the
primary obligation.

## Risk Thresholds

| Ratio (stipulated/loss) | Risk Level |
|---|---|
| <= 1.0 | LOW — no uplift |
| <= 1.5 | LOW — modest uplift, likely enforceable |
| <= 3.0 | MEDIUM — may be challenged |
| > 3.0 | HIGH — likely a penalty |

## Example

```python
result = execute_skill("nz-penalty-clause-analyzer", {
    "clause_text": "Late payment fee of $5,000 per day",
    "actual_loss": 1000,
    "stipulated_amount": 5000,
})
# → {"is_likely_penalty": True, "ratio": 5.0, "risk_level": "HIGH", ...}
```
