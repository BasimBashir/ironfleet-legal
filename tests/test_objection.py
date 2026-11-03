# tests/test_objection.py — G5: the adversary's three failure modes as a tool.
# Offline: real CorpusStore + fake embedder (verify is FTS-only), run ledger on the
# same tmp workspace — no Ollama, no network. Kernel checks read the tool_result
# events stage 6 logs; MISMATCH reads the evidence event the house rules mandate.
import sys
from pathlib import Path

import pytest

PLUGIN = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PLUGIN / "mcp"))

import records  # noqa: E402
from harness.corpus import CorpusStore, DocRecord, chunk_text  # noqa: E402
from harness.objection import objection  # noqa: E402

BODY = ("Harbour Freight Solutions Ltd agreed to pay default interest at the rate of "
        "twenty-six per cent per annum on all overdue amounts. The plaintiff delivered "
        "goods under the contract. The seller would deliver the equipment in two "
        "instalments during 2019.")
SOURCE = "THE SUPPLY AGREEMENT TERMS\n\n" + BODY
WS = "ws"


@pytest.fixture(autouse=True)
def _home(tmp_path, monkeypatch):
    monkeypatch.setenv("HARNESS_HOME", str(tmp_path))   # records' .index stays in tmp


@pytest.fixture
def store(tmp_path):
    def fake_embed(texts):
        return [[float(ord(c) % 17) for c in t[:8].ljust(8, "x")] for t in texts]

    s = CorpusStore(tmp_path / "corpus.sqlite3")          # FTS-only, like verify
    embedded = chunk_text("doc-a", SOURCE)
    s.ingest("harbour-freight", DocRecord("doc-a", SOURCE, "supply-agreement.md"),
             vectors=fake_embed(embedded), model="fake", provider="test")
    return s


def _draft(tmp_path, body: str) -> str:
    p = tmp_path / "draft.md"
    p.write_text(body, encoding="utf-8")
    return str(p)


def _run(tmp_path, events: list[tuple]) -> str:
    ws = str(tmp_path / WS)
    r = records.begin_run("harbour-freight", "p", workspace=ws)
    for event, payload in events:
        records.log(r["run_id"], event, payload, workspace=ws)
    return r["run_id"]


def _obj(store, tmp_path, body, run_id=None):
    return objection("harbour-freight", _draft(tmp_path, body), run_id=run_id,
                     workspace=str(tmp_path / WS), store=store)


def test_clean_draft_without_a_run_is_ok(store, tmp_path):
    out = _obj(store, tmp_path,
               'The agreement says "default interest at the rate of twenty-six per '
               'cent per annum on all overdue amounts" [E1.S1].')
    assert out["ok"] is True and out["objections"] == []
    assert out["kernel"] == {"computations": 0, "deadlines_matched": 0,
                             "note": "no run_id — kernel checks skipped"}


def test_fabricated_quote_and_authority_are_objected(store, tmp_path):
    out = _obj(store, tmp_path,
               'In *Kaikoura Freight v Reed* the court held that "a seller may '
               'recover punitive damages where the buyer repudiates without '
               'cause" [E1.S2].')
    assert out["ok"] is False
    assert out["summary"] == {"authority_not_in_corpus": 1, "quote_not_in_corpus": 1,
                              "date_not_matching_kernel": 0}
    kinds = {o["kind"] for o in out["objections"]}
    assert kinds == {"quote_not_in_corpus", "authority_not_in_corpus"}


def test_kernel_deadline_stated_prose_matches(store, tmp_path):
    rid = _run(tmp_path, [("tool_result", {"tool": "ironfleet_filing_deadline",
                                           "service_date": "2026-03-02", "days": 15,
                                           "deadline": "2026-03-23"})])
    out = _obj(store, tmp_path,
               "The filing deadline is 23 March 2026.", run_id=rid)
    assert out["kernel"]["computations"] == 1
    assert out["kernel"]["deadlines_matched"] == 1
    assert out["ok"] is True and out["objections"] == []


