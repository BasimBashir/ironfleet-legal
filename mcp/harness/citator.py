# mcp/harness/citator.py — W3 (ROADMAP-0.2.0): citator-lite over a law-judgments
# matter. Mechanical, offline, no LLM: the cites_<m> table the corpus already derives
# from chunk text (corpus._citation_keys) IS the citation graph — the query names an
# authority, the join lists the ingested judgments whose text cites it, each flagged
# later/same-or-earlier by its own neutral-citation year. Closes the "authority exists
# but is no longer good law" half of the Stanford finding: the tool SURFACES later
# citing judgments; whether one overruled or distinguished the authority is a human
# reading call, never a signal this module emits (a treatment citator is not W3).
"""Envelope (citing_judgments):
  ok          false only when the input names no citation span or the matter has no
              ingested corpus — an empty corpus can never clear an authority
  authority   {keys, year, in_corpus, doc_ids}
  citing      [{doc_id, source_name, year, later}]   later: True | False | None
  summary     {citing_docs, later, same_or_earlier, year_unknown}

`authority -> path` mode (citator): pass path=<deliverable> to check EVERY authority
the draft names (case keys + statute pins), one summary row per key, citing detail
only where citing_docs > 0. Informational by design: a later citing judgment does not
make a deliverable wrong, so ok stays true — the human reads the surfaced judgments.

Self-vs-citing: a doc whose FIRST chunk (heading, else heading+body when no heading
match exists) carries the authority's key is the authority's own doc — its chunks
carry their own name/pin — and never appears as citing. shortcut: a citing judgment
whose first chunk is heading-less AND names the authority in the same year as the
string, with the authority itself absent from the corpus, lands in the authority
bucket instead of citing — upgrade to an identity column stamped at ingest if a real
corpus ever trips on it. Name forms must match exactly (house rule: distinct
authorities never merge, so abbreviations never bridge — 'A-G' and
'Attorney-General' are different keys).
"""
from __future__ import annotations

import re
import sqlite3
from pathlib import Path

from harness.corpus import _citation_keys, _mtable
from harness.paths import resolve_store_root

# "[2020] NZSC 100" — the judgment's own header year. Bare years are never counted:
# a body may mention any year for any reason.
_NEUTRAL_YEAR = re.compile(r"\[(\d{4})\]")


def _doc_year(text: str) -> str | None:
    m = _NEUTRAL_YEAR.search(text)
    return m.group(1) if m else None


def _expand(keys: list[str]) -> list[str]:
    """A sentence-initial 'In X v Y ...' makes _CASE_SPAN swallow the leading 'In'
    into the stored join key ('case:in x v y'); a bare authority query keys the
    clean form. Adds the 'in' variant as an EXTRA candidate — the house rule never
    merges two distinct authorities' keys, and this adds one, never merges."""
    return keys + sorted({f"case:in {k[5:]}" for k in keys
                          if k.startswith("case:") and " v " in k[5:]
                          and not k.startswith("case:in ")})


def _authority(authority: str, keys: list, year=None, in_corpus=False,
               doc_ids=None) -> dict:
    return {"raw": authority, "keys": keys, "year": year,
            "in_corpus": in_corpus, "doc_ids": doc_ids or []}


def _fail(matter: str, authority: str, keys: list, error: str) -> dict:
    return {"matter": matter, "keys": keys, "ok": False, "error": error,
            "authority": _authority(authority, keys), "citing": [],
            "summary": {"citing_docs": 0, "later": 0, "same_or_earlier": 0,
                        "year_unknown": 0}}


def citing_judgments(matter_ref: str, authority: str, store=None) -> dict:
    """The cites join: which ingested judgments of this matter cite `authority`."""
    keys = sorted(_citation_keys(authority))
    if not matter_ref:
        return _fail(matter_ref, authority, keys, "no matter bound")
    if not keys:
        return _fail(matter_ref, authority, keys,
                     "no citation span recognised — name the judgment as "
                     "'X v Y [year] court no' or the provision as 'Act year, s N'")
    return _join(matter_ref, authority, _expand(keys), store)


