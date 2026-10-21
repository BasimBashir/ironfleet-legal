"""Jurisdiction-specific legal rule loader for Iron Fleet.

Reads per-jurisdiction JSON config files from ``config/jurisdictions/``
and provides typed access to legal parameters (interest rates, limitation
periods, statutory demand rules, etc.).

Default jurisdiction is ``"nz"`` for full backward compatibility.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from decimal import Decimal
from functools import lru_cache
from pathlib import Path
from typing import Any

_CONFIG_DIR = Path(__file__).resolve().parent / "data" / "config" / "jurisdictions"


@dataclass(frozen=True)
class JurisdictionConfig:
    """Immutable jurisdiction configuration loaded from JSON."""

    code: str
    name: str
    currency: str
    interest_rate: Decimal
    day_count_convention: str
    interest_statute_ref: str
    limitation_periods: dict[str, int]
    statutory_demand_minimum: Decimal
    compliance_period_working_days: int
    statutory_demand_statute_ref: str
    penalty_ratio_thresholds: dict[str, Decimal]
    penalty_statute_ref: str
    solvency_warning_threshold: Decimal
    solvency_critical_threshold: Decimal
    solvency_statute_ref: str
    valid_collateral_types: frozenset[str]
    security_interest_statute_ref: str
    holidays_file: str


class JurisdictionLoader:
    """Load jurisdiction-specific legal rules from config files."""

    _DEFAULT = "nz"
    _CONFIG_DIR = _CONFIG_DIR

    @classmethod
    @lru_cache(maxsize=16)
    def load(cls, jurisdiction: str = "nz") -> JurisdictionConfig:
        """Load and cache a jurisdiction config.

        Parameters
        ----------
        jurisdiction:
            Two-letter jurisdiction code (e.g. ``"nz"``, ``"au"``, ``"uk"``).

        Returns
        -------
        JurisdictionConfig
            Immutable config dataclass.

        Raises
        ------
        ValueError
            If the jurisdiction code is unknown (no matching JSON file).
        """
        code = jurisdiction.strip().lower()
        path = cls._CONFIG_DIR / f"{code}.json"
        if not path.exists():
            available = cls.list_jurisdictions()
            raise ValueError(
                f"Unknown jurisdiction {jurisdiction!r}. "
                f"Available: {', '.join(available)}"
            )

        with open(path, encoding="utf-8") as fh:
            raw: dict[str, Any] = json.load(fh)

        return _parse_config(raw)

    @classmethod
    def list_jurisdictions(cls) -> list[str]:
        """Return sorted list of available jurisdiction codes."""
        return sorted(
            p.stem
            for p in cls._CONFIG_DIR.glob("*.json")
            if not p.stem.endswith("_holidays")
        )

    @classmethod
    def get_interest_rate(cls, jurisdiction: str = "nz") -> Decimal:
        """Return the prescribed interest rate for *jurisdiction*."""
        return cls.load(jurisdiction).interest_rate

    @classmethod
    def get_limitation_periods(cls, jurisdiction: str = "nz") -> dict[str, int]:
        """Return limitation periods dict for *jurisdiction*."""
        return cls.load(jurisdiction).limitation_periods

    @classmethod
    def get_statutory_demand_rules(cls, jurisdiction: str = "nz") -> dict[str, Any]:
        """Return statutory demand rules for *jurisdiction*."""
        cfg = cls.load(jurisdiction)
        return {
            "prescribed_minimum": cfg.statutory_demand_minimum,
            "compliance_period_working_days": cfg.compliance_period_working_days,
            "statute_ref": cfg.statutory_demand_statute_ref,
        }

    @classmethod
    def get_penalty_thresholds(cls, jurisdiction: str = "nz") -> dict[str, Decimal]:
        """Return penalty clause ratio thresholds for *jurisdiction*."""
        return cls.load(jurisdiction).penalty_ratio_thresholds

    @classmethod
    def get_solvency_thresholds(cls, jurisdiction: str = "nz") -> dict[str, Decimal]:
        """Return solvency assessment thresholds for *jurisdiction*."""
        cfg = cls.load(jurisdiction)
        return {
            "warning": cfg.solvency_warning_threshold,
            "critical": cfg.solvency_critical_threshold,
        }

    @classmethod
    def get_collateral_types(cls, jurisdiction: str = "nz") -> frozenset[str]:
        """Return valid collateral types for *jurisdiction*."""
        return cls.load(jurisdiction).valid_collateral_types


def _parse_config(raw: dict[str, Any]) -> JurisdictionConfig:
    """Parse a raw JSON dict into a JurisdictionConfig."""
    interest = raw["interest"]
    lim = raw["limitation_periods"]
    sd = raw["statutory_demand"]
    pen = raw["penalty_clause"]
    sol = raw["solvency"]
    sec = raw["security_interest"]

    return JurisdictionConfig(
        code=raw["code"],
        name=raw["name"],
        currency=raw["currency"],
        interest_rate=Decimal(interest["prescribed_rate"]),
        day_count_convention=interest["day_count_convention"],
        interest_statute_ref=interest["statute_ref"],
        limitation_periods=dict(lim),
        statutory_demand_minimum=Decimal(sd["prescribed_minimum"]),
        compliance_period_working_days=int(sd["compliance_period_working_days"]),
        statutory_demand_statute_ref=sd["statute_ref"],
        penalty_ratio_thresholds={
            k: Decimal(v) for k, v in pen["ratio_thresholds"].items()
        },
        penalty_statute_ref=pen["statute_ref"],
        solvency_warning_threshold=Decimal(sol["warning_threshold"]),
        solvency_critical_threshold=Decimal(sol["critical_threshold"]),
        solvency_statute_ref=sol["statute_ref"],
        valid_collateral_types=frozenset(sec["valid_collateral_types"]),
        security_interest_statute_ref=sec["statute_ref"],
        holidays_file=raw["holidays_file"],
    )
