# src/harness/vectors.py
# VENDOR NOTE — copied from harness-core src/harness/vectors.py (IronFleet programme).
# One delta, found live on fresh Ubuntu 2026-10-22: the harness venv always had pydantic
# installed, so `from pydantic import BaseModel` for the 3-field SearchHit never bit —
# on a bare box it broke server BOOT (a hardcoded third-party import for a data holder).
# SearchHit is now a stdlib dataclass; byte-identical attribute access everywhere.
"""A-4 thin local vector index — NOW on sqlite-vec (R1 plan Task 4, spec 14 D4).

The S7e interface is unchanged (add/search/count, per-matter confidentiality); the
engine underneath is swapped from pure-Python cosine to sqlite-vec 0.1.9 (pinned),
which the S7e spec pre-authorised as a store-internal change. D4: the extension is a
HARD dependency — fail-closed at construction, no silent pure-Python fallback (a slow
index that "works" is the S7e scaling lie again; the swap is justified by measurement:
pure-Python cosine 333 ms @ 2.4k chunks).

Vectors are normalised at add time, so sqlite-vec's L2 distance maps to exact cosine
by score = 1 - d²/2 (self-match → 1.0). A row whose vector is not `dim`-long is
REFUSED at add (fail loud), not silently skipped — an index that silently shrinks is
the prefix-embedding lie again.
"""
from __future__ import annotations

import sqlite3
from array import array
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path


@dataclass
class SearchHit:
    seq: int
    text: str
    score: float


def _load_extension(con: sqlite3.Connection) -> None:
    try:
        import sqlite_vec
    except ImportError as ex:                              # pragma: no cover — pinned dep
        raise RuntimeError("sqlite-vec is a hard dependency (D4, pinned 0.1.9): "
                           "pip install sqlite-vec==0.1.9") from ex
    try:
        con.enable_load_extension(True)
        con.load_extension(sqlite_vec.loadable_path())
    except Exception as ex:                                # noqa: BLE001 — fail closed
        raise RuntimeError(f"sqlite-vec extension failed to load (D4 fail-closed): {ex}") from ex


def _unit(v: array) -> array:
    n = sum(x * x for x in v) ** 0.5
    if n == 0.0:
        return v
    return array("f", (x / n for x in v))


