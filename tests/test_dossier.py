# tests/test_dossier.py — the M5 case-dossier self-check: eight append-only JSONL
# registers, the debrief prediction-vs-outcome diff, kernel-only deadlines, and the
# R-CL2 per-doc corpus delete/reingest — all offline (fake embeddings, no Ollama,
# no Claude, no network).
import sys
from datetime import date, timedelta
from pathlib import Path

import pytest

PLUGIN = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PLUGIN / "mcp"))

import server   # noqa: E402
import dossier  # noqa: E402


def fake1024(texts):                        # deterministic 1024-dim proxy (store dim)
    return [[float((ord(t[i % len(t) or 1]) + i) % 17) for i in range(1024)]
            for t in texts]


@pytest.fixture()
def ws(tmp_path):
    return tmp_path / "m-harbour-freight"


# ------------------------------------------------------------------ the registers

def test_append_and_read_roundtrip(ws):
    row = dossier.append("harbour-freight", "facts",
                         {"op": "set", "field": "debt", "value": "$126,000",
                          "source": "statement-of-claim.md"}, workspace=str(ws))
    assert row["ts"] and row["actor"] == "case-manager"
    out = dossier.read("harbour-freight", "facts", workspace=str(ws))
    assert out["count"] == 1 and out["events"][0]["value"] == "$126,000"


def test_all_eight_registers(ws):
    assert set(dossier.ENTITIES) == {"facts", "evidence", "strategy", "proposals",
                                     "predictions", "court_events", "deadlines",
                                     "outcomes"}
    for entity in dossier.ENTITIES:
        dossier.append("m", entity, {"x": 1}, workspace=str(ws))
        assert dossier.read("m", entity, workspace=str(ws))["count"] == 1


def test_bad_entity_refused(ws):
    # the flaw ledger is M6's register — it must not silently exist
    with pytest.raises(RuntimeError):
        dossier.append("m", "flaw_ledger", {}, workspace=str(ws))


def test_non_serialisable_event_refused(ws):
    with pytest.raises(RuntimeError):
        dossier.append("m", "facts", {"op": "set", "field": "f", "value": object()},
                       workspace=str(ws))


def test_colon_or_path_matter_refused(ws):
    for bad in ("bad:ref", "../escape", r"c:\temp", ""):
        with pytest.raises(RuntimeError):
            dossier.append(bad, "facts", {}, workspace=str(ws))


# ------------------------------------------------------------------- projections

def test_facts_projection_latest_per_field(ws):
    for v in ("$126,000", "$126,000 plus default interest"):
        dossier.append("m", "facts",
                       {"op": "set", "field": "debt", "value": v}, workspace=str(ws))
    out = dossier.read("m", "facts", workspace=str(ws))
    assert out["fields"]["debt"]["value"] == "$126,000 plus default interest"


def test_strategy_versions_and_latest(ws):
    for v in (1, 2):
        dossier.append("m", "strategy",
                       {"version": v, "file": f"strategy-v{v}.md", "why_changed": "x"},
                       workspace=str(ws))
    out = dossier.read("m", "strategy", workspace=str(ws))
    assert out["versions"] == [1, 2] and out["latest"]["version"] == 2


def test_deadline_status_projection(ws):
    today = date.today()
    for label, due in (("past", today - timedelta(days=10)),
                       ("soon", today + timedelta(days=2)),
                       ("far", today + timedelta(days=40))):
        dossier.append("m", "deadlines", {"what": label, "due": due.isoformat()},
                       workspace=str(ws))
    got = {d["what"]: d["status"]
           for d in dossier.read("m", "deadlines", workspace=str(ws))["deadlines"]}
    assert got == {"past": "overdue", "soon": "due_soon", "far": "ok"}


def test_predictions_unresolved_projection(ws):
    for pid, claim in (("p1", "x"), ("p2", "y")):
        dossier.append("m", "predictions",
                       {"prediction_id": pid, "claim": claim}, workspace=str(ws))
    dossier.append("m", "outcomes", {"prediction_id": "p2", "match": True},
                   workspace=str(ws))
    out = dossier.read("m", "predictions", workspace=str(ws))
    assert out["unresolved"] == ["p1"]


# ---------------------------------------------------------------- the debrief loop

def test_debrief_diff_pairs_unresolved_predictions(ws):
    for pid, claim in (("p1", "immediate payment of the whole debt"),
                       ("p2", "judgment for the claimant")):
        dossier.append("m", "predictions",
                       {"prediction_id": pid, "strategy_version": 1, "claim": claim},
                       workspace=str(ws))
    out = dossier.debrief("m", {"event_type": "hearing", "date": "2026-11-05",
                                "orders": ["payment within 20 working days"]},
                          workspace=str(ws))
    assert [d["prediction_id"] for d in out["diff"]] == ["p1", "p2"]
    assert out["court_event"]["date"] == "2026-11-05"
    # the case-manager resolves p1 as a miss; the next debrief pairs only p2
    dossier.append("m", "outcomes",
                   {"prediction_id": "p1", "match": False,
                    "actual": "payment in 20 working days, not immediate"},
                   workspace=str(ws))
    out2 = dossier.debrief("m", {"date": "2026-11-12"}, workspace=str(ws))
    assert [d["prediction_id"] for d in out2["diff"]] == ["p2"]


