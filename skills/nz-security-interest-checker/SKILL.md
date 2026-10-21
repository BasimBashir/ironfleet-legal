---
name: nz-security-interest-checker
description: 'Validates security interest registrations on the Personal Property Securities Register (PPSR) under the PLA 2007 / PPSA 1999 (NZ). Use when: Use when checking whether a PPSR registration is valid, verifying collateral types, checking registration expiry, or preparing for enforcement of a security interest.'
license: MIT
compatibility: Claude Code, Claude Desktop, Claude Cowork. Corpus tools need local Python 3.10+ and Ollama.
metadata:
  version: 1.0.0
  source_kernel: pla_2007.py
  function: validate_security_interest
  parameters:
    security_details:
      type: object
      required: true
      description: 'Dict with required keys: secured_party (str), debtor (str), collateral_type (str).  Optional: collateral_description, registration_date, expiry_date, registration_number, reference_date.

        '
  returns:
    is_valid:
      type: boolean
      description: Whether the registration meets all requirements.
    issues:
      type: array
      description: List of validation issues found.
    secured_party:
      type: string
      description: Secured party name.
    debtor:
      type: string
      description: Debtor name.
    collateral_type:
      type: string
      description: Normalised collateral type.
    collateral_description:
      type: string
      description: Free-text description (if provided).
    registration_number:
      type: string
      description: PPSR financing statement number (if provided).
    registration_date:
      type: string
      description: Registration date ISO-8601 (if provided).
    expiry_date:
      type: string
      description: Expiry date ISO-8601 (if provided).
    is_expired:
      type: boolean
      description: Whether registration has expired (null if no expiry_date).
    days_until_expiry:
      type: integer
      description: Days until expiry (null if no expiry_date).
  iron_logic: true
  mode: both
  permissions: []
  trust_tier_required: 0
---


# NZ Security Interest Checker

Validates security interest registrations on the **Personal Property Securities
Register (PPSR)** under the Property Law Act 2007 / Personal Property
Securities Act 1999.

## Key Requirements

- Identified secured party and debtor
- Valid collateral type / classification
- Registration must not have expired

## Valid Collateral Types

`accounts_receivable`, `all_present_and_after_acquired_property`,
`chattel_paper`, `consumer_goods`, `crops`, `documents_of_title`, `equipment`,
`intangibles`, `inventory`, `investment_securities`, `livestock`,
`motor_vehicle`, `negotiable_instruments`, `other_goods`

## Example

```python
result = execute_skill("nz-security-interest-checker", {
    "security_details": {
        "secured_party": "ANZ Bank",
        "debtor": "Acme Ltd",
        "collateral_type": "equipment",
        "registration_date": "2024-01-01",
        "expiry_date": "2029-01-01",
    }
})
# → {"is_valid": True, "is_expired": False, ...}
```
