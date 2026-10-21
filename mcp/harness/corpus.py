# VENDOR NOTE — copied from harness-core src/harness/corpus.py (IronFleet programme,
# R1 spec 14) for the ironfleet-legal plugin. Exactly three deltas from the source of
# record, all in the DEFAULT callables; every store/split/search/splice function is
# byte-identical: (1) the harness.gate import is gone (the plugin MCP server is
# mechanical-only — embeddings go direct to local Ollama, rerank to local llama-server
# via harness.localstack); (2) the default expand_fn raises instead of dispatching an
# LLM (Claude does its own multi-query by calling the tool per query); (3) the
# _default_gate lazy builder is gone for the same reason as (1).
"""R1 (spec 14): the citation-exact legal corpus layer — store, retrieval, composition.

Task 1: the structure-aware splitter, promoted verbatim from the research bench
(scripts/bench_r1_ingest.py, which now imports this module). D2: paragraph- AND
heading-aware; every chunk carries its section heading as provenance.
"""
from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass

from harness.vectors import VectorStore

_HEADING = re.compile(r"^(?:[IVXLC]+|\d+)[.\)]?\s+[A-Z].*[A-Z]{3}")   # "III. Title ..." / "12. Foo Bar"
_ALLCAPS = re.compile(r"^[^a-z]{6,}$")                                # "TITLE TO BULLION"


@dataclass
class Chunk:
    doc_id: str
    heading: str
    text: str


def split_structure(doc_id: str, text: str, target_words: int = 210) -> list[Chunk]:
    """Paragraph- AND heading-aware split; each chunk carries its section heading.

    Legal structure honoured: ALL-CAPS headings, roman/numbered headings ("III. Title"),
    and blank-line paragraphs. A paragraph is never split mid-way unless it alone exceeds
    2x target (hard-split then — judgments have some very long paragraphs).
    """
    chunks: list[Chunk] = []
    heading = ""
    para_buf: list[str] = []
    buf_words = 0

    def flush() -> None:
        nonlocal para_buf, buf_words
        body = "\n\n".join(para_buf).strip()
        if body:
            chunks.append(Chunk(doc_id, heading, body))
        para_buf, buf_words = [], 0

    for para in (p.strip() for p in re.split(r"\n\s*\n", text)):
        if not para:
            continue
        first_line = para.splitlines()[0].strip()
        is_heading = (len(para) <= 120
                      and (_ALLCAPS.match(first_line) or _HEADING.match(first_line)))
        if is_heading:
            flush()
            heading = first_line
            continue
        words = len(para.split())
        if words > target_words * 2:                      # hard-split an outsized paragraph
            flush()
            cur: list[str] = []
            cur_w = 0
            for s in para.split(". "):
                cur.append(s)
                cur_w += len(s.split())
                if cur_w >= target_words:
                    chunks.append(Chunk(doc_id, heading, ". ".join(cur).strip()))
                    cur, cur_w = [], 0
            if cur:
                chunks.append(Chunk(doc_id, heading, ". ".join(cur).strip()))
            continue
        if buf_words and buf_words + words > target_words:
            flush()
        para_buf.append(para)
        buf_words += words
    flush()
    return chunks


def chunk_text(doc_id: str, text: str) -> list[str]:
    """The embedded form: heading-prefixed chunk bodies."""
    return [f"{c.heading}\n{c.text}" if c.heading else c.text
            for c in split_structure(doc_id, text)]


# ------------------------------------------------------------------ R1 Task 2: the store

import hashlib  # noqa: E402
import sqlite3  # noqa: E402
from datetime import datetime, timezone  # noqa: E402
from pathlib import Path  # noqa: E402


@dataclass
class DocRecord:
    doc_id: str
    text: str
    source_name: str


@dataclass
class CorpusHit:
    doc_id: str
    heading: str
    text: str
    source_name: str
    score: float


