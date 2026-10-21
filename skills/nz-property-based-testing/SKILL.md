---
name: nz-property-based-testing
description: Use this skill whenever writing tests for Iron Fleet skills or simulation modules that involve serialization, parsing, mathematical calculations, deterministic transformations, or data validation. Invoke automatically when you detect encode/decode pairs, confidence score calculations, date arithmetic, financial amount processing, or schema validation in any skill script. Especially invoke for SIM-A-19 BATNA/WATNA calculations, SIM-A-21 accuracy tracking, BN-01 label generation, and any Category A Iron Logic skill. Adapted from trailofbits/skills property-based-testing — Iron Fleet contextualised for NZ legal data patterns and Decimal arithmetic requirements.
license: CC-BY-SA-4.0
compatibility: Claude Code, Claude Desktop, Claude Cowork. Corpus tools need local Python 3.10+ and Ollama.
metadata:
  mode: GLASS
  version: 1.0.0
  source_kernel: nz_property_based_testing.py
  function: run
  permissions: []
  trust_tier_required: 1
  adapted_from: trailofbits/skills
---


# nz-property-based-testing

## Purpose
Guides property-based testing (PBT) for Iron Fleet skills and simulation
modules. Adapted from trailofbits/skills `property-based-testing`.

PBT finds edge cases that example-based tests miss — critical for Iron
Fleet because legal data has high-cardinality inputs (NZ dates, monetary
amounts, document text) and deterministic functions must be provably correct
for Iron Logic (Category A) skills.

## When to Invoke Automatically

**Always invoke when detecting:**
- `encode`/`decode`, `serialize`/`deserialize` pairs
- `calculate_confidence()` — weighted signal arithmetic must be stable
- Date arithmetic in `helpers/nz_calendar.py` — working-day calculations
- Financial amounts using `decimal.Decimal` — no float drift permitted
- Label generation (BN-01) — alpha/numeric sequences must be exhaustive
- Schema validation — Iron Fleet output dicts must match declared schema
- Simulation outputs (SIM-A-19, SIM-A-21) — BATNA/WATNA are mathematical

**Priority by Iron Fleet pattern:**

| Pattern | Property | Priority | Skill |
|---|---|---|---|
| `calculate_confidence()` | Output always in [0.0, 1.0] | HIGH | All GLASS/IRON |
| `court_filing_deadline()` | deadline >= service_date | HIGH | BN-09 |
| `_alpha_label(n)` | No duplicates, sequential | HIGH | BN-01 |
| Date parsing | Roundtrip ISO-8601 | HIGH | BN-09, IN-02 |
| Decimal arithmetic | No float at intermediate steps | HIGH | All Category A |
| WP classification | Deterministic for same input | HIGH | BN-03 |
| Bundle page map | No duplicate pdf_page values | MEDIUM | BN-05 |
| BATNA/WATNA | WATNA <= BATNA always | HIGH | SIM-A-19 |
| Accuracy delta | delta = predicted - actual | MEDIUM | SIM-A-21 |

## Property Catalog for Iron Fleet

| Property | Formula | Iron Fleet Application |
|---|---|---|
| **Roundtrip** | `decode(encode(x)) == x` | ISO-8601 dates, JSON serialisation |
| **Idempotence** | `f(f(x)) == f(x)` | Confidence clamping, label normalisation |
| **Bounded output** | `0.0 <= confidence <= 1.0` | All GLASS/IRON confidence scores |
| **Monotonicity** | `n1 < n2 → label(n1) != label(n2)` | BN-01 alpha/numeric labels |
| **No exception** | No crash on valid input | All skill `run()` functions |
| **Determinism** | `f(x) == f(x)` always | All Category A Iron Logic skills |
| **Decimal invariant** | No float in intermediate calc | All financial/confidence arithmetic |
| **Order preservation** | Chronological sort stable | BN-04 bundle assembly |

## How to Write PBT for Iron Fleet Skills

### Step 1 — Identify the pattern
```python
# Example: calculate_confidence() has bounded output property
# Input: any list of (name, weight, score) where weights sum to 1.0
# Property: output always in [0.0, 1.0]
```

### Step 2 — Choose the library
For Iron Fleet Python skills use **Hypothesis**:
```python
from hypothesis import given, strategies as st

@given(
    score=st.floats(min_value=0.0, max_value=1.0, allow_nan=False)
)
def test_confidence_bounded(score):
    signals = [("test_signal", 1.0, score)]
    result = calculate_confidence(signals)
    assert 0.0 <= result <= 1.0
```

### Step 3 — Write the property
```python
# Determinism property for Category A skills
@given(st.integers(min_value=0, max_value=10000))
def test_alpha_label_deterministic(n):
    label1 = _alpha_label(n)
    label2 = _alpha_label(n)
    assert label1 == label2

# No-duplicate property for label generation
@given(st.lists(st.integers(min_value=0, max_value=1000),
                min_size=2, unique=True))
def test_alpha_labels_no_duplicates(indices):
    labels = [_alpha_label(i) for i in indices]
    assert len(labels) == len(set(labels))
```

### Step 4 — Run and interpret failures
Hypothesis shrinks failing inputs to minimal examples. A failure means
the property is violated — this is a real bug, not a test issue.

## Confidence Signals

| Signal | Weight | How scored |
|---|---|---|
| `pattern_detected` | 0.50 | 1.0 if PBT-suitable pattern found; 0.0 if not |
| `property_defined` | 0.30 | 1.0 if clear property stated; 0.5 if implicit |
| `library_available` | 0.20 | 1.0 if Hypothesis installed; 0.5 if manual only |

## Ambiguity Handling

If no PBT-suitable pattern is detected, output `status: FLAGGED` with
`[NO-PBT-PATTERN-DETECTED — REVIEW]` — use example-based tests instead.

If user declines PBT after suggestion, do not push further — write
good example-based tests without further prompting.

Never recommend PBT for simple CRUD, UI logic, or integration tests.

## Output Schema
```json
{
  "status": "SUCCESS | FLAGGED",
  "result": {
    "patterns_detected": ["roundtrip", "bounded_output"],
    "recommended_properties": [
      {
        "pattern": "bounded_output",
        "property": "0.0 <= calculate_confidence(signals) <= 1.0",
        "priority": "HIGH",
        "hypothesis_example": "code snippet"
      }
    ],
    "library": "hypothesis",
    "skip_pbt": false,
    "reason": "PBT recommended — confidence arithmetic has bounded output property"
  },
  "confidence": 0.90,
  "flags": [],
  "trust_tier": "T1"
}
```