# tests/test_disclosure.py — G4: the certification block must be self-consistent
# with the trace: a stage is listed only if a stage_end event shows it; verify
# verdicts and corpus refs render only from logged tool_result/exception events.
# Offline, no services, no embeddings.
import sys
from pathlib import Path

PLUGIN = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PLUGIN / "mcp"))

import records  # noqa: E402


def _run_with_trace(tmp_path):
    ws = tmp_path / "ws"
    r = records.begin_run("m-g4", "can I win?", workspace=str(ws),
                          stages=["intake", "filings", "verify"])
    rid = r["run_id"]
    records.log(rid, "stage_start", {"stage": "intake", "agent": "ingestor"},
                workspace=str(ws))
    records.log(rid, "stage_end", {"stage": "intake", "file": "case-summary.md",
                                   "digest": "facts extracted"}, workspace=str(ws))
    records.log(rid, "tool_result",
                {"tool": "ironfleet_verify_document", "path": "advice-letter.md",
                 "ok": True, "summary": {"verified": 2, "corrected": 0, "ungrounded": 0},
                 "refs": [{"ref": "[E1.S1]", "verdict": "VERIFIED"},
                          {"ref": "[E2.S3]", "verdict": "VERIFIED"}]},
                workspace=str(ws))
    records.log(rid, "exception", {"ref": "[NOT IN CORPUS]", "quote": "x",
                                   "ruling": "designed honesty marker"},
                workspace=str(ws))
    return rid, ws


def test_block_lists_only_trace_evidenced_stages(tmp_path):
    rid, ws = _run_with_trace(tmp_path)
    b = records.disclosure_block(rid, workspace=str(ws))["block"]
    assert "case-summary.md" in b and "ingestor" in b     # the ended stage, with agent
    # declared but never ended: flagged, never silently omitted (self-consistency)
    assert "no stage_end event" in b and "\n- filings" in b and "\n- verify" in b
    # verdicts + refs render only from logged events
    assert "ok=True" in b and "[E1.S1]" in b and "[NOT IN CORPUS]" in b
    assert "ironfleet_verify_document" in b
    assert "No AI system made any decision or filing" in b
    assert "Certified by:" in b


def test_unended_run_block_stays_honest(tmp_path):
    ws = tmp_path / "ws2"
    r = records.begin_run("m-g4b", "p", workspace=str(ws), stages=["a"])
    b = records.disclosure_block(r["run_id"], workspace=str(ws))["block"]
    assert "none recorded" in b and "no stage_end event" in b