def _mtable(matter_ref: str, kind: str) -> str:
    """Colon-free per-matter table names (Windows rule; D1: one table PER MATTER —
    FTS5 BM25 statistics span the whole table even under a column filter, so shared
    tables degrade ranking and leak corpus shape across matters; measured 2026-10-13)."""
    name = re.sub(r"[^A-Za-z0-9_]", "_", matter_ref)
    return f"{kind}_{name}"


def _fts_query(query: str, max_terms: int = 24) -> str:
    """FTS5 OR of the alphanumeric tokens — FTS5 query syntax chokes on legal punctuation."""
    terms = [t for t in re.findall(r"[A-Za-z0-9]{3,}", query)][:max_terms]
    return " OR ".join(f'"{t}"' for t in terms)


# ------------------------------------------------- R1 Task-3 amendment: citation injection
_ACT_RE = re.compile(
    r"((?:[A-Z][A-Za-z’'\-\.]*\s+){0,11}(?:Act|Acts|Regulations|Rules)\s+"
    r"(?:19\d\d|20\d\d))")
_SECT_RE = re.compile(
    r"(?:ss\.?|s\.?|sections?\.?)\s+(\d+[A-Za-z()]*(?:\s+(?:and|to)\s+\d+[A-Za-z()]*"
    r"|\s+\d+[A-Za-z()]*){0,3})", re.IGNORECASE)
# case-name spans: "X v Y" (counsel lists with '& ORS' trailers) and "Re X" —
# case-sensitive proper-noun shape, but 'v'/'V' and 'Re'/'RE' both legal (headers)
_CASE_SPAN = re.compile(
    r"\b((?:[Rr]e|[Ee]x\s+[Pp]arte)\s+(?:[A-Z&][A-Za-z’'&.\-]*\s+){0,3}"
    r"[A-Z][A-Za-z’'&.\-]*"
    r"|(?:[A-Z&][A-Za-z’'&.\-]*\s+){0,5}[A-Z][A-Za-z’'&.\-]*\s+[vV](?:s\.?)?\s+"
    r"(?:[A-Z&][A-Za-z’'&.\-]*\s+){0,5}[A-Z][A-Za-z’'&.\-]*)")
_PARTICLES = {"ors", "anor", "ano", "others", "orters"}
# law-report / court designators and bare years never belong in a case-name key —
# headers write 'MADSEN-RIES & ORS V COOPER NZSC', needles write '... v Cooper
# [2020] NZSC 100'; only the name part is the join identity
_DESIGNATORS = {"nzsc", "nzca", "nzhc", "nzsca", "nzacc", "nzenv", "nzempc", "nzfc",
                "nzhrtrt", "nzlatc", "nzcpc", "nzlr", "nzflj", "ac", "clr", "alr",
                "rpc", "ukpc", "pc", "sc", "hl"}
# UNAMBIGUOUS act-name abbreviations (jurisdiction vocabulary, extensible — never per-
# case): a query writing 'PPSA 1999 s 6' must key the same join as the DLM provision
# 'Personal Property Securities Act 1999, s 6'. An abbreviation that could name two
# authorities stays OUT of this table (never merge distinct authorities).
_ABBREVIATIONS = {
    "PPSA": "Personal Property Securities Act",
}
_ABBREV_RE = re.compile(
    r"\b(" + "|".join(_ABBREVIATIONS) + r")\s+(\d{4})\b")


def _cit_key(title: str, year: str, section: str) -> str:
    return f"{re.sub(r'[^a-z ]', '', title.lower().strip())}|{year}|{section}"


def _case_key(span: str) -> str:
    words = [w for w in re.sub(r"[^A-Za-z0-9 ]", " ", span.lower()).split()
             if w not in _PARTICLES and w not in _DESIGNATORS
             and not (w.isdigit() and len(w) == 4)]
    return "case:" + " ".join(words)


