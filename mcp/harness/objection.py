# mcp/harness/objection.py — G5 (ROADMAP-0.2.0): the adversary's failure modes
# as a tool. Mechanical, offline, re-runnable — it runs BEFORE advice is drafted, not
# after: (a) a cited authority not in corpus, (b) a quoted span not in corpus, (c) a
# date/period not matching the kernel's computation for this matter, (d) a statutory
# demand drafted but never kernel-computed (found live 2026-10-26, SL test). (a)+(b)
# reuse G1's verify_document core byte-for-byte; (c) reads the kernel computations
# stage 6 already logs as tool_result events — zero new storage.
# When the run logs an evidence table (log_event event `evidence`, payload
# `{table: {"[E1.S1]": "<verbatim sentence>"}}`), every [E.n.S.n] ref is PINNED to
# its sentence: a ref whose draft quote differs from its pinned sentence is finally a
# MISMATCH (the verdict G1 deferred lands here), and a ref with no quote at all
# verifies through its pinned, corpus-grounded sentence.
"""shortcut: dates are matched as whole calendar days in deadline-context lines only —
a date the draft states outside deadline language is a fact, not an assertion to check.
Upgrade to per-sentence attribution when a drafting stage emits structured dates."""
from __future__ import annotations

import bisect
import json
import re
from pathlib import Path

from harness.corpus import _REF_TOKEN
from harness.paths import resolve_store_root
from harness.verify import (MIN_QUOTE_WORDS, _QUOTE, _locate, _norm, load_chunks,
                            verify_document)

_KERNEL_TOOLS = {"ironfleet_filing_deadline": ("deadline", "days"),
                 "ironfleet_statutory_demand": ("compliance_deadline",
                                                "compliance_period_days")}
_CTX = re.compile(r"(?i)deadline|complian|no later than|working days")
_CTX_STRICT = re.compile(r"(?i)deadline|compl")        # for periods: _PERIOD already
                                                       # guarantees a days phrase
_PERIOD = re.compile(r"(?i)within (\d+) (?:working )?days?")
_MONTHS = {m: i for i, m in enumerate(
    ("jan feb mar apr may jun jul aug sep oct nov dec").split(), 1)}
_PROSE_DATE = re.compile(
    r"\b(\d{1,2})(?:st|nd|rd|th)?\s+(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)"
    r"[a-z]*\s+(\d{4})\b", re.I)
_SLASH_DATE = re.compile(r"\b(\d{1,2})/(\d{1,2})/(\d{4})\b")   # NZ day-first
_ISO_DATE = re.compile(r"\b(\d{4}-\d{2}-\d{2})\b")


def _store_path(store: object | None) -> Path:
    if store is not None:
        return Path(store.db_path)
    root, _source = resolve_store_root()
    return Path(root) / "corpus.sqlite3"


def _trace(run_id: str | None, matter: str, workspace: str | None):
    """(events, evidence table) from the run ledger; ([], {}) without a run — the
    tool must also work on any draft nobody ran a pipeline over."""
    if not run_id:
        return [], {}
    try:
        import records
        d = records._resolve(run_id, matter, workspace)
        events = [json.loads(l) for l in
                  (d / "trace.jsonl").read_text(encoding="utf-8").splitlines() if l.strip()]
    except Exception:                                  # noqa: BLE001 — no ledger, still object
        return [], {}
    table: dict[str, str] = {}
    for e in events:
        if e.get("event") == "evidence" and isinstance(e.get("table"), dict):
            table.update({str(k): _norm(str(v)) for k, v in e["table"].items()})
    return events, table


def _kernel_computations(events: list[dict]) -> list[dict]:
    """The kernel computations the run logged (stage 6's flat tool_result payloads)."""
    comps = []
    for e in events:
        if e.get("event") != "tool_result" or e.get("tool") not in _KERNEL_TOOLS:
            continue
        dkey, pkey = _KERNEL_TOOLS[e["tool"]]
        if e.get(dkey):
            comps.append({"tool": e["tool"], "deadline": str(e[dkey]),
                          "days": e.get(pkey), "service": e.get("service_date")})
    return comps


