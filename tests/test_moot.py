# tests/test_moot.py — M6 self-check: the flaw ledger (dossier register #9), the
# keep-if-better comparator, the moot_check deterministic pre-pass (objection +
# citator + exhibit + form checks), and the seeded-flaw scorer — all offline
# (fake embeddings, no Ollama, no Claude, no network).
import sys
from pathlib import Path

import pytest

PLUGIN = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PLUGIN / "mcp"))

import server   # noqa: E402
import dossier  # noqa: E402
import moot     # noqa: E402
from harness.moot_checks import check, exhibit_rows, form_rows  # noqa: E402


def fake1024(texts):
    return [[float((ord(t[i % len(t) or 1]) + i) % 17) for i in range(1024)]
            for t in texts]


_LAW_PARA = (
    "The Companies Act 1993 governs statutory demands in New Zealand. A company "
    "that fails to comply with a statutory demand within 15 working days is deemed "
    "unable to pay its debts. The prescribed minimum amount for a statutory demand "
    "is $1,000. Service must be effected before the compliance period begins to "
    "run.\n\n")
# the ingest gate skips docs under 200 words — repeat the same five sentences
# (verbatim, so quotes can still be located) until the corpus clears the gate
LAW_TEXT = "POWELL BUILDERS LAW MEMO\n\n" + _LAW_PARA * 5


@pytest.fixture()
def store_env(tmp_path, monkeypatch):
    monkeypatch.setenv("HARNESS_HOME", str(tmp_path))
    monkeypatch.setattr("harness.localstack.embed_fn", fake1024)
    law = tmp_path / "law-memo.md"
    law.write_text(LAW_TEXT, encoding="utf-8")
    r = server.dispatch("ironfleet_ingest_docs", {"matter": "m", "path": str(law)})
    assert r["chunks"] > 0, f"corpus did not chunk: {r}"
    return tmp_path


def draft(tmp_path, name, text):
    p = tmp_path / name
    p.write_text(text, encoding="utf-8")
    return str(p)


@pytest.fixture()
def ws(tmp_path):
    return tmp_path / "m-ws"


# ------------------------------------------------------- register #9: the flaw ledger

def test_nine_register_set():
    assert "flaws" in dossier.ENTITIES and len(dossier.ENTITIES) == 9


def test_flaw_ledger_open_projection(ws):
    dossier.append("m", "flaws", {"flaw_id": "F1", "class": "misquote",
                                  "severity": "critical", "doc": "advice.md",
                                  "status": "open"}, workspace=str(ws))
    out = dossier.read("m", "flaws", workspace=str(ws))
    assert out["open_counts"] == {"critical": 1, "material": 0, "minor": 0}
    assert out["gate_blocked"] is True
    # last status wins: F1 fixed -> no longer open, history intact
    dossier.append("m", "flaws", {"flaw_id": "F1", "class": "misquote",
                                  "severity": "critical", "doc": "advice.md",
                                  "status": "fixed"}, workspace=str(ws))
    out2 = dossier.read("m", "flaws", workspace=str(ws))
    assert out2["open_counts"]["critical"] == 0 and out2["gate_blocked"] is False
    assert out2["count"] == 2


def test_flaw_ledger_minor_never_blocks(ws):
    dossier.append("m", "flaws", {"flaw_id": "F9", "class": "citator_later",
                                  "severity": "minor", "doc": "advice.md",
                                  "status": "open"}, workspace=str(ws))
    assert dossier.read("m", "flaws", workspace=str(ws))["gate_blocked"] is False


# ------------------------------------------------------------ keep-if-better (S7i bar)

def test_compare_truth_table():
    good = moot.compare({"critical": 2, "material": 1, "minor": 3},
                        {"critical": 1, "material": 1, "minor": 3})
    assert good["keep"] is True and good["verdict"] == "KEEP"
    tie = moot.compare({"critical": 1, "material": 1, "minor": 1},
                       {"critical": 1, "material": 1, "minor": 1})
    assert tie["keep"] is False and tie["verdict"] == "ROLLBACK"
    worse = moot.compare({"critical": 1, "material": 0, "minor": 0},
                         {"critical": 1, "material": 1, "minor": 0})
    assert worse["keep"] is False and worse["verdict"] == "ROLLBACK"
    new_crit = moot.compare({"critical": 0, "material": 0, "minor": 0},
                            {"critical": 1, "material": 0, "minor": 0})
    assert new_crit["keep"] is False and "critical" in new_crit["reason"]