def _citation_keys(text: str) -> set[str]:
    """Citation spans -> canonical join keys: 'act title|year|section' for statute
    pins, 'case:x v y' / 'case:re x' for case names (2026-10-14 amendment 2).

    The measured failure this closes (2026-10-14, live on the 36k-chunk acceptance
    corpus): for a query naming 'Companies Act 1993 s 135' exactly, BM25 ranked the
    containing provision chunk 41st among 24,343 OR-matches — 'Act' alone is in 65% of
    chunks and BM25's length normalisation lifts short amendment stubs over the real
    400-word provision. A citation is a JOIN KEY, not a prose match: section spans are
    found in a window around the act-year match, so 's 135 ... Companies Act 1993'
    (query order) and 'Companies Act 1993, s 135' (DLM anchor body) canonicalise alike.
    The case-name keys close the measured PRESENT_NOT_RETRIEVED class (24 needles,
    dominated by neutral-cited judgments: 'Madsen-Ries v Cooper [2020] NZSC 100' never
    surfaced because nothing joined on the party names). Keys are exact-span matches —
    case-folded, punctuation-stripped, '& ORS'-particles dropped — so distinct
    authorities with similar names NEVER merge; a spurious join only adds a candidate
    that must still survive fusion, rerank, and the guard.
    """
    keys: set[str] = set()
    text = _ABBREV_RE.sub(
        lambda m: f"{_ABBREVIATIONS[m.group(1)]} {m.group(2)}", text)
    for act in _ACT_RE.finditer(text):
        window = text[max(0, act.start() - 60):act.end() + 60]
        span = act.group(1)
        year, title = span[-4:], span[:-4].strip()
        secs = _SECT_RE.findall(window)
        if not secs:
            continue   # no section in scope: leave the whole-act match to BM25
        for _s in [_s for sec in secs for _s in re.findall(r"\d+[A-Za-z()]*", sec)]:
            keys.add(_cit_key(title, year, _s))
    for m in _CASE_SPAN.finditer(text):
        k = _case_key(m.group(1))
        if 2 <= len(k[5:].split()) <= 14:                  # drop 1-word noise
            keys.add(k)
    return keys