def _join(matter_ref: str, authority: str, keys: list, store=None) -> dict:
    if store is not None:
        con = store._c()          # a fresh connection per call — closing it is safe
    else:
        root, _src = resolve_store_root()
        db = Path(root) / "corpus.sqlite3"
        if not db.exists():
            return _fail(matter_ref, authority, keys,
                         f"no corpus store at {db} — ingest the law corpus first")
        con = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
    try:
        try:
            if con.execute(f"SELECT COUNT(*) FROM {_mtable(matter_ref, 'docs')}"
                           ).fetchone()[0] == 0:
                return _fail(matter_ref, authority, keys,
                             f"no corpus ingested for matter {matter_ref!r} — an "
                             "empty corpus cannot clear an authority")
        except sqlite3.OperationalError:
            return _fail(matter_ref, authority, keys,
                         f"no corpus ingested for matter {matter_ref!r} — an "
                         "empty corpus cannot clear an authority")
        marks = ",".join("?" * len(keys))
        try:
            rows = con.execute(
                f"SELECT DISTINCT f.doc_id, d.source_name FROM "
                f"{_mtable(matter_ref, 'cites')} ci"
                f" JOIN {_mtable(matter_ref, 'fts')} f ON f.rowid = ci.fts_rowid"
                f" JOIN {_mtable(matter_ref, 'docs')} d ON d.doc_id = f.doc_id"
                f" WHERE ci.key IN ({marks})", tuple(keys)).fetchall()
        except sqlite3.OperationalError:
            return _fail(matter_ref, authority, keys,
                         "matter ingested before the citation-index amendment — "
                         "re-index it (CorpusStore.reindex_cites) first")
        first = {d: con.execute(
            f"SELECT heading, body FROM {_mtable(matter_ref, 'fts')}"
            f" WHERE doc_id=? ORDER BY rowid LIMIT 1", (d,)).fetchone()
            for d, _s in rows}
    finally:
        con.close()

    keyset = set(keys)
    first_text = {d: f"{h or ''}\n{b or ''}" for d, (h, b) in first.items()}
    head_hit = {d for d, (h, _b) in first.items()
                if _citation_keys(h or "") & keyset}
    body_hit = {d for d in first_text
                if d not in head_hit and _citation_keys(first_text[d]) & keyset}
    str_year = _doc_year(authority)
    # the authority's own docs: heading match; else (no heading match anywhere)
    # first-chunk body matches whose own year agrees with the string's — provisions
    # (pin in body, no neutral-citation year) and duplicate same-year ingests
    auth = head_hit or {d for d in body_hit if _doc_year(first_text[d]) == str_year}
    ay = str_year or next((y for d in sorted(auth)
                           if (y := _doc_year(first_text[d]))), None)
    citing = [{"doc_id": d, "source_name": s, "year": _doc_year(first_text[d]),
               "later": None if (_doc_year(first_text[d]) is None or ay is None)
               else int(_doc_year(first_text[d])) > int(ay)}
              for d, s in rows if d not in auth]
    out = {"matter": matter_ref, "keys": keys, "ok": True,
           "authority": _authority(authority, keys, ay, bool(auth), sorted(auth)),
           "citing": citing,
           "summary": {"citing_docs": len(citing),
                       "later": sum(1 for c in citing if c["later"]),
                       "same_or_earlier": sum(1 for c in citing
                                              if c["later"] is False),
                       "year_unknown": sum(1 for c in citing
                                           if c["later"] is None)},
           "note": "citator-lite lists citing judgments only — treatment "
                   "(overruled/distinguished) is a human reading call, not a signal"}
    return out


def citator(matter_ref: str, authority: str | None = None, path: str | None = None,
            store=None) -> dict:
    """Entry point: one authority, or every authority a deliverable names."""
    if authority:
        return citing_judgments(matter_ref, authority, store=store)
    if not path:
        return {"matter": matter_ref, "ok": False,
                "error": "pass authority=<one citation> or path=<deliverable file>"}
    f = Path(path)
    if store is not None and not f.is_absolute():
        f = Path(store.db_path).parent / f
    elif not f.is_absolute():
        root, _src = resolve_store_root()
        f = Path(root) / f
    try:
        text = f.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as ex:
        return {"matter": matter_ref, "ok": False,
                "error": f"deliverable not found or not readable: {ex}"}
    keys = sorted(_citation_keys(text))
    # the keys are already canonical join keys — hand them straight to the join
    # (re-parsing a key string as prose would find no citation span)
    rows = [_join(matter_ref, k, _expand([k]), store) for k in keys]
    authorities = [{"key": r["authority"]["raw"],
                    "in_corpus": r["authority"]["in_corpus"],
                    "authority_year": r["authority"]["year"],
                    "citing_docs": r["summary"]["citing_docs"],
                    "later_citing": r["summary"]["later"],
                    **({"citing": r["citing"]}
                       if r["summary"]["citing_docs"] else {})}
                   for r in rows]
    return {"matter": matter_ref, "path": str(path), "ok": True,
            "authorities": authorities,
            "summary": {"authorities": len(rows),
                        "with_later_citations": sum(
                            1 for r in rows if r["summary"]["later"])},
            "note": "informational: later citing judgments surface the good-law "
                    "question — they do not by themselves invalidate a deliverable"}