def test_wrong_deadline_date_is_caught_both_ways(store, tmp_path):
    """The kernel computed 23 March; the draft says 30 March — the computed date is
    MISSING and the asserted date matches no computation."""
    rid = _run(tmp_path, [("tool_result", {"tool": "ironfleet_filing_deadline",
                                           "service_date": "2026-03-02", "days": 15,
                                           "deadline": "2026-03-23"})])
    out = _obj(store, tmp_path,
               "The filing deadline is 30 March 2026.", run_id=rid)
    assert out["ok"] is False
    assert out["summary"]["date_not_matching_kernel"] == 2
    assert any("never states it" in o["detail"] for o in out["objections"])
    assert any("asserts 2026-03-30" in o["detail"] for o in out["objections"])


def test_service_date_is_a_fact_not_an_objection(store, tmp_path):
    rid = _run(tmp_path, [("tool_result", {"tool": "ironfleet_filing_deadline",
                                           "service_date": "2026-03-02", "days": 15,
                                           "deadline": "2026-03-23"})])
    out = _obj(store, tmp_path,
               "Served 2 March 2026. The filing deadline is 23 March 2026.",
               run_id=rid)
    assert out["ok"] is True and out["objections"] == []


def test_period_not_matching_the_kernel_is_objected(store, tmp_path):
    rid = _run(tmp_path, [("tool_result", {
        "tool": "ironfleet_statutory_demand", "service_date": "2026-03-02",
        "compliance_period_days": 15,
        "compliance_deadline": "2026-03-23"})])
    out = _obj(store, tmp_path,
               "The company must comply with the demand within 10 working days "
               "(by 23 March 2026).", run_id=rid)
    assert out["ok"] is False
    assert out["summary"]["date_not_matching_kernel"] == 1
    assert "10 working days" in out["objections"][0]["detail"]


def test_dates_outside_deadline_context_are_facts(store, tmp_path):
    """A fact date on a plain line is the adversary's business, not the tool's."""
    rid = _run(tmp_path, [("tool_result", {"tool": "ironfleet_filing_deadline",
                                           "service_date": "2026-03-02", "days": 15,
                                           "deadline": "2026-03-23"})])
    out = _obj(store, tmp_path,
               "The breach occurred on 12 February 2026 and goods were delivered "
               "on 14/02/2026.", run_id=rid)
    assert out["ok"] is True and out["objections"] == []


def test_evidence_table_pins_a_ref_without_a_quote(store, tmp_path):
    rid = _run(tmp_path, [("evidence", {"table": {
        "[E1.S1]": "The plaintiff delivered goods under the contract."}})])
    out = _obj(store, tmp_path, "Performance was complete [E1.S1].", run_id=rid)
    assert out["ok"] is True
    assert out["refs"][0]["verdict"] == "VERIFIED"
    assert out["refs"][0]["found_in"] == "supply-agreement.md"


def test_quote_contradicting_the_evidence_table_is_a_mismatch(store, tmp_path):
    """The G1-deferred verdict: the ref resolves to a pinned sentence the draft
    does not quote."""
    rid = _run(tmp_path, [("evidence", {"table": {
        "[E1.S1]": "The plaintiff delivered goods under the contract."}})])
    out = _obj(store, tmp_path,
               'The defendant argued "a seller may recover punitive damages where '
               'the buyer repudiates without cause" [E1.S1].', run_id=rid)
    assert out["refs"][0]["verdict"] == "MISMATCH"
    assert out["ok"] is False
    assert out["summary"]["authority_not_in_corpus"] == 1


def test_evidence_sentence_not_in_corpus_is_loud(store, tmp_path):
    rid = _run(tmp_path, [("evidence", {"table": {
        "[E1.S1]": "A sentence no ingested document ever contained at all."}})])
    out = _obj(store, tmp_path, "Performance was complete [E1.S1].", run_id=rid)
    assert out["refs"][0]["verdict"] == "NOT_IN_CORPUS"
    assert "nowhere in this corpus" in out["refs"][0]["pinned"]
    assert out["ok"] is False


def test_run_without_kernel_computations_notes_it(store, tmp_path):
    rid = _run(tmp_path, [])
    out = _obj(store, tmp_path, "The filing deadline is 23 March 2026.", run_id=rid)
    assert out["kernel"]["computations"] == 0
    assert "no kernel computations logged" in out["kernel"]["note"]
    assert out["ok"] is True


def test_missing_deliverable_is_loud(store, tmp_path):
    out = objection("harbour-freight", str(tmp_path / "nope.md"), store=store)
    assert out["ok"] is False and "not found" in out["error"]