class CorpusStore:
    """One SQLite db at the store root; each matter gets its own docs + FTS tables (D1).

    The store never dispatches: the caller embeds (through the gate — D3/LOCAL_ONLY)
    and hands vectors in, aligned 1:1 with the doc's chunks. Vectors ride the existing
    VectorStore interface (Task 4 swaps its engine store-internally).
    """

    def __init__(self, db_path: Path, vectors: "VectorStore | None" = None) -> None:
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._vectors = vectors
        with self._c() as c:
            c.executescript("PRAGMA journal_mode=WAL;")

    def _c(self) -> sqlite3.Connection:
        return sqlite3.connect(self.db_path)

    def has_doc(self, matter_ref: str, sha256: str) -> bool:
        try:
            with self._c() as c:
                row = c.execute(
                    f"SELECT 1 FROM {_mtable(matter_ref, 'docs')} WHERE sha256=?",
                    (sha256,)).fetchone()
        except sqlite3.OperationalError:        # matter never ingested -> not present
            return False
        return row is not None

    def ingest(self, matter_ref: str, doc: DocRecord, vectors: list,
               model: str, provider: str) -> int:
        chunks = split_structure(doc.doc_id, doc.text)
        if len(vectors) != len(chunks):
            raise ValueError(f"{len(vectors)} vectors for {len(chunks)} chunks "
                             f"of {doc.doc_id} — the caller embeds 1:1 with the split")
        sha = hashlib.sha256(doc.text.encode("utf-8")).hexdigest()
        with self._c() as c:
            c.execute(f"CREATE TABLE IF NOT EXISTS {_mtable(matter_ref, 'docs')}"
                      "(doc_id TEXT PRIMARY KEY, source_name TEXT, sha256 TEXT,"
                      " words INTEGER, chunk_count INTEGER, ts TEXT)")
            c.execute(f"CREATE VIRTUAL TABLE IF NOT EXISTS {_mtable(matter_ref, 'fts')}"
                      " USING fts5(doc_id, heading, body)")
            c.execute(f"CREATE TABLE IF NOT EXISTS {_mtable(matter_ref, 'cites')}"
                      "(key TEXT, fts_rowid INTEGER, PRIMARY KEY(key, fts_rowid))")
            c.execute(f"INSERT OR REPLACE INTO {_mtable(matter_ref, 'docs')}"
                      " VALUES(?,?,?,?,?,?)",
                      (doc.doc_id, doc.source_name, sha, len(doc.text.split()),
                       len(chunks), datetime.now(timezone.utc).isoformat()))
            c.execute(f"DELETE FROM {_mtable(matter_ref, 'fts')} WHERE doc_id=?",
                      (doc.doc_id,))
            c.execute(f"DELETE FROM {_mtable(matter_ref, 'cites')} WHERE key IN "
                      f"(SELECT key FROM {_mtable(matter_ref, 'cites')} WHERE "
                      f"fts_rowid IN (SELECT rowid FROM {_mtable(matter_ref, 'fts')}"
                      " WHERE doc_id=?))", (doc.doc_id,))
            c.executemany(f"INSERT INTO {_mtable(matter_ref, 'fts')}"
                          "(doc_id, heading, body) VALUES(?,?,?)",
                          [(ch.doc_id, ch.heading, ch.text) for ch in chunks])
            rowids = [r[0] for r in c.execute(
                f"SELECT rowid FROM {_mtable(matter_ref, 'fts')} WHERE doc_id=? "
                f"ORDER BY rowid", (doc.doc_id,))]
            # the join keys: each chunk's own citation spans (the DLM provision anchor
            # lands in the body; judgment bodies cite provisions inline too)
            cite_rows = [(k, rid) for rid, ch in zip(rowids, chunks)
                         for k in _citation_keys(f"{ch.heading}\n{ch.text}")]
            c.executemany(f"INSERT OR REPLACE INTO {_mtable(matter_ref, 'cites')}"
                          " VALUES(?,?)", cite_rows)
        if self._vectors is not None:
            self._vectors.add(matter_ref,
                              chunk_text(doc.doc_id, doc.text),
                              [list(map(float, v)) for v in vectors], model, provider)
        return len(chunks)

    def search_lexical(self, matter_ref: str, query: str, k: int = 20) -> list[CorpusHit]:
        q = _fts_query(query)
        if not q:
            return []
        try:
            rows = self._c().execute(
                f"SELECT f.doc_id, f.heading, f.body, d.source_name, bm25({_mtable(matter_ref, 'fts')})"
                f" FROM {_mtable(matter_ref, 'fts')} f"
                f" JOIN {_mtable(matter_ref, 'docs')} d ON d.doc_id = f.doc_id"
                f" WHERE {_mtable(matter_ref, 'fts')} MATCH ? ORDER BY 5 LIMIT ?",
                (q, k)).fetchall()
        except sqlite3.OperationalError:
            return []
        return [CorpusHit(doc_id=d, heading=h, text=b, source_name=s, score=-sc)
                for d, h, b, s, sc in rows]

    def reindex_cites(self, matter_ref: str) -> int:
        """(Re)derive cites_<m> from the stored chunks — keys are pure text, so no
        re-embedding. Runs after upgrading an already-ingested corpus to the
        citation-injection amendment (2026-10-14)."""
        with self._c() as c:
            c.execute(f"CREATE TABLE IF NOT EXISTS {_mtable(matter_ref, 'cites')}"
                      "(key TEXT, fts_rowid INTEGER, PRIMARY KEY(key, fts_rowid))")
            c.execute(f"DELETE FROM {_mtable(matter_ref, 'cites')}")
            rows = c.execute(
                f"SELECT rowid, heading, body FROM {_mtable(matter_ref, 'fts')}"
            ).fetchall()
            c.executemany(
                f"INSERT OR REPLACE INTO {_mtable(matter_ref, 'cites')} VALUES(?,?)",
                [(k, r) for r, h, b in rows
                 for k in _citation_keys(f"{h}\n{b}")])
            return c.execute(f"SELECT COUNT(*) FROM {_mtable(matter_ref, 'cites')}"
                             ).fetchone()[0]

    def count(self, matter_ref: str) -> int:
        """Stored chunk count (the FTS row count). Restored 2026-10-14: ae1fe3f's
        replace left this method's body orphaned inside reindex_cites, so
        accept_r1.py's C3 crashed on a missing attribute."""
        try:
            with self._c() as c:
                return c.execute(
                    f"SELECT COUNT(*) FROM {_mtable(matter_ref, 'fts')}").fetchone()[0]
        except sqlite3.OperationalError:
            return 0

    def doc_count(self, matter_ref: str) -> int:
        try:
            with self._c() as c:
                return c.execute(
                    f"SELECT COUNT(*) FROM {_mtable(matter_ref, 'docs')}").fetchone()[0]
        except sqlite3.OperationalError:
            return 0

    def docs(self, matter_ref: str) -> list[dict]:
        """The matter's ingested documents, newest first — the shell's Corpus pane
        reads this (one row per source file: name, words, chunks, when)."""
        try:
            with self._c() as c:
                rows = c.execute(
                    f"SELECT doc_id, source_name, words, chunk_count, ts"
                    f" FROM {_mtable(matter_ref, 'docs')} ORDER BY ts DESC").fetchall()
        except sqlite3.OperationalError:
            return []
        return [{"doc_id": r[0], "name": r[1], "words": r[2],
                 "chunks": r[3], "ts": r[4] or ""} for r in rows]

    def drop_matter(self, matter_ref: str) -> None:
        """D for the corpus side (2026-10-14, the matter-CRUD completion): drop the
        matter's docs + fts (+ shadow) + cites tables. ingest is create+update,
        search/count read, this deletes — a matter can be fully managed from the
        harness, never by hand-rolled SQL against the store."""
        with self._c() as c:
            for kind in ("docs", "fts", "cites"):
                c.execute(f"DROP TABLE IF EXISTS {_mtable(matter_ref, kind)}")

    def _cited_hits(self, matter_ref: str, query: str, k: int) -> list[CorpusHit]:
        """Citation-injected candidates: a citation named in the query is a join key on
        cites_<m>, bypassing BM25's length/IDF dilution — the amendment the measured
        rank-41-for-an-exact-name failure forced (2026-10-14). Empty when the query
        names no (act, section) pair."""
        keys = _citation_keys(query)
        if not keys:
            return []
        marks = ",".join("?" for _ in keys)
        try:
            rowids = [r[0] for r in self._c().execute(
                f"SELECT DISTINCT fts_rowid FROM {_mtable(matter_ref, 'cites')} "
                f"WHERE key IN ({marks}) ORDER BY fts_rowid", tuple(keys)).fetchall()]
        except sqlite3.OperationalError:
            return []   # no cites table for this matter yet
        if not rowids:
            return []
        marks = ",".join("?" for _ in rowids)
        rows = self._c().execute(
            f"SELECT f.doc_id, f.heading, f.body, d.source_name FROM "
            f"{_mtable(matter_ref, 'fts')} f JOIN {_mtable(matter_ref, 'docs')} d "
            f"ON d.doc_id = f.doc_id WHERE f.rowid IN ({marks}) ORDER BY f.rowid",
            tuple(rowids)).fetchall()
        return [CorpusHit(doc_id=d, heading=h, text=b, source_name=s,
                          score=1.0 - i / max(1, len(rows)))
                for i, (d, h, b, s) in enumerate(rows[:k])]

    def search_legs(self, matter_ref: str, query_text: str,
                    query_vector: list[float], candidates: int = 20
                    ) -> dict[str, list[CorpusHit]]:
        """The three retrieval legs as SEPARATE rankings — search() fuses them for a
        single query; search_multi() re-fuses them across queries (multi-query pool
        formation, 2026-10-14) and needs each leg's identity to record supply."""
        lex = self.search_lexical(matter_ref, query_text, candidates)
        vec: list[CorpusHit] = []
        if self._vectors is not None and query_vector:
            vec = self._vec_hits(matter_ref, list(query_vector), candidates)
        cit = self._cited_hits(matter_ref, query_text, candidates)
        return {"lexical": lex, "vector": vec, "citation": cit}

    def search(self, matter_ref: str, query_text: str, query_vector: list[float],
               k: int = 5, candidates: int = 20) -> list[CorpusHit]:
        """Hybrid: lexical BM25 + dense vector, fused by RRF (Task 3). Either leg may
        come back empty; the other carries alone. Per-matter by construction (D1).
        Citation-injected candidates ride a third ranking (Task-3 amendment) — a
        citation named in the query is a join key, not a prose match."""
        return self.search_multi(matter_ref, [(query_text, query_vector)],
                                 k=k, candidates=candidates)[0]

    def search_multi(self, matter_ref: str, queries: list[tuple[str, list[float]]],
                     k: int | None = None, candidates: int = 20
                     ) -> tuple[list[CorpusHit], dict[str, list[tuple[int, str]]]]:
        """Multi-query candidate-pool construction (the state-doc §8 lever 2: the
        reranker cannot recover evidence that never enters its pool; the saved
        expansion probe proved the expanded queries are correct but never built a
        deep MERGED pool).

        Every query's three legs run unchanged, then ONE reciprocal-rank fusion
        across all (query, leg) rankings — an agreement lift: passages found by
        several queries (or by several legs) rank above single-leg noise, while a
        needle that surfaces under ANY query stays in the pool. Identity is the
        stable passage key (doc_id+heading+text), never a vector seq (the measured
        batch-local-seq corruption). Ties resolve deterministically (stable sort =
        first-appearance order). Dedup keeps the FIRST sighting's metadata; source
        identity and provenance never change.

        Returns (fused_hits, supply): fused is the FULL ranked pool (bound it before
        rerank — the reranker refuses above its 64 ceiling), and supply[hit_key]
        lists every (query_index, leg) that produced the passage — the diagnostic
        that says which query and which leg lifted each selected passage.
        """
        leg_rankings: list[list[str]] = []
        by_key: dict[str, CorpusHit] = {}
        supply: dict[str, list[tuple[int, str]]] = {}
        for qi, (qtext, qvec) in enumerate(queries):
            legs = self.search_legs(matter_ref, qtext, qvec or [], candidates)
            for leg, hits in legs.items():
                leg_rankings.append([_hit_key(h) for h in hits])
                for h in hits:
                    hk = _hit_key(h)
                    if hk not in by_key:
                        by_key[hk] = h
                    supply.setdefault(hk, []).append((qi, leg))
        fused = [by_key[hk] for hk in rrf(leg_rankings)]
        return (fused if k is None else fused[:k]), supply

    def _vec_hits(self, matter_ref: str, query_vector: list[float],
                  candidates: int) -> list[CorpusHit]:
        hits = self._vectors.search(matter_ref, query_vector, k=candidates)
        out: list[CorpusHit] = []
        if not hits:
            return out
        with self._c() as c:
            for h in hits:
                row = c.execute(
                    f"SELECT f.doc_id, f.heading, f.body, d.source_name FROM "
                    f"{_mtable(matter_ref, 'fts')} f JOIN "
                    f"{_mtable(matter_ref, 'docs')} d ON d.doc_id = f.doc_id "
                    f"WHERE (? = '' OR f.heading || char(10) || f.body = ? OR f.body = ?)",
                    (h.text, h.text, h.text)).fetchone()
                if row:
                    out.append(CorpusHit(doc_id=row[0], heading=row[1], text=row[2],
                                         source_name=row[3], score=h.score))
        return out