def test_compare_refuses_unusable_leg():
    out = moot.compare({"critical": 1}, {"critical": 1, "material": 0, "minor": 0})
    assert out["keep"] is False and out["verdict"] == "REFUSED"


# ------------------------------------------------------- the pure checks (moot_checks)

def test_exhibit_rows_match_registered_labels():
    text = "As per Exhibit A and exhibit \"B\" the goods were delivered; see [Exhibit 3]."
    labels = {"a", "b", "3"}
    assert exhibit_rows(text, labels) == []
    rows = exhibit_rows(text, {"a", "b"})
    assert len(rows) == 1 and rows[0]["class"] == "missing_exhibit" and "3" in rows[0]["detail"]


def test_exhibit_rows_none_when_no_refs():
    assert exhibit_rows("No exhibits cited here.", set()) == []


def test_form_rows_kernel_invalid_amount():
    rows = form_rows("The statutory demand required payment of $950 within 15 "
                     "working days of service.")
    assert len(rows) == 1 and rows[0]["class"] == "wrong_form"
    assert "$950" in rows[0]["detail"]


def test_form_rows_kernel_invalid_period():
    rows = form_rows("The statutory demand required payment within 14 working days "
                     "of service.")
    assert len(rows) == 1 and rows[0]["class"] == "wrong_form"
    assert "14" in rows[0]["detail"]


def test_form_rows_clean_demand_passes():
    assert form_rows("The statutory demand required payment of $22,000 within 15 "
                     "working days of service.") == []


def test_form_rows_ignores_amounts_outside_demand_context():
    assert form_rows("The debt of $500 remains unpaid; interest runs daily.") == []


def test_combined_check():
    text = ("The statutory demand sought $500. See Exhibit C for the ledger. "
            "Exhibit A is the contract.")
    rows = check(text, {"a"})
    classes = {r["class"] for r in rows}
    assert classes == {"wrong_form", "missing_exhibit"}


# --------------------------------------------------------- the integrated moot_check

def test_moot_check_cleans_draft(store_env, tmp_path):
    p = draft(tmp_path, "clean.md",
              'As the memo states, "A company that fails to comply with a statutory '
              'demand within 15 working days is deemed unable to pay its debts." '
              "[E1.S1] The compliance period runs from service.")
    out = moot.moot_check("m", p, workspace=str(store_env))
    assert out["ok"] is True, out
    assert [r for r in out["flaws"] if r["severity"] != "minor"] == []


def test_moot_check_misquote_detected(store_env, tmp_path):
    p = draft(tmp_path, "misquote.md",
              'Per the memo, "A company that fails to comply with a statutory demand '
              'within 14 calendar days is deemed insolvent." [E1.S1]')
    out = moot.moot_check("m", p, workspace=str(store_env))
    assert out["ok"] is False
    assert any(r["class"] == "misquote" for r in out["flaws"])


def test_moot_check_fabricated_ref_detected(store_env, tmp_path):
    p = draft(tmp_path, "fabricated.md",
              "Zealand Holdings Ltd v Meridian Farms [2019] NZHC 999 establishes "
              "the point. [E9.S9]")
    out = moot.moot_check("m", p, workspace=str(store_env))
    assert out["ok"] is False
    assert any(r["class"] == "fabricated_case" for r in out["flaws"])


def test_moot_check_wrong_deadline_detected(store_env, tmp_path, monkeypatch):
    run = server.dispatch("ironfleet_begin_run",
                          {"matter": "m", "prompt": "x", "workspace": str(store_env)})
    server.dispatch("ironfleet_log_event",
                    {"run_id": run["run_id"], "event": "tool_result",
                     "payload": {"tool": "ironfleet_filing_deadline",
                                 "deadline": "2026-03-30", "days": 20,
                                 "service_date": "2026-03-02"},
                     "matter": "m", "workspace": str(store_env)})
    p = draft(tmp_path, "late.md",
              "Powell Builders must file no later than 6 April 2026 (deadline).")
    out = moot.moot_check("m", p, run_id=run["run_id"], workspace=str(store_env))
    assert out["ok"] is False
    assert any(r["class"] == "wrong_deadline" for r in out["flaws"])


