# tests/test_jurisdictions.py — W1 round-trip: every declared jurisdiction
# loads from the law pack and its statute references survive the trip
# (JSON -> JurisdictionConfig -> kernel output). Run with `-s` to print
# each jurisdiction's statute refs.
import json
import sys
from pathlib import Path

PLUGIN = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PLUGIN / "mcp"))

from harness.module_e.vendored.companies_act import validate_statutory_demand   # noqa: E402
from harness.module_e.vendored.jurisdiction_loader import JurisdictionLoader    # noqa: E402
from harness.module_e.vendored.without_prejudice_detector import run as wp_run  # noqa: E402

_PACK_DIR = (PLUGIN / "mcp" / "harness" / "module_e" / "vendored" / "data"
             / "config" / "jurisdictions")


def test_roundtrip_all_declared_jurisdictions_load():
    for code in JurisdictionLoader.list_jurisdictions():
        raw = json.loads((_PACK_DIR / f"{code}.json").read_text(encoding="utf-8"))
        cfg = JurisdictionLoader.load(code)
        assert cfg.code == code == raw["code"]
        refs = {
            "interest": cfg.interest_statute_ref,
            "statutory_demand": cfg.statutory_demand_statute_ref,
            "statutory_demand_compliance": cfg.statutory_demand_compliance_statute_ref,
            "penalty": cfg.penalty_statute_ref,
            "solvency": cfg.solvency_statute_ref,
            "security_interest": cfg.security_interest_statute_ref,
            "without_prejudice": cfg.without_prejudice_statute_ref,
        }
        for name, ref in refs.items():
            assert ref.strip(), f"{code}.{name}: empty statute ref"
        print(f"\n{cfg.code} ({cfg.name}, {cfg.currency}):")
        for name, ref in refs.items():
            print(f"  {name}: {ref}")


def test_nz_kernel_reads_pack_not_hardcoded_strings():
    cfg = JurisdictionLoader.load("nz")
    got = validate_statutory_demand(5000, "Debtor Ltd", "Creditor Ltd",
                                    "unpaid invoices")
    assert got["is_valid"]
    assert got["statute_ref"] == cfg.statutory_demand_statute_ref
    assert got["compliance_statute_ref"] == cfg.statutory_demand_compliance_statute_ref
    # the 15-working-day minimum and $1,000 floor live in nz.json now
    assert got["compliance_period_days"] == cfg.compliance_period_days == 15
    assert got["compliance_period_day_type"] == "working"
    assert got["compliance_statute_ref"] == "Companies Act 1993 s 289(2)(d)"


def test_au_uk_compliance_periods_are_calendar_days():
    """2026-11-03 ruling: au/uk compliance periods are CALENDAR days by statute
    (Corporations Act 2001 s 459F: 21 days after service; UK: three weeks, IA 1986
    s 123(1)(a)) — the working-day calendar overstated them ~8 days."""
    for code in ("au", "uk"):
        got = validate_statutory_demand(
            JurisdictionLoader.load(code).statutory_demand_minimum,
            "Debtor Ltd", "Creditor Ltd", "unpaid invoices",
            service_date="2026-03-02", jurisdiction=code)     # a Monday
        assert got["is_valid"]
        assert got["compliance_period_day_type"] == "calendar"
        assert got["compliance_period_days"] == 21
        # 21 plain days from Mon 2 Mar — weekends and holidays NOT skipped
        assert got["compliance_deadline"] == "2026-03-23"


def test_nz_compliance_stays_working_days():
    got = validate_statutory_demand(5000, "Debtor Ltd", "Creditor Ltd",
                                    "unpaid invoices", service_date="2026-03-02")
    assert got["compliance_period_day_type"] == "working"
    from datetime import date
    from harness.module_e.vendored.court_calendar import add_working_days
    assert got["compliance_deadline"] == add_working_days(
        date(2026, 3, 2), 15, None, "nz").isoformat()


def test_wp_reasoning_carries_jurisdiction_pack_ref():
    letter = "WITHOUT PREJUDICE\n\nWe offer fifty thousand dollars in full and final settlement."
    au = wp_run({"content": letter, "trust_tier": "T1", "jurisdiction": "au"})
    assert au["status"] == "SUCCESS"
    au_ref = JurisdictionLoader.load("au").without_prejudice_statute_ref
    assert au_ref in au["result"]["reasoning_chain"]
    nz = wp_run({"content": letter, "trust_tier": "T1"})      # default stays nz
    nz_ref = JurisdictionLoader.load("nz").without_prejudice_statute_ref
    assert nz_ref in nz["result"]["reasoning_chain"]
    assert nz_ref != au_ref


def test_nz_working_days_skip_companies_act_christmas_closure():
    """CA 1993 s 2 "working day" (b)-(d). Dates from run 20261104-6174c7: the
    s 288(1) 30-working-day window had come out 3 days early (22 Jan, 9 Feb)."""
    from datetime import date
    from harness.module_e.vendored.court_calendar import add_working_days, is_working_day
    assert add_working_days(date(2026, 12, 7), 30) == date(2027, 1, 27)
    assert add_working_days(date(2026, 12, 22), 30) == date(2027, 2, 12)
    assert not is_working_day(date(2026, 12, 29))                        # (b)
    assert not is_working_day(date(2027, 1, 4))                          # (c) 1 Jan a Friday
    assert not is_working_day(date(2028, 1, 4))                          # (d) 1 Jan a Saturday
    assert is_working_day(date(2028, 1, 5))
    assert is_working_day(date(2026, 12, 29), jurisdiction="au")         # NZ-only rule