def test_debrief_requires_date(ws):
    with pytest.raises(RuntimeError):
        dossier.debrief("m", {"event_type": "hearing"}, workspace=str(ws))


# -------------------------------------------------------------- the MCP tool surface

def test_new_tool_surface():
    names = {t["name"] for t in server.TOOL_DEFS}
    assert {"ironfleet_dossier_append", "ironfleet_dossier_read",
            "ironfleet_deadline_register", "ironfleet_debrief_ingest",
            "ironfleet_delete_docs", "ironfleet_reingest"} <= names


def test_dossier_tools_dispatch(ws):
    server.dispatch("ironfleet_dossier_append",
                    {"matter": "m", "entity": "facts", "workspace": str(ws),
                     "event": {"op": "set", "field": "debt", "value": "126000"}})
    out = server.dispatch("ironfleet_dossier_read",
                          {"matter": "m", "entity": "facts", "workspace": str(ws)})
    assert out["fields"]["debt"]["value"] == "126000"
    with pytest.raises(RuntimeError):
        server.dispatch("ironfleet_dossier_append",
                        {"matter": "m", "entity": "nope", "workspace": str(ws),
                         "event": {}})


def test_deadline_register_refuses_model_supplied_due(tmp_path, monkeypatch):
    monkeypatch.setenv("HARNESS_HOME", str(tmp_path))
    with pytest.raises(RuntimeError):
        server.dispatch("ironfleet_deadline_register",
                        {"matter": "m", "what": "file submissions", "due": "2026-12-01",
                         "service_date": "2026-03-02", "days": 20})


def test_deadline_register_filing_kernel(tmp_path, monkeypatch):
    monkeypatch.setenv("HARNESS_HOME", str(tmp_path))
    out = server.dispatch("ironfleet_deadline_register",
                          {"matter": "m", "what": "file submissions",
                           "service_date": "2026-03-02", "days": 20})
    assert out["due"] == "2026-03-30"          # 20 working days from Mon 2 Mar 2026
    assert out["row"]["source"] == "kernel"
    got = dossier.read("m", "deadlines")["deadlines"]
    assert got[0]["what"] == "file submissions"
    assert got[0]["status"] == "overdue"       # today-relative: 2026-03 is long past


def test_deadline_register_statutory_demand_kernel(tmp_path, monkeypatch):
    monkeypatch.setenv("HARNESS_HOME", str(tmp_path))
    args = {"matter": "m", "what": "comply with statutory demand",
            "kind": "statutory_demand", "service_date": "2026-03-02",
            "amount": 22000, "debtor_company": "Harbour Freight Ltd",
            "creditor": "Powell Builders Ltd", "debt_details": "unpaid invoices"}
    out = server.dispatch("ironfleet_deadline_register", dict(args))
    kernel = server.dispatch("ironfleet_statutory_demand",
                             {k: v for k, v in args.items()
                              if k not in ("matter", "what", "kind")})
    assert out["due"] == str(kernel["compliance_deadline"])[:10]  # the kernel's answer


# ------------------------------------------------------- R-CL2 per-doc corpus CRUD

def test_delete_and_reingest_roundtrip(tmp_path, monkeypatch):
    monkeypatch.setenv("HARNESS_HOME", str(tmp_path))
    monkeypatch.setattr("harness.localstack.embed_fn", fake1024)
    doc = tmp_path / "memo.txt"
    doc.write_text("FREIGHT DEBT MEMO\n\nThe defendant owes $126,000 under the "
                   "supply agreement and default interest runs. " * 30,
                   encoding="utf-8")
    r1 = server.dispatch("ironfleet_ingest_docs", {"matter": "m", "path": str(doc)})
    assert r1["ingested"] == ["memo.txt"] and r1["chunks"] > 0

    # edit + reingest REPLACES (delete-by-name then ingest), never appends a twin
    doc.write_text("FREIGHT DEBT MEMO REVISED\n\nThe defendant owes $126,000 plus "
                   "default interest at 26 per cent per annum. " * 30,
                   encoding="utf-8")
    r2 = server.dispatch("ironfleet_reingest", {"matter": "m", "path": str(doc)})
    assert r2["replaced"] == ["memo.txt"] and r2["ingested"] == ["memo.txt"]
    docs = server.dispatch("ironfleet_list_docs", {"matter": "m"})["docs"]
    assert len(docs) == 1 and docs[0]["chunks"] == r2["chunks"]

    # delete by name: docs row, FTS chunks, cites and vectors all go; search stops
    r3 = server.dispatch("ironfleet_delete_docs", {"matter": "m", "name": "memo.txt"})
    assert r3["removed"] and r3["chunks"] == r2["chunks"] and r3["vectors"] > 0
    assert server.dispatch("ironfleet_list_docs", {"matter": "m"})["docs"] == []
    out = server.dispatch("ironfleet_corpus_search",
                          {"matter": "m", "query": "freight debt memo", "rerank": False})
    assert out["passages"] == []

    # unknown doc: loud, honest envelope
    r4 = server.dispatch("ironfleet_delete_docs", {"matter": "m", "doc_id": "doc-nope"})
    assert r4["removed"] == [] and "no matching doc" in r4["error"]
