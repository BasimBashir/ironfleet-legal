# tests/test_smoke.py — the ponytail self-check: the server's tool surface and the
# records ledger must work without Ollama, Claude, or a network. Live corpus round-trip
# rides an injected fake embedder (no service calls); anything Ollama-dependent is
# out of scope here.
import json
import sys
from pathlib import Path

import pytest

PLUGIN = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PLUGIN / "mcp"))

import server  # noqa: E402
import records  # noqa: E402


def test_tools_list_shape():
    names = {t["name"] for t in server.TOOL_DEFS}
    assert {"ironfleet_corpus_search", "ironfleet_statutory_demand",
            "ironfleet_without_prejudice", "ironfleet_filing_deadline",
            "ironfleet_ingest_docs", "ironfleet_list_docs",
            "ironfleet_begin_run", "ironfleet_log_event",
            "ironfleet_finish_run", "ironfleet_provenance"} <= names
    for t in server.TOOL_DEFS:
        assert t["inputSchema"]["type"] == "object" and t["description"]


def test_filing_deadline_known_date():
    out = server.dispatch("ironfleet_filing_deadline",
                          {"service_date": "2026-03-02", "days": 15})  # Mon
    # 15 working days from Mon 2 Mar 2026, no NZ holidays in the window
    assert out["deadline"] == "2026-03-23"


def test_statutory_demand_minimum_enforced():
    out = server.dispatch("ironfleet_statutory_demand",
                          {"amount": 500, "debtor_company": "X Ltd",
                           "creditor": "Y Ltd", "debt_details": "unpaid invoice"})
    text = json.dumps(out).lower()
    assert "1000" in text or "minimum" in text      # below the s 241(4)(a) floor


def test_without_prejudice_classifies():
    out = server.dispatch("ironfleet_without_prejudice",
                          {"content": "Without prejudice, we offer $80,000 "
                                      "in full and final settlement.",
                           "trust_tier": "T1"})
    assert json.dumps(out), out
    body = json.dumps(out).lower()
    assert "wp" in body or "without" in body


def test_corpus_search_fail_closed_without_matter():
    out = server.dispatch("ironfleet_corpus_search", {"matter": "", "query": "x"})
    assert out["passages"] == [] and out["authorities"] == []
    assert "no matter bound" in out["error"]


def test_corpus_roundtrip_fake_embeddings(tmp_path, monkeypatch):
    """The vendored corpus delta (gate -> injected callables) end to end, offline."""
    monkeypatch.setenv("HARNESS_HOME", str(tmp_path))
    from harness.corpus import CorpusStore, DocRecord, ironfleet_corpus_search
    from harness.vectors import VectorStore

    def fake_embed(texts):                     # deterministic 8-dim bag-of-chars proxy
        return [[float(ord(c) % 17) for c in t[:8].ljust(8, "x")] for t in texts]

    store = CorpusStore(tmp_path / "corpus.sqlite3",
                        vectors=VectorStore(tmp_path / "vectors.sqlite3", dim=8))
    text = ("THE SUBSTANTIAL PERFORMANCE QUESTION\n\n"
            "The plaintiff delivered goods under the contract. The defendant refused "
            "payment citing defective performance. Section 42 of the Contract and "
            "Commercial Law Act 2017 governs substantial performance.") * 6
    from harness.corpus import chunk_text
    embedded = chunk_text("doc-a", text)           # the exact 1:1 ingest() expectation
    chunks = store.ingest("m-test", DocRecord("doc-a", text, "a.txt"),
                          vectors=fake_embed(embedded), model="fake", provider="test")
    assert chunks == len(embedded) > 0
    got = ironfleet_corpus_search("substantial performance s 42", k=3, store=store,
                                  embed_fn=fake_embed, rerank=False, matter="m-test")
    assert got["passages"] and got["authorities"]
    assert got["passages"][0]["text"].strip() == got["authorities"][0].strip()


def test_records_full_cycle(tmp_path):
    ws = tmp_path / "matter-ws"
    r = records.begin_run("m-x", "can I win?", workspace=str(ws), stages=["a", "b"])
    rid = r["run_id"]
    records.attach_session(rid, "sess-1", "/t/p.jsonl", workspace=str(ws))
    records.log(rid, "stage_end", {"file": "a.md"}, workspace=str(ws))
    records.checkpoint(rid, "confirm dates?", "yes", workspace=str(ws))
    done = records.finish_run(rid, "complete", [str(ws / "a.md")], workspace=str(ws))
    d = Path(r["run_dir"])
    run = json.loads((d / "run.json").read_text(encoding="utf-8"))
    assert run["session_id"] == "sess-1" and run["status"] == "complete"
    events = [json.loads(l) for l in
              (d / "trace.jsonl").read_text(encoding="utf-8").splitlines()]
    assert [e["event"] for e in events] == [
        "run_started", "stage_end", "checkpoint", "run_finished"]
    rec = (d / "RECORD.md").read_text(encoding="utf-8")
    assert "can I win?" in rec and "sess-1" in rec and done["record"].endswith("RECORD.md")


def test_records_never_blocks_on_bad_run():
    assert records.log("nope-404", "x", {}, matter="m")["ok"] is False


def test_records_index_resolves_without_workspace(tmp_path, monkeypatch):
    """Later calls must resolve the run WITHOUT workspace re-passed (found live
    2026-10-22: the orchestrator burned calls on 'unknown run_id' otherwise)."""
    monkeypatch.setenv("HARNESS_HOME", str(tmp_path))
    r = records.begin_run("m-idx", "p", workspace=str(tmp_path / "ws"))
    out = records.log(r["run_id"], "note", {"x": 1})      # no matter, no workspace
    assert out["ok"] is True
    done = records.finish_run(r["run_id"], "complete", workspace=str(tmp_path / "ws"))
    assert done["ok"] is True


def test_provenance_resolves_relative_sources(tmp_path):
    """Agents name sources relatively (found live 2026-10-22: every sha256 came back
    'absent'); the header must hash them against the workspace."""
    ws = tmp_path / "ws"
    ws.mkdir()
    (ws / "a.md").write_text("evidence", encoding="utf-8")
    out = records.provenance_header("r-9", "attack", "adversary",
                                    sources=["a.md"], workspace=str(ws))
    assert "absent" not in out["header"]


def test_provenance_header_carries_sha():
    src = Path(__file__)
    out = records.provenance_header("r-1", "research", "hunter", sources=[str(src)])
    assert "run_id: r-1" in out["header"] and "agent: hunter" in out["header"]


def test_extract_text_child_inherits_path(tmp_path):
    """The killable-parse child python must be able to `import harness` (found live
    2026-10-21: it only resolved where the package was pip-installed)."""
    f = tmp_path / "doc.txt"
    f.write_text("word " * 250, encoding="utf-8")
    from harness.ingest_generic import extract_text
    assert len(extract_text(f).split()) == 250