def test_moot_check_missing_exhibit_detected(store_env, tmp_path):
    for label in ("Exhibit A", "Exhibit B"):
        dossier.append("m", "evidence", {"op": "add", "label": label,
                                         "file": f"{label}.pdf"}, workspace=str(store_env))
    p = draft(tmp_path, "exhibits.md",
              'The contract is Exhibit A; the ledger is Exhibit C. "Service must be '
              'effected before the compliance period begins to run." [E1.S1]')
    out = moot.moot_check("m", p, workspace=str(store_env))
    assert any(r["class"] == "missing_exhibit" and "C" in r["detail"]
               for r in out["flaws"])


def test_moot_check_wrong_form_detected(store_env, tmp_path):
    p = draft(tmp_path, "form.md",
              "The statutory demand required payment of $950. See the memo on the "
              "prescribed minimum.")
    out = moot.moot_check("m", p, workspace=str(store_env))
    assert any(r["class"] == "wrong_form" for r in out["flaws"])


def test_moot_check_unreadable_draft_is_loud(store_env, tmp_path):
    out = moot.moot_check("m", str(tmp_path / "nope.md"), workspace=str(store_env))
    assert out["ok"] is False and "error" in out


# ------------------------------------------------------------- the scorer (eval B5)

def test_score_rates_detection_and_flags_false_positives():
    manifest = {"docs": [
        {"file": "a.md", "class": "misquote", "severity": "critical"},
        {"file": "b.md", "class": "wrong_form", "severity": "critical"},
        {"file": "c.md", "class": "clean", "severity": None}]}
    results = {"a.md": {"flaws": [{"class": "misquote", "severity": "critical"}]},
               "b.md": {"flaws": [{"class": "missing_exhibit", "severity": "critical"}]},
               "c.md": {"flaws": [{"class": "citator_later", "severity": "minor"}]}}
    out = moot.score(manifest, results)
    assert out["per_class"]["misquote"]["detected"] == 1
    assert out["per_class"]["wrong_form"]["detected"] == 0
    assert out["overall"]["detected"] == 1 and out["overall"]["rate"] == pytest.approx(1 / 2)
    assert out["controls"]["false_positives"] == 0   # minor rows on controls are noise, not FP
    results["c.md"]["flaws"].append({"class": "misquote", "severity": "critical"})
    assert moot.score(manifest, results)["controls"]["false_positives"] == 1
    assert moot.score(manifest, results)["meets_bar"] is False


# ------------------------------------------------------------ the MCP tool surface

def test_new_tools_surface():
    names = {t["name"] for t in server.TOOL_DEFS}
    assert {"ironfleet_flaw_ledger", "ironfleet_moot_check"} <= names


def test_flaw_ledger_dispatch(ws):
    server.dispatch("ironfleet_flaw_ledger",
                    {"matter": "m", "op": "append", "workspace": str(ws),
                     "flaw": {"flaw_id": "F2", "class": "wrong_deadline",
                              "severity": "material", "doc": "advice.md",
                              "status": "open"}})
    out = server.dispatch("ironfleet_flaw_ledger",
                          {"matter": "m", "op": "read", "workspace": str(ws)})
    assert out["open_counts"]["material"] == 1
    cmp = server.dispatch("ironfleet_flaw_ledger",
                          {"matter": "m", "op": "compare",
                           "baseline": {"critical": 1, "material": 1, "minor": 0},
                           "candidate": {"critical": 0, "material": 1, "minor": 0}})
    assert cmp["keep"] is True


def test_flaw_ledger_validates_severity_and_class(ws):
    with pytest.raises(RuntimeError):
        server.dispatch("ironfleet_flaw_ledger",
                        {"matter": "m", "op": "append", "workspace": str(ws),
                         "flaw": {"flaw_id": "F3", "class": "wrong_form",
                                  "severity": "huge", "doc": "x.md", "status": "open"}})
    with pytest.raises(RuntimeError):
        server.dispatch("ironfleet_flaw_ledger",
                        {"matter": "m", "op": "append", "workspace": str(ws),
                         "flaw": {"flaw_id": "F4", "class": "", "severity": "minor",
                                  "doc": "x.md", "status": "open"}})
