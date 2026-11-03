# tests/test_trust_tier.py — G3's leak barrier: privileged-tier text stays READABLE
# (passages) but never QUOTABLE (authorities, verify_document). Search excludes
# T0/T2/unknown from authorities; verify flags a quote that lives only in privileged
# chunks PRIVILEGED (ok=false, not closable as a ruled exception).
import sqlite3
import sys
from pathlib import Path

PLUGIN = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PLUGIN / "mcp"))

from harness.corpus import (CorpusStore, DocRecord, chunk_text,           # noqa: E402
                            ironfleet_corpus_search, quotable_tier)
from harness.verify import load_chunks, verify_document                   # noqa: E402
from harness.vectors import VectorStore                                   # noqa: E402


def fake_embed(texts):                      # same offline proxy as test_smoke.py
    return [[float(ord(c) % 17) for c in t[:8].ljust(8, "x")] for t in texts]


def _store(tmp_path):
    return CorpusStore(tmp_path / "corpus.sqlite3",
                       vectors=VectorStore(tmp_path / "vectors.sqlite3", dim=8))


def _ingest(store, matter, doc_id, text, tier="T1"):
    embedded = chunk_text(doc_id, text)
    store.ingest(matter, DocRecord(doc_id, text, f"{doc_id}.txt", trust_tier=tier),
                 vectors=fake_embed(embedded), model="fake", provider="test")


WP = ("SETTLEMENT CORRESPONDENCE\n\nWithout prejudice, we offer eighty thousand "
      "dollars in full and final settlement of the whole dispute.") * 4
OPEN = ("OPEN LETTER\n\nWe acknowledge receipt of your letter and confirm the "
        "delivery of the goods ordered last March.") * 4
WP_LINE = ("Without prejudice, we offer eighty thousand dollars in full and final "
           "settlement of the whole dispute")
OPEN_LINE = ("We acknowledge receipt of your letter and confirm the delivery of "
             "the goods ordered last March")


def test_quotable_tier_table():
    assert quotable_tier("T1") and quotable_tier("T3")
    for t in ("T0", "T2", "T9", "", None):
        assert not quotable_tier(t)             # unknown tier -> privileged, fail-closed
    assert quotable_tier("T2", min_tier="T0")   # explicit floor opens known tiers
    assert not quotable_tier("T0") and not quotable_tier("T9", min_tier="T0")


def test_search_authorities_tier_filtered(tmp_path):
    store = _store(tmp_path)
    for did, text, tier in (("d-wp", WP, "T0"), ("d-open", OPEN, "T1"),
                            ("d-int", "INTERNAL MEMO\n\nOur settlement ceiling is "
                                      "ninety thousand dollars before costs.", "T2"),
                            ("d-unk", "UNCLASSIFIED\n\nunclassified scribble about "
                                      "delivery schedules", "T9")):
        _ingest(store, "m-tier", did, text, tier)
    got = ironfleet_corpus_search("settlement delivery acknowledge ceiling", k=10,
                                  store=store, embed_fn=fake_embed, rerank=False,
                                  matter="m-tier")
    tiers = {p["doc_id"]: p["trust_tier"] for p in got["passages"]}
    assert tiers == {"d-wp": "T0", "d-open": "T1", "d-int": "T2", "d-unk": "T9"}
    quoted = "\n".join(got["authorities"])
    assert "acknowledge receipt" in quoted                    # the T1 doc is quotable
    for leak in ("eighty thousand", "ceiling", "unclassified scribble"):
        assert leak not in quoted                             # T0/T2/unknown never
    got0 = ironfleet_corpus_search("settlement delivery acknowledge ceiling", k=10,
                                   store=store, embed_fn=fake_embed, rerank=False,
                                   matter="m-tier", min_tier="T0")
    quoted0 = "\n".join(got0["authorities"])
    assert "eighty thousand" in quoted0 and "ceiling" in quoted0   # explicit floor
    assert "unclassified scribble" not in quoted0                  # unknown stays out


def test_verify_privileged_leak_blocked(tmp_path):
    store = _store(tmp_path)
    _ingest(store, "m-leak", "d-wp", WP, "T0")     # WP ingested FIRST: quotable copy later
    _ingest(store, "m-leak", "d-open", OPEN, "T1")
    draft = tmp_path / "advice.md"
    draft.write_text(f'WP only: "{WP_LINE}".\nOpen: "{OPEN_LINE}".\n'
                     f'Nowhere: "the moon was made of green cheese in nineteen '
                     f'eighty four".\n', encoding="utf-8")
    out = verify_document("m-leak", str(draft), store=store)
    verdicts = {q["quote"][:24]: q["verdict"] for q in out["quotes"]}
    assert verdicts[WP_LINE[:24]] == "PRIVILEGED"
    assert verdicts[OPEN_LINE[:24]] == "VERIFIED"
    assert verdicts["the moon was made of gre"] == "NOT_IN_CORPUS"
    assert out["ok"] is False
    row = next(q for q in out["quotes"] if q["verdict"] == "PRIVILEGED")
    assert row["source_name"] == "d-wp.txt" and row["trust_tier"] == "T0"


def test_verify_open_copy_rescues_identical_bytes(tmp_path):
    store = _store(tmp_path)
    _ingest(store, "m-dup", "d-wp", WP, "T0")
    _ingest(store, "m-dup", "d-copy", WP, "T1")    # identical bytes, open tier
    draft = tmp_path / "a.md"
    draft.write_text(f'"{WP_LINE}".', encoding="utf-8")
    out = verify_document("m-dup", str(draft), store=store)
    assert out["quotes"][0]["verdict"] == "VERIFIED" and out["ok"] is True


def _legacy_db(tmp_path):
    """A pre-G3 matter: docs table without trust_tier (the old 6-column schema)."""
    db = tmp_path / "legacy.sqlite3"
    con = sqlite3.connect(db)
    con.execute("CREATE TABLE docs_mleg (doc_id TEXT PRIMARY KEY, source_name TEXT,"
                " sha256 TEXT, words INTEGER, chunk_count INTEGER, ts TEXT)")
    con.execute("CREATE VIRTUAL TABLE fts_mleg USING fts5(doc_id, heading, body)")
    con.execute("INSERT INTO docs_mleg VALUES ('doc-old','old.txt','x',9,1,'2026-01-01')")
    con.execute("INSERT INTO fts_mleg (doc_id, heading, body) VALUES ('doc-old','',"
                "'We acknowledge receipt of your letter and confirm the delivery')")
    con.commit()
    con.close()
    return db


def test_pre_g3_corpus_migrates_in_place(tmp_path):
    store = CorpusStore(_legacy_db(tmp_path))      # no vectors: lexical leg only
    got = ironfleet_corpus_search("acknowledge receipt delivery", store=store,
                                  embed_fn=fake_embed, rerank=False, matter="mleg")
    assert got["passages"] and got["authorities"]  # healed: column added, not dropped
    assert got["passages"][0]["trust_tier"] == "T1"
    assert store.docs("mleg")[0]["trust_tier"] == "T1"


def test_verify_reads_pre_g3_corpus_as_t1(tmp_path):
    # the court's bare box: read-only db, no healing possible — legacy rows are T1
    # by the column's own declared DEFAULT, so the check still runs.
    chunks = load_chunks("mleg", _legacy_db(tmp_path))
    assert chunks[0]["trust_tier"] == "T1" and "acknowledge receipt" in chunks[0]["text"]
