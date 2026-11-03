# mcp/harness/verify.py — G1 (ROADMAP-0.2.0): the ground-truth citation checker.
# Mechanical, offline, re-runnable: reads the deliverable, checks every quoted span and
# every [E.n.S.n] reference against the matter's corpus chunks by BYTE containment.
# No LLM, no embeddings, no sqlite-vec — the FTS docs/body tables are all it reads,
# so it runs on a bare box and a court can run it with nothing but the corpus file.
"""Verdicts, per the corpus contract:
  VERIFIED      the quoted span is a byte substring of a corpus chunk of this matter
  PRIVILEGED    the span lives only in privileged-tier chunks (T0/T2, G3) — it must
                not appear in an open deliverable; not closable as a ruled exception
  MISMATCH      a reference resolved to a chunk that does not contain the quote
  NOT_IN_CORPUS the quoted span (or the ref's quote) is nowhere in this matter's corpus

shortcut: byte-substring containment, not NLI entailment — the contract a drafting
model can break is VERBATIM quoting, so that is what this proves. Whether the passage
SUPPORTS the proposition is G6's job. Upgrade to entailment when G6 lands.
"""
from __future__ import annotations

import bisect
import re
import sqlite3
from pathlib import Path

from harness.corpus import _REF_TOKEN, _mtable, quotable_tier
from harness.paths import resolve_store_root

MIN_QUOTE_WORDS = 6            # below this a quoted span is a phrase, not a quotation claim
_QUOTE = re.compile(r"[\"“](.+?)[\"”]", re.DOTALL)     # straight + curly, may wrap a line
_WS = re.compile(r"\s+")


def _norm(s: str) -> str:
    """Whitespace-collapsed: a quote wrapped across a line break is still a quote."""
    return _WS.sub(" ", s).strip()


def load_chunks(matter: str, store_path: Path) -> list[dict]:
    """This matter's ingested chunks, straight from the docs table it ingested into."""
    db = Path(store_path)
    if not db.exists():
        return []
    con = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
    try:
        try:
            rows = con.execute(
                f"SELECT f.doc_id, f.heading, f.body, d.source_name, d.trust_tier, d.ts"
                f" FROM {_mtable(matter, 'fts')} f"
                f" JOIN {_mtable(matter, 'docs')} d ON d.doc_id = f.doc_id"
                f" ORDER BY f.rowid").fetchall()
        except sqlite3.OperationalError as ex:
            if "no such column" in str(ex):
                # pre-G3 corpus opened read-only (a court's bare box): the column's
                # declared DEFAULT is T1, so legacy rows are open by the roadmap's
                # own ruling — read them as T1 instead of failing every check.
                # (ts predates G3 — every table has it.)
                rows = con.execute(
                    f"SELECT f.doc_id, f.heading, f.body, d.source_name, 'T1', d.ts"
                    f" FROM {_mtable(matter, 'fts')} f"
                    f" JOIN {_mtable(matter, 'docs')} d ON d.doc_id = f.doc_id"
                    f" ORDER BY f.rowid").fetchall()
            else:
                return []                 # matter never ingested -> empty, not a raise
        return [{"doc_id": r[0], "heading": r[1] or "", "text": r[2],
                 "source_name": r[3], "trust_tier": r[4], "synced_at": r[5]}
                for r in rows]
    finally:
        con.close()


def _locate(chunks: list[dict], quote: str) -> tuple[dict | None, bool]:
    """The chunk this quote is byte-contained in — the ground-truth join, tier-aware
    (G3): identical bytes carried by ANY open-enough chunk verify (they already exist
    in an open source); a span that lives only in privileged chunks is a leak.
    Returns (deciding_chunk, quotable); the chunk is None when nowhere in corpus."""
    priv: dict | None = None
    for c in chunks:
        if quote in _norm(c["text"]):
            if quotable_tier(c["trust_tier"]):
                return c, True
            priv = priv or c
    return priv, False