class VectorStore:
    def __init__(self, db_path: Path, dim: int = 1024) -> None:
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.dim = dim
        self.last_skipped: list[int] = []      # interface compat: the vec0 engine has no
        con = self._c()                        # skippable rows — mismatches refuse at add
        with con:
            con.executescript(f"""
            PRAGMA journal_mode=WAL;
            CREATE TABLE IF NOT EXISTS embeddings(
              id INTEGER PRIMARY KEY AUTOINCREMENT, ts TEXT,
              matter_ref TEXT, seq INTEGER, text TEXT, model TEXT, provider TEXT);
            CREATE INDEX IF NOT EXISTS idx_emb_matter ON embeddings(matter_ref);
            CREATE VIRTUAL TABLE IF NOT EXISTS vec_index USING vec0(
              embedding float[{dim}], matter_ref TEXT PARTITION KEY);
            """)
            try:
                con.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_emb_matter_text "
                            "ON embeddings(matter_ref, text)")
            except sqlite3.IntegrityError:
                # Legacy store (pre-idempotence): duplicate (matter_ref, text) rows from
                # interrupted-then-rerun ingests. Self-migrate — earliest row wins —
                # then bind the constraint. A no-op on every compliant store.
                con.execute(
                    "DELETE FROM vec_index WHERE rowid IN (SELECT id FROM embeddings e "
                    "WHERE EXISTS (SELECT 1 FROM embeddings t WHERE "
                    "t.matter_ref=e.matter_ref AND t.text=e.text AND t.id < e.id))")
                con.execute(
                    "DELETE FROM embeddings WHERE id IN (SELECT id FROM embeddings e "
                    "WHERE EXISTS (SELECT 1 FROM embeddings t WHERE "
                    "t.matter_ref=e.matter_ref AND t.text=e.text AND t.id < e.id))")
                con.execute("CREATE UNIQUE INDEX idx_emb_matter_text "
                            "ON embeddings(matter_ref, text)")

    def _c(self) -> sqlite3.Connection:
        con = sqlite3.connect(self.db_path)
        _load_extension(con)
        return con

    def add(self, matter_ref: str, texts: list[str], vectors: list[list[float]],
            model: str, provider: str) -> int:
        """Idempotent per (matter_ref, text) as of 2026-10-14: an interrupted-then-rerun
        ingest previously appended DUPLICATE rows (measured live: 48,436 rows / 18,845
        distinct texts), and duplicate KNN rows crowd out unique chunks at depth —
        the first write wins, re-adds are ignored, and a model swap is a deliberate
        wipe-and-reindex (the row's model column records what is stored)."""
        if len(texts) != len(vectors):
            raise ValueError(f"{len(texts)} texts but {len(vectors)} vectors")
        ts = datetime.now(timezone.utc).isoformat()
        con = self._c()
        with con:
            for seq, (text, vec) in enumerate(zip(texts, vectors)):
                u = _unit(array("f", map(float, vec)))
                if len(u) != self.dim:
                    raise ValueError(f"vector {seq} is {len(u)}-dim; this store is "
                                     f"{self.dim}-dim (D4: refuse, never shrink)")
                cur = con.execute(
                    "INSERT OR IGNORE INTO embeddings(ts,matter_ref,seq,text,model,provider)"
                    " VALUES(?,?,?,?,?,?)",
                    (ts, matter_ref, seq, text, model, provider))
                if cur.rowcount:               # duplicate text: the stored row stands
                    con.execute(
                        "INSERT INTO vec_index(rowid, matter_ref, embedding) VALUES(?,?,?)",
                        (cur.lastrowid, matter_ref, u.tobytes()))
        return len(texts)

    def search(self, matter_ref: str, query: list[float], k: int = 5) -> list[SearchHit]:
        q = _unit(array("f", map(float, query)))
        con = self._c()
        rows = con.execute(
            "SELECT v.rowid, v.distance FROM vec_index v "
            "WHERE v.matter_ref=? AND v.embedding MATCH ? "
            "ORDER BY distance LIMIT ?", (matter_ref, q.tobytes(), k)).fetchall()
        out: list[SearchHit] = []
        for rid, dist in rows:
            meta = con.execute(
                "SELECT seq, text FROM embeddings WHERE id=?", (rid,)).fetchone()
            if meta is None:                       # vec row without metadata: never surface
                continue
            # unit vectors: cosine = 1 - d²/2 (exact; self-match → 1.0)
            out.append(SearchHit(seq=meta[0], text=meta[1],
                                 score=1.0 - (dist ** 2) / 2.0))
        con.close()
        out.sort(key=lambda h: h.score, reverse=True)
        return out

    def count(self, matter_ref: str) -> int:
        con = self._c()
        try:
            return con.execute("SELECT COUNT(*) FROM embeddings WHERE matter_ref=?",
                               (matter_ref,)).fetchone()[0]
        finally:
            con.close()

    def list_texts(self, matter_ref: str, limit: int = 20, offset: int = 0) -> list[dict]:
        """R (2026-10-14): row-level read for ops visibility (count/search are the
        retrieval reads; this is the store-inspection read). Newest last, id order."""
        con = self._c()
        try:
            rows = con.execute(
                "SELECT id, ts, model, provider, seq, text FROM embeddings "
                "WHERE matter_ref=? ORDER BY id LIMIT ? OFFSET ?",
                (matter_ref, limit, offset)).fetchall()
        finally:
            con.close()
        return [{"id": r[0], "ts": r[1], "model": r[2], "provider": r[3],
                 "seq": r[4], "text": r[5]} for r in rows]

    def delete(self, matter_ref: str, texts: list[str] | None = None) -> int:
        """D (2026-10-14): delete specific texts, or the WHOLE matter when texts is
        None (a matter purge). Index rows go with their metadata (vec_index.rowid ==
        embeddings.id). Returns the number of embedding rows removed. The store never
        decides scope: callers (the harness CLI gates it behind --yes) own consent."""
        con = self._c()
        try:
            with con:
                if texts is None:
                    con.execute(
                        "DELETE FROM vec_index WHERE rowid IN "
                        "(SELECT id FROM embeddings WHERE matter_ref=?)", (matter_ref,))
                    con.execute("DELETE FROM vec_index WHERE matter_ref=?", (matter_ref,))
                    cur = con.execute(
                        "DELETE FROM embeddings WHERE matter_ref=?", (matter_ref,))
                else:
                    marks = ",".join("?" for _ in texts)
                    con.execute(
                        f"DELETE FROM vec_index WHERE rowid IN "
                        f"(SELECT id FROM embeddings WHERE matter_ref=? "
                        f"AND text IN ({marks}))", (matter_ref, *texts))
                    cur = con.execute(
                        f"DELETE FROM embeddings WHERE matter_ref=? "
                        f"AND text IN ({marks})", (matter_ref, *texts))
                return cur.rowcount
        finally:
            con.close()
