# mcp/harness/moot_checks.py — M6's two NEW deterministic checks, pure: text in,
# flaw-shaped rows out. Exhibit refs vs the matter's evidence register (labels are
# passed in — this module stays corpus+kernel-owned law only, no store access);
# statutory-demand terms re-validated through the kernel (the kernel owns the law:
# prescribed minimum, compliance period). Everything else the moot gate checks is
# objection/citator's existing machinery — this module adds only the missing half.
# Boundary (doc 09): court forms WITHOUT a kernel are judgement-only until M9's
# jurisdiction packs.
from __future__ import annotations

import re

from .module_e.vendored import companies_act

# "Exhibit A", exhibit "B", [Exhibit 3] — one label per match; the label is capped
# at 1–3 chars ending on a non-word boundary so prose ("exhibits cited here",
# "exhibits listed below") is not taken for a label and convicted as missing
_EXHIBIT_REF = re.compile(r"(?i)\bexhibits?\s+[\"\[]?\s*([A-Za-z0-9]{1,3})(?![A-Za-z0-9])")
_SD_CONTEXT = re.compile(r"(?i)statutory demand")
_AMOUNT = re.compile(r"\$\s?([\d,]+(?:\.\d{1,2})?)")
_PERIOD = re.compile(r"(?i)within\s+(\d+)\s+(?:working\s+)?days?")

# kernel args for the term-less side of a validation — valid values, so ONLY the
# parsed term can invalidate (the kernel owns the minimums)
_NEUTRAL = {"debtor_company": "Debtor Company", "creditor": "Creditor",
            "debt_details": "parsed from the draft"}


def line_at(text: str, offset: int) -> int:
    """1-based line of an offset — the same convention verify/objection report."""
    return text.count("\n", 0, offset) + 1


def exhibit_rows(text: str, labels: set[str]) -> list[dict]:
    """Every exhibit ref must trace to a registered exhibit — fail-closed: a ref
    with no register row is a flaw (the exhibit never made it into the case). One
    row per missing label, first occurrence; a draft with no exhibit refs passes."""
    seen: set[str] = set()
    rows: list[dict] = []
    for m in _EXHIBIT_REF.finditer(text):
        ref = m.group(1).lower()
        if ref in labels or ref in seen:
            continue
        seen.add(ref)
        rows.append({"class": "missing_exhibit", "severity": "critical",
                     "detail": f'exhibit ref "{m.group(0)}" names no evidence-register '
                               f'exhibit (registered: {sorted(labels) or "none"})',
                     "line": line_at(text, m.start())})
    return rows


def form_rows(text: str) -> list[dict]:
    """Where a kernel owns the form, the kernel re-validates: every statutory-demand
    line's parsed amount/period goes through validate_statutory_demand; each kernel
    issue is a wrong_form flaw. Amounts outside demand context are facts, not forms.
    shortcut: terms are parsed from the SD-context line itself — a demand whose
    amount/period wrap to the next line is missed; upgrade to sentence-window
    parsing when a real corpus demands it."""
    rows: list[dict] = []
    for m in _SD_CONTEXT.finditer(text):
        nl = text.find("\n", m.start())
        line_text = text[m.start():nl if nl != -1 else len(text)]
        amt = _AMOUNT.search(line_text)
        per = _PERIOD.search(line_text)
        result = companies_act.validate_statutory_demand(
            amount=amt.group(1).replace(",", "") if amt else 1000,
            compliance_period=int(per.group(1)) if per else 15,
            **_NEUTRAL)
        for issue in result["issues"]:
            rows.append({"class": "wrong_form", "severity": "critical",
                         "detail": f"statutory-demand line re-validated by the "
                                   f"kernel ({result['statute_ref']}): {issue}",
                         "line": line_at(text, m.start())})
    return rows


def check(text: str, labels: set[str]) -> list[dict]:
    """The two checks together, in document order."""
    return sorted(exhibit_rows(text, labels) + form_rows(text),
                  key=lambda r: r["line"])