# ---------------------------------------------------------------- R1 Task 3: hybrid search

def rrf(rankings: list[list[str]], k: int = 60) -> list[str]:
    """Reciprocal Rank Fusion (k=60, the 2026 standard): no score normalisation needed
    between BM25 (negative-better) and cosine (positive-better)."""
    scores: dict[str, float] = {}
    for ranking in rankings:
        for rank, item in enumerate(ranking):
            scores[item] = scores.get(item, 0.0) + 1.0 / (k + rank + 1)
    return [item for item, _ in sorted(scores.items(), key=lambda kv: -kv[1])]


def _hit_key(hit: CorpusHit) -> str:
    return f"{hit.doc_id}\x1f{hit.heading}\x1f{hit.text}"


# ------------------------------------------- multi-query expansion (2026-10-14)

_EXPAND_TMPL = """You are a legal retrieval expert. Given this New Zealand legal problem, output \
ONLY a JSON array of exactly 3 short search query strings (no commentary, no markdown) that a \
hybrid lexical+semantic search engine should run to retrieve (a) the governing statutory \
provisions, (b) the leading cases on the point, and (c) the procedural rule. Each query under 20 \
words, dense with the salient legal terms — not the facts of the parties.

PROBLEM:
{prompt}"""


def expand_query(prompt: str, dispatch_fn, max_queries: int = 3,
                 max_len: int = 200) -> list[str]:
    """Bounded multi-query expansion: the ORIGINAL query stays primary; these are
    alternate issue-form retrieval queries (the saved probe measured them correct).

    STRICT schema: the model must return a JSON array of strings. Any violation —
    malformed JSON, a non-list, a non-string, an empty or over-length query — rejects
    the WHOLE output. One attempt, no retry loop, and this function never raises: the
    caller falls back to the original query alone, which always runs (fail-open to a
    correct single-query search, never to a broken retrieval)."""
    try:
        out = json.loads(dispatch_fn(_EXPAND_TMPL.format(prompt=prompt[:1200])))
        if (not isinstance(out, list) or not out
                or not all(isinstance(q, str) for q in out)):
            return []                       # one wrong-typed element rejects the WHOLE output
        queries = [q.strip() for q in out if q.strip()]
        if not queries or any(len(q) > max_len for q in queries):
            return []
        return queries[:max_queries]
    except Exception:                                  # noqa: BLE001 — fail-open, by contract
        return []