def _dates(text: str) -> dict[str, int]:
    """Every date the draft states -> ISO, mapped to its first offset. A date stated
    twice counts once (first occurrence wins the context check)."""
    out: dict[str, int] = {}
    for m in _ISO_DATE.finditer(text):
        out.setdefault(m.group(1), m.start())
    for m in _PROSE_DATE.finditer(text):
        out.setdefault(f"{m.group(3)}-{_MONTHS[m.group(2).lower()]:02d}-"
                       f"{int(m.group(1)):02d}", m.start())
    for m in _SLASH_DATE.finditer(text):
        out.setdefault(f"{m.group(3)}-{int(m.group(2)):02d}-{int(m.group(1)):02d}",
                       m.start())
    return out


def _pin(evidence: dict[str, str], chunks: list[dict], text: str,
         refs: list[dict]) -> None:
    """Upgrade ref verdicts in place from borrowed (nearest preceding quote) to pinned
    (the run's own evidence table). A table sentence nowhere in the corpus is loud;
    a draft quote that differs from its pinned sentence is the MISMATCH G1 deferred."""
    spans: list[str] = []
    ends: list[int] = []
    for m in _QUOTE.finditer(text):
        span = _norm(m.group(1))
        if len(span.split()) >= MIN_QUOTE_WORDS:
            spans.append(span)
            ends.append(m.end())
    for row, m in zip(refs, _REF_TOKEN.finditer(text)):
        pinned = evidence.get(row["ref"])
        if pinned is None:
            continue
        hit, quotable = _locate(chunks, pinned)
        if hit is None:
            row.update(verdict="NOT_IN_CORPUS", found_in=None,
                       pinned="the evidence table's sentence is nowhere in this corpus")
            continue
        i = bisect.bisect_right(ends, m.start()) - 1
        owner = spans[i] if i >= 0 else None
        if owner is not None and owner != pinned:
            row.update(verdict="MISMATCH", found_in=hit["source_name"],
                       pinned=f'the draft quotes "{owner[:80]}" but the evidence table '
                              f'pins "{pinned[:80]}"')
        else:
            row.update(verdict="VERIFIED", found_in=hit["source_name"], pinned=True)


