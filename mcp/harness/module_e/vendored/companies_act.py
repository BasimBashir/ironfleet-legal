"""Companies Act 1993 (NZ) kernel — statutory demand validation.

Validates a statutory demand under s 289 of the Companies Act 1993 and
computes the compliance deadline per s 241(4)(a).

Requirements:
- Debt must be due and owing
- Amount must meet the prescribed minimum (NZD 1,000)
- Demand must identify creditor, debtor company, and debt particulars
- Company has at least 15 working days to comply after service

Iron Logic: all amounts use exact ``Decimal`` arithmetic; deadlines are
computed via the NZ working-day calendar.
"""

from __future__ import annotations

from datetime import date
from decimal import ROUND_HALF_UP, Decimal
from typing import Any

from .nz_calendar import add_working_days

# Prescribed minimum debt for a statutory demand (s 241(4)(a)).
PRESCRIBED_MINIMUM = Decimal("1000.00")

# Minimum compliance period in working days (s 241(4)(a)).
DEFAULT_COMPLIANCE_PERIOD = 15

_TWO_DP = Decimal("0.01")


def validate_statutory_demand(
    amount: float | int | str | Decimal,
    debtor_company: str,
    creditor: str,
    debt_details: str,
    service_date: date | str | None = None,
    compliance_period: int | None = None,
    region: str | None = None,
    jurisdiction: str = "nz",
) -> dict[str, Any]:
    """Validate a statutory demand under Companies Act 1993 s 289.

    Parameters
    ----------
    amount:
        The debt amount claimed.  Must be >= prescribed minimum ($1,000).
    debtor_company:
        Name of the debtor company.
    creditor:
        Name of the creditor.
    debt_details:
        Description of the debt (nature, basis, particulars).
    service_date:
        Date the demand was / will be served.  Defaults to today.
    compliance_period:
        Working days for the company to comply (default 15, the
        statutory minimum per s 241(4)(a)).
    region:
        NZ region for regional holidays in deadline calculation.

    Returns
    -------
    dict
        ``is_valid``, ``issues``, ``amount``, ``debtor_company``,
        ``creditor``, ``compliance_deadline``,
        ``compliance_period_working_days``, ``service_date``.
    """
    issues: list[str] = []

    # ── Load jurisdiction-specific rules ────────────────────
    if jurisdiction != "nz":
        from .jurisdiction_loader import JurisdictionLoader
        rules = JurisdictionLoader.get_statutory_demand_rules(jurisdiction)
        prescribed_min = rules["prescribed_minimum"]
        default_period = rules["compliance_period_working_days"]
    else:
        prescribed_min = PRESCRIBED_MINIMUM
        default_period = DEFAULT_COMPLIANCE_PERIOD

    if compliance_period is None:
        compliance_period = default_period

    # ── Validate amount ───────────────────────────────────
    amount_d = _to_decimal(amount, "amount")
    if amount_d < 0:
        issues.append("Amount must be non-negative")
    elif amount_d < prescribed_min:
        issues.append(
            f"Amount ${amount_d} is below the prescribed minimum of "
            f"${prescribed_min}"
        )

    # ── Validate required fields ──────────────────────────
    _PLACEHOLDER_NAMES = {"unknown creditor", "unknown debtor", "unknown"}
    if not debtor_company or not debtor_company.strip():
        issues.append("Debtor company name is required")
    elif debtor_company.strip().lower() in _PLACEHOLDER_NAMES:
        issues.append(
            "Debtor company name is a placeholder — a valid company name "
            "is required for a s 289 demand to be enforceable"
        )
    if not creditor or not creditor.strip():
        issues.append("Creditor name is required")
    elif creditor.strip().lower() in _PLACEHOLDER_NAMES:
        issues.append(
            "Creditor name is a placeholder — the actual creditor must be "
            "identified for a s 289 demand to be enforceable"
        )
    if not debt_details or not debt_details.strip():
        issues.append("Debt details/particulars are required")

    # ── Validate compliance period ────────────────────────
    if compliance_period < default_period:
        issues.append(
            f"Compliance period ({compliance_period} working days) is below "
            f"the statutory minimum of {default_period} working days"
        )

    # ── Compute compliance deadline ───────────────────────
    from .court_calendar import add_working_days as _add_wd
    svc = _to_date(service_date, "service_date") if service_date else date.today()
    deadline = _add_wd(svc, compliance_period, region, jurisdiction)

    return {
        "is_valid": len(issues) == 0,
        "issues": issues,
        "amount": float(amount_d.quantize(_TWO_DP, ROUND_HALF_UP)),
        "debtor_company": (debtor_company or "").strip(),
        "creditor": (creditor or "").strip(),
        "compliance_deadline": deadline.isoformat(),
        "compliance_period_working_days": compliance_period,
        "service_date": svc.isoformat(),
    }


# ── Internal helpers ──────────────────────────────────────


def _to_decimal(value: float | int | str | Decimal, name: str) -> Decimal:
    try:
        return Decimal(str(value))
    except Exception as exc:
        raise TypeError(
            f"{name} must be a number, got {type(value).__name__}"
        ) from exc


def _to_date(value: date | str, name: str) -> date:
    if isinstance(value, date):
        return value
    try:
        return date.fromisoformat(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(
            f"{name} must be a date or ISO-8601 string, got {value!r}"
        ) from exc