# ---------------------------------------------------------------- R1 Task 6: the tool
# (plugin line: no gate — the defaults below go direct to LOCAL services, never cloud)


def ironfleet_corpus_search(query, k: int = 5, rerank: bool = True,
                            store: "CorpusStore | None" = None,
                            embed_fn=None, rerank_fn=None,
                            matter: str | None = None,
                            expand: bool = False, expand_fn=None,
                            pool_cap: int = 48) -> dict:
    """The gated ported tool (D5): matter-scoped hybrid corpus search whose result
    carries the AUTHORITIES list — the verbatim passage texts the guard checks quotes
    against. Fail-closed: no matter bound -> an honest empty envelope, never another
    matter's text. The store never dispatches; embeddings and rerank go through the
    injected callables (the gate in production, fakes in tests).

    expand=True builds the candidate pool multi-query (expand_query + search_multi):
    the original query first, alternates bounded and schema-validated, the merged
    pool capped at pool_cap (<= the reranker's 64 refusal ceiling) before rerank,
    and the result carries a "supply" diagnostic naming the (query, leg) pairs that
    produced each returned passage. Expansion failure degrades to the exact
    single-query search (default off — the D5 envelope and behaviour are unchanged)."""
    if isinstance(query, dict):
        # the module_e dispatch convention (the TS tools shim calls fn(args) with ONE
        # JSON-args dict); direct Python callers keep the keyword form
        args = query
        query = str(args.get("query", ""))
        k = int(args.get("k", k))
        rerank = bool(args.get("rerank", rerank))
        expand = bool(args.get("expand", expand))
        matter = args.get("matter", matter) or matter
    matter = matter or os.environ.get("IRONFLEET_MATTER", "")
    if not matter:
        return {"passages": [], "authorities": [], "error": "no matter bound"}
    if store is None:
        from harness.paths import resolve_store_root
        root, _source = resolve_store_root()
        store = CorpusStore(Path(root) / "corpus.sqlite3",
                            vectors=VectorStore(Path(root) / "vectors.sqlite3"))
    if embed_fn is None:
        from harness.localstack import embed_fn as embed_fn
    if not expand:
        qvec = embed_fn([query[:1200]])[0]
        hits = store.search(matter, query, qvec, k=max(k * 4, 20))
    else:
        if expand_fn is None:
            def expand_fn(_prompt):
                raise RuntimeError(
                    "multi-query expansion needs an LLM and the plugin MCP server is "
                    "mechanical-only — call ironfleet_corpus_search once per query instead")
        queries = [query] + expand_query(query, expand_fn)
        qvecs = embed_fn([q[:1200] for q in queries])
        hits, supply = store.search_multi(matter, list(zip(queries, qvecs)),
                                          candidates=50)
        hits = hits[:pool_cap]          # rerank REFUSES above 64 — cap before, never truncate inside
    if rerank and rerank_fn is None:
        from harness.localstack import rerank_fn as rerank_fn
    if rerank and rerank_fn is not None and hits:
        try:
            scores = rerank_fn(query[:1200], [h.text[:4000] for h in hits])
            hits = [h for _, h in sorted(zip(scores, hits), key=lambda p: -p[0])]
        except Exception:
            # The reranker being down (llama-rerank REFUSED on this box) must
            # degrade, not blind the search: un-reranked fusion order beats an
            # error envelope — the agent can still read the passages.
            pass
    top = hits[:k]
    out = {"passages": [{"doc_id": h.doc_id, "heading": h.heading, "text": h.text,
                         "source_name": h.source_name, "score": h.score} for h in top],
           "authorities": [h.text for h in top]}
    if expand:
        out["supply"] = {str(i): supply.get(_hit_key(h), [])
                         for i, h in enumerate(top)}
    return out