def verify_document(matter: str, path: str, store: object | None = None) -> dict:
    """Check one deliverable against the matter's corpus. `store` is a CorpusStore
    (tests inject one); default resolves the production store root. Never raises."""
    if not matter:
        return {"ok": False, "error": "no matter bound", "refs": [], "quotes": [],
                "summary": {"verified": 0, "corrected": 0, "ungrounded": 0},
                "corpus_chunks": 0}
    if store is not None:
        store_path = Path(store.db_path)
    else:
        root, _source = resolve_store_root()
        store_path = Path(root) / "corpus.sqlite3"

    out = {"matter": matter, "path": str(path), "corpus_chunks": 0, "refs": [],
           "quotes": [], "summary": {"verified": 0, "corrected": 0, "ungrounded": 0}}

    f = Path(path)
    if store is not None and not f.is_absolute():
        f = store_path.parent / f
    try:
        text = f.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as ex:
        out["ok"] = False
        out["error"] = f"deliverable not found or not readable: {ex}"
        return out

    chunks = load_chunks(matter, store_path)
    out["corpus_chunks"] = len(chunks)

    line_starts = [0] + [m.end() for m in re.finditer(r"\n", text)]

    def line_at(offset: int) -> int:
        return bisect.bisect_right(line_starts, offset)

    # 1. every quoted span — matched over the WHOLE document, so a quote wrapped
    #    across a line break is still a quote.
    spans: list[dict] = []                 # rows, in document order
    ends: list[int] = []                   # span end offsets, ascending (for bisect)
    for m in _QUOTE.finditer(text):
        span = _norm(m.group(1))
        if len(span.split()) < MIN_QUOTE_WORDS:
            continue                      # a legal phrase, not a quotation claim
        hit, quotable = _locate(chunks, span)
        spans.append({"quote": span,
                      "verdict": "VERIFIED" if quotable else
                                 ("PRIVILEGED" if hit else "NOT_IN_CORPUS"),
                      "source_name": hit["source_name"] if hit else None,
                      "trust_tier": hit["trust_tier"] if hit else None,
                      "synced_at": hit["synced_at"] if hit else None,
                      "line": line_at(m.start())})
        ends.append(m.end())
    out["quotes"] = spans

    # 2. every reference token is REPORTED (the trace names which token failed) and
    #    borrows its verdict from the span it cites — a draft writes the quote then the
    #    ref, so the owner is the nearest span ENDING before the token.
    cited: set[int] = set()
    for m in _REF_TOKEN.finditer(text):
        i = bisect.bisect_right(ends, m.start()) - 1
        owner = spans[i] if i >= 0 else None
        if owner is not None:
            cited.add(i)
        out["refs"].append({
            "ref": m.group(0),
            "verdict": owner["verdict"] if owner else "NOT_IN_CORPUS",
            "found_in": owner["source_name"] if owner else None,
            "synced_at": owner["synced_at"] if owner else None,
            "line": line_at(m.start())})

    # No MISMATCH branch here: pinning a ref to its sentence needs the run's evidence
    # table ([E.n.S.n] -> sentence), which exists only once a stage logs it (G5's
    # `evidence` event) — ironfleet_objection reads that event and emits MISMATCH.
    # Without a table a ref can only be VERIFIED (its quote is somewhere in this
    # matter's corpus) or NOT_IN_CORPUS.
    # summary counts CITATION INSTANCES so a gate never understates: every ref counts
    # (two refs on one bad quote = 2), and a quote no ref cites counts once — a quote
    # in the text is still an assertion the draft is making.
    for row in out["refs"] + [s for j, s in enumerate(spans) if j not in cited]:
        out["summary"]["verified" if row["verdict"] == "VERIFIED" else "ungrounded"] += 1
    # W2 step 3: the run's currency date — the newest ingest time among the chunks
    # that decided a VERIFIED verdict. ISO-8601 UTC strings compare lexically.
    synced = [s["synced_at"] for s in spans
              if s["verdict"] == "VERIFIED" and s["synced_at"]]
    out["freshness"] = max(synced) if synced else None
    out["ok"] = (out["summary"]["corrected"] == 0
                 and out["summary"]["ungrounded"] == 0)
    return out