def objection(matter: str, path: str, run_id: str | None = None,
              workspace: str | None = None, store: object | None = None) -> dict:
    """The adversary's three failure modes over one draft. Never raises; ok=false
    means objections stand (the gate stays verify_document's — objections are the
    mechanical attack the agent must fix or answer in prose)."""
    out = {"matter": matter, "path": str(path), "objections": [], "ok": True,
           "kernel": {"computations": 0, "deadlines_matched": 0}}
    v = verify_document(matter, path, store=store)
    out["corpus_chunks"] = v.get("corpus_chunks", 0)
    if v.get("error"):
        out["ok"] = False
        out["error"] = v["error"]
        return out

    f = Path(path)
    sp = _store_path(store)
    if store is not None and not f.is_absolute():
        f = sp.parent / f
    try:
        text = f.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as ex:
        out["ok"] = False
        out["error"] = f"deliverable not readable: {ex}"
        return out

    events, evidence = _trace(run_id, matter, workspace)
    chunks = load_chunks(matter, sp)
    if evidence:
        _pin(evidence, chunks, text, v["refs"])

    # (a) + (b): every ungrounded verify row is an objection
    for q in v["quotes"]:
        if q["verdict"] != "VERIFIED":
            out["objections"].append({"kind": "quote_not_in_corpus",
                                      "verdict": q["verdict"],
                                      "quote": q["quote"][:120], "line": q["line"]})
    for row in v["refs"]:
        if row["verdict"] != "VERIFIED":
            out["objections"].append({"kind": "authority_not_in_corpus",
                                      "verdict": row["verdict"], "ref": row["ref"],
                                      "found_in": row.get("found_in"),
                                      "line": row["line"], "note": row.get("pinned")})

    # (c): dates/periods vs the kernel's computation for this matter
    comps = _kernel_computations(events)
    out["kernel"]["computations"] = len(comps)
    if comps:
        dates = _dates(text)
        want = {c["deadline"] for c in comps}
        served = {str(c["service"]) for c in comps if c.get("service")}
        # a draft that never speaks of deadlines (an attack brief) cannot omit one;
        # a deadline-speaking draft (advice letter, filings roadmap) must state the
        # kernel's computation or it is stating something else in its place
        talks_deadlines = bool(_CTX.search(text))
        for c in comps:
            if c["deadline"] in dates:
                out["kernel"]["deadlines_matched"] += 1
            elif talks_deadlines:
                out["objections"].append({
                    "kind": "date_not_matching_kernel",
                    "detail": f"{c['tool']} computed deadline {c['deadline']}"
                              + (f" ({c['days']} days from service "
                                 f"{c['service']})" if c.get("service") else "")
                              + " but the draft never states it"})
        starts = [0] + [mm.end() for mm in re.finditer(r"\n", text)]
        lines = text.splitlines()
        for iso, off in dates.items():
            if iso in want or iso in served:
                continue
            ln = bisect.bisect_right(starts, off)
            if ln <= len(lines) and _CTX.search(lines[ln - 1]):
                out["objections"].append({
                    "kind": "date_not_matching_kernel", "line": ln,
                    "detail": f"the draft asserts {iso} in a deadline context; no "
                              f"kernel computation logged for this run produced it"})
        periods = {str(c["days"]) for c in comps if c.get("days")}
        if periods:
            for m in _PERIOD.finditer(text):
                ln = bisect.bisect_right(starts, m.start())
                if (ln <= len(lines) and _CTX_STRICT.search(lines[ln - 1])
                        and m.group(1) not in periods):
                    out["objections"].append({
                        "kind": "date_not_matching_kernel", "line": ln,
                        "detail": f"the draft states \"{m.group(0)}\"; the kernel "
                                  f"computed {sorted(periods)} days for this matter"})
    else:
        out["kernel"]["note"] = ("no kernel computations logged in this run (stage 6 "
                                 "logs them as tool_result events)" if run_id
                                 else "no run_id — kernel checks skipped")

    # (d): a draft that raises a statutory demand must have run the kernel — found
    # live 2026-10-26: the stage-6 instruction alone was obeyed by one model and
    # skipped by another (which then flagged the kernel's own $1,000 minimum as
    # [NOT IN CORPUS]). Instruction-following is nondeterministic; this is not.
    if run_id and re.search(r"(?i)statutory demand", text) and \
            not any(c["tool"] == "ironfleet_statutory_demand" for c in comps):
        out["objections"].append({
            "kind": "statutory_demand_not_computed",
            "detail": "the draft raises a statutory demand but this run logged no "
                      "ironfleet_statutory_demand computation — run the kernel "
                      "(amount vs the $1,000 minimum; the compliance deadline) and "
                      "state its result, or rule the exception via log_event"})

    out["refs"] = v["refs"]
    out["quotes"] = v["quotes"]
    out["verify_summary"] = v["summary"]
    out["summary"] = {k: sum(1 for o in out["objections"] if o["kind"] == k)
                      for k in ("authority_not_in_corpus", "quote_not_in_corpus",
                                "date_not_matching_kernel",
                                "statutory_demand_not_computed")}
    out["ok"] = not out["objections"]
    if not out["ok"]:
        out["remedy"] = ("fix each objection in the draft or answer it in the "
                         "adversary's prose; a ruled exception is logged via "
                         "ironfleet_log_event (event `exception`) naming ref, quote "
                         "and ruling")
    return out
