"""NZ-specific date calculation utilities for Iron Fleet.

This module is a backward-compatible wrapper around
:mod:`helpers.court_calendar`.  All functions delegate to the
multi-jurisdiction calendar with ``jurisdiction="nz"``.

Existing imports like ``from helpers.nz_calendar import add_working_days``
continue to work unchanged.
"""

from __future__ import annotations

from datetime import date
from typing import Any

from .court_calendar import (
    add_working_days as _add_working_days,
    court_filing_deadline as _court_filing_deadline,
    get_holidays as _get_holidays,
    is_working_day as _is_working_day,
    list_regions as _list_regions,
)


def is_working_day(d: date, region: str | None = None) -> bool:
    """Return ``True`` if *d* is a NZ business day."""
    return _is_working_day(d, region, jurisdiction="nz")


def add_working_days(
    start: date,
    days: int,
    region: str | None = None,
) -> date:
    """Return the date that is *days* NZ working days after *start*."""
    return _add_working_days(start, days, region, jurisdiction="nz")


def court_filing_deadline(
    service_date: date,
    days: int,
    region: str | None = None,
) -> date:
    """Compute a NZ court / statutory filing deadline."""
    return _court_filing_deadline(service_date, days, region, jurisdiction="nz")


def get_holidays(
    year: int,
    region: str | None = None,
) -> list[dict[str, str]]:
    """Return NZ holiday records for *year*."""
    return _get_holidays(year, region, jurisdiction="nz")


def list_regions() -> list[str]:
    """Return available NZ region keys."""
    return _list_regions(jurisdiction="nz")
