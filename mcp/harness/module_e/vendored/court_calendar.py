"""Multi-jurisdiction court calendar for Iron Fleet.

Provides working-day arithmetic that respects public holidays for NZ (default),
AU, and UK jurisdictions.  Holiday data is loaded from per-jurisdiction JSON
files via the ``JurisdictionLoader``.

Key functions
-------------
- :func:`is_working_day` -- check if a date is a business day.
- :func:`add_working_days` -- advance by *n* working days.
- :func:`court_filing_deadline` -- compute a court/statutory deadline.
- :func:`get_holidays` -- list holidays for a year.
- :func:`list_regions` -- list available sub-national regions.
"""

from __future__ import annotations

import json
from datetime import date, timedelta
from functools import lru_cache
from pathlib import Path
from typing import Any

from .jurisdiction_loader import JurisdictionLoader

_PROJECT_ROOT = Path(__file__).resolve().parent / "data"

# Years covered by the shipped holiday data.
_MIN_YEAR = 2024
_MAX_YEAR = 2030


# -- Holiday data access ------------------------------------------------------


@lru_cache(maxsize=16)
def _load_holidays_raw(jurisdiction: str = "nz") -> dict[str, Any]:
    """Read and cache the JSON holiday file for *jurisdiction*."""
    cfg = JurisdictionLoader.load(jurisdiction)
    path = _PROJECT_ROOT / cfg.holidays_file
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


@lru_cache(maxsize=256)
def _holidays_for(
    year: int,
    region: str | None = None,
    jurisdiction: str = "nz",
) -> frozenset[date]:
    """Return the set of holiday dates for *year* (and optional *region*)."""
    data = _load_holidays_raw(jurisdiction)
    dates: set[date] = set()

    # National holidays
    for entry in data.get("national", {}).get(str(year), []):
        dates.add(date.fromisoformat(entry["date"]))

    # Regional holidays
    if region:
        key = region.strip().lower()
        for entry in data.get("regional", {}).get(key, {}).get(str(year), []):
            dates.add(date.fromisoformat(entry["date"]))

    return frozenset(dates)


def get_holidays(
    year: int,
    region: str | None = None,
    jurisdiction: str = "nz",
) -> list[dict[str, str]]:
    """Return holiday records for *year* in *jurisdiction*.

    Includes national holidays plus the regional holidays if *region* is
    given.  Returns an empty list for years outside 2024-2030.
    """
    data = _load_holidays_raw(jurisdiction)
    results: list[dict[str, str]] = []

    for entry in data.get("national", {}).get(str(year), []):
        results.append({"date": entry["date"], "name": entry["name"]})

    if region:
        key = region.strip().lower()
        region_data = data.get("regional", {}).get(key, {})
        for entry in region_data.get(str(year), []):
            results.append({"date": entry["date"], "name": entry["name"]})

    return results


def list_regions(jurisdiction: str = "nz") -> list[str]:
    """Return the region keys available in the holiday data."""
    data = _load_holidays_raw(jurisdiction)
    return sorted(data.get("regional", {}).keys())


# -- Working-day logic ---------------------------------------------------------


def is_working_day(
    d: date,
    region: str | None = None,
    jurisdiction: str = "nz",
) -> bool:
    """Return ``True`` if *d* is a business day in *jurisdiction*.

    A date is a working day if it is Monday-Friday **and** not a national
    or regional public holiday.

    For years outside 2024-2030 only weekends are excluded (no holiday
    data available).
    """
    if d.weekday() >= 5:  # Saturday = 5, Sunday = 6
        return False
    return d not in _holidays_for(d.year, region, jurisdiction)


def add_working_days(
    start: date,
    days: int,
    region: str | None = None,
    jurisdiction: str = "nz",
) -> date:
    """Return the date that is *days* working days after *start*.

    The *start* date itself is **not** counted.  Each step forward skips
    weekends and public holidays.

    Parameters
    ----------
    start:
        Reference date (not counted).
    days:
        Number of working days to advance.  Must be >= 0.
    region:
        Optional sub-national region for regional holidays
        (e.g. ``"auckland"`` for NZ, ``"nsw"`` for AU, ``"scotland"`` for UK).
    jurisdiction:
        Jurisdiction code (default ``"nz"``).

    Raises
    ------
    ValueError
        If *days* is negative.
    """
    if days < 0:
        raise ValueError("days must be non-negative")

    current = start
    remaining = days
    while remaining > 0:
        current += timedelta(days=1)
        if is_working_day(current, region, jurisdiction):
            remaining -= 1
    return current


def court_filing_deadline(
    service_date: date,
    days: int,
    region: str | None = None,
    jurisdiction: str = "nz",
) -> date:
    """Compute a court / statutory filing deadline.

    The day of service is **excluded** and only working days
    (Monday-Friday, excluding public holidays) are counted.

    Parameters
    ----------
    service_date:
        Date on which the document was served (excluded from the count).
    days:
        Number of working days in the statutory period.
    region:
        Optional sub-national region for regional holidays.
    jurisdiction:
        Jurisdiction code (default ``"nz"``).
    """
    if days <= 0:
        raise ValueError("Statutory period must be at least 1 working day")
    return add_working_days(service_date, days, region, jurisdiction)
