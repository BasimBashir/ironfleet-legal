"""Statutory demand kernel — parameters from the jurisdiction pack.

Validates a statutory demand and computes the compliance deadline. Every
statutory parameter (prescribed minimum, compliance period, statute
references) loads from the jurisdiction pack via JurisdictionLoader — the
kernel owns no statute strings of its own. NZ pack: Companies Act 1993
s 289 (demand; prescribed amount s 289(2)(a), 15 working days s 289(2)(d)).

Requirements:
- Debt must be due and owing
- Amount must meet the jurisdiction's prescribed minimum
- Demand must identify creditor, debtor company, and debt particulars
- Company has at least the pack's compliance period after service (day type per
  the pack: NZ working days, au/uk calendar days — 2026-11-03 ruling)

Iron Logic: all amounts use exact ``Decimal`` arithmetic; deadlines are
computed via the pack's day type — the working-day calendar for nz, plain
calendar days for au/uk.
"""

from __future__ import annotations

from datetime import date, timedelta
from decimal import ROUND_HALF_UP, Decimal
from typing import Any

from .jurisdiction_loader import JurisdictionLoader

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
    """Validate a statutory demand under the jurisdiction pack's
    statutory_demand rules (NZ: Companies Act 1993 s 289).

    Parameters
    ----------
    amount:
        The debt amount claimed.  Must be >= the jurisdiction's prescribed
        minimum.
    debtor_company:
        Name of the debtor company.
    creditor:
        Name of the creditor.
    debt_details:
        Description of the debt (nature, basis, particulars).
    service_date:
        Date the demand was / will be served.  Defaults to today.
    compliance_period:
        Days for the company to comply (default: the jurisdiction pack's
        compliance_period_days; day type per the pack).
    region:
        Region for regional holidays in deadline calculation.
    jurisdiction:
        Two-letter jurisdiction pack code (default ``"nz"``).

    Returns
    -------
    dict
        ``is_valid``, ``issues``, ``amount``, ``debtor_company``,
        ``creditor``, ``compliance_deadline``,
        ``compliance_period_days``, ``compliance_period_day_type``,
        ``service_date``, ``statute_ref``, ``compliance_statute_ref``.
    """
    issues: list[str] = []

    # ── Load jurisdiction-specific rules ────────────────────
    rules = JurisdictionLoader.get_statutory_demand_rules(jurisdiction)
    prescribed_min = rules["prescribed_minimum"]
    default_period = rules["compliance_period_days"]
    day_type = rules["compliance_period_day_type"]
    if day_type not in ("working", "calendar"):
        raise ValueError(f"pack {jurisdiction!r}: unknown compliance_period_day_type "
                         f"{day_type!r} — must be 'working' or 'calendar'")
    unit = "calendar days" if day_type == "calendar" else "working days"

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
            f"is required for the demand to be enforceable "
            f"({rules['statute_ref']})"
        )
    if not creditor or not creditor.strip():
        issues.append("Creditor name is required")
    elif creditor.strip().lower() in _PLACEHOLDER_NAMES:
        issues.append(
            "Creditor name is a placeholder — the actual creditor must be "
            f"identified for the demand to be enforceable "
            f"({rules['statute_ref']})"
        )
    if not debt_details or not debt_details.strip():
        issues.append("Debt details/particulars are required")

    # ── Validate compliance period ────────────────────────
    if compliance_period < default_period:
        issues.append(
            f"Compliance period ({compliance_period} {unit}) is below "
            f"the statutory minimum of {default_period} {unit}"
        )

    # ── Compute compliance deadline ───────────────────────
    from .court_calendar import add_working_days as _add_wd
    svc = _to_date(service_date, "service_date") if service_date else date.today()
    if day_type == "calendar":
        deadline = svc + timedelta(days=compliance_period)
    else:
        deadline = _add_wd(svc, compliance_period, region, jurisdiction)

    return {
        "is_valid": len(issues) == 0,
        "issues": issues,
        "amount": float(amount_d.quantize(_TWO_DP, ROUND_HALF_UP)),
        "debtor_company": (debtor_company or "").strip(),
        "creditor": (creditor or "").strip(),
        "compliance_deadline": deadline.isoformat(),
        "compliance_period_days": compliance_period,
        "compliance_period_day_type": day_type,
        "service_date": svc.isoformat(),
        "statute_ref": rules["statute_ref"],
        "compliance_statute_ref": rules["compliance_statute_ref"],
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