# ------------------------------------------------- R1 Task 10: D9 select-compose support

_SENT_SPLIT = re.compile(r"(?<=[.!?])\s+(?=[A-Z“(\[])")
_REF_TOKEN = re.compile(r"\[E\d+\.S\d+\]")


def evidence_window(passages: list[dict], min_words: int = 6, cap: int = 500
                    ) -> tuple[str, dict[str, str]]:
    """D9: render the numbered evidence window the drafting model composes against.

    Returns (block, table): the block numbers every sentence [E<extract>.S<sent>]; the
    table maps each reference to its VERBATIM sentence. The model never copies quoted
    prose — it emits references, and splice_references() restores the exact text, making
    quote-fidelity a construction property (measured 781/0 valid on a 30B model)."""
    table: dict[str, str] = {}
    blocks: list[str] = []
    offered = 0
    for e, p in enumerate(passages, 1):
        lines = []
        for s_i, sent in enumerate(
                (s.strip() for s in _SENT_SPLIT.split(p["text"])), 1):
            if len(sent.split()) < min_words:
                continue
            if offered >= cap:
                break
            ref = f"[E{e}.S{s_i}]"
            table[ref] = sent
            lines.append(f"{ref} {sent}")
            offered += 1
        if lines:
            blocks.append(f"[Extract {e} | {p.get('source', '')}]\n" + "\n".join(lines))
        if offered >= cap:
            break
    return "\n\n".join(blocks), table


def splice_references(draft: str, table: dict[str, str]) -> tuple[str, int, int]:
    """Substitute every valid reference with its verbatim sentence, in quotes.
    Returns (spliced, substituted, invalid). Invalid references stay VISIBLE in the
    output (never silently dropped — the D9 contract) and are counted for the repair
    pass / guard."""
    invalid = 0
    substituted = 0

    def rep(m: re.Match) -> str:
        nonlocal invalid, substituted
        ref = m.group(0)
        if ref in table:
            substituted += 1
            return f"\"{table[ref]}\""
        invalid += 1
        return ref

    spliced = _REF_TOKEN.sub(rep, draft)
    return spliced, substituted, invalid
