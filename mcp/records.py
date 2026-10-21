# mcp/records.py — the runs/ ledger (R-CL4 re-hosted as files, plan P1: structural).
# Every run leaves a complete, human-openable paper trail in the matter workspace:
#   runs/<date>-<run-id>/run.json     — prompt, stages, agents, session id, status
#   runs/<date>-<run-id>/trace.jsonl  — append-only events (stage/tool/file/guard/error)
#   runs/<date>-<run-id>/RECORD.md    — the human report
# Everything on the user's machine, nothing in the plugin dir (updates must not eat data).
from __future__ import annotations

import hashlib
import json
import os
import re
import secrets
from datetime import datetime, timezone
from pathlib import Path

from harness.paths import resolve_store_root


def runs_root(matter: str, workspace: str | None = None) -> Path:
    """The matter workspace when given, else the store root — never the plugin dir."""
    if workspace:
        return Path(workspace) / "runs"
    root, _source = resolve_store_root()
    return Path(root) / "runs" / re.sub(r"[^A-Za-z0-9_-]", "_", matter)


def _run_dir(runs: Path, run_id: str) -> Path:
    d = runs / run_id
    d.mkdir(parents=True, exist_ok=True)
    return d


def begin_run(matter: str, prompt: str, workspace: str | None = None,
              stages: list[str] | None = None) -> dict:
    run_id = f"{datetime.now().strftime('%Y%m%d')}-{secrets.token_hex(3)}"
    d = _run_dir(runs_root(matter, workspace), run_id)
    (d / "trace.jsonl").write_text("", encoding="utf-8")
    run = {"run_id": run_id, "matter": matter, "prompt": prompt,
           "started": datetime.now(timezone.utc).isoformat(),
           "status": "running", "stages": stages or [], "agents": [],
           "session_id": None, "transcript_path": None,
           "checkpoints": [], "deliverables": []}
    (d / "run.json").write_text(json.dumps(run, indent=2), encoding="utf-8")
    log(run_id, "run_started", {"matter": matter}, d=d)
    return {"run_id": run_id, "run_dir": str(d)}


def _find(runs: Path, run_id: str) -> Path:
    d = runs / run_id
    if not (d / "run.json").exists():
        raise RuntimeError(f"unknown run_id {run_id} (no run.json under {runs})")
    return d


def log(run_id: str, event: str, payload: dict | None = None,
        matter: str = "", workspace: str | None = None, d: Path | None = None) -> dict:
    """Append one trace event. Safe against a missing run: an error dict, never a raise —
    a broken ledger must not break the legal work."""
    try:
        d = d or _find(runs_root(matter, workspace), run_id)
        line = {"ts": datetime.now(timezone.utc).isoformat(), "event": event,
                **(payload or {})}
        with (d / "trace.jsonl").open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(line, ensure_ascii=False) + "\n")
        return {"ok": True}
    except Exception as ex:                                # noqa: BLE001 — ledger never blocks
        return {"ok": False, "error": str(ex)}


def attach_session(run_id: str, session_id: str, transcript_path: str,
                   matter: str = "", workspace: str | None = None) -> dict:
    """Patch run.json with the native session identity (the PreToolUse hook calls this
    at the run's first tool call — the full-transcript replay link, captured at start)."""
    d = _find(runs_root(matter, workspace), run_id)
    run = json.loads((d / "run.json").read_text(encoding="utf-8"))
    run["session_id"] = session_id
    run["transcript_path"] = transcript_path
    (d / "run.json").write_text(json.dumps(run, indent=2), encoding="utf-8")
    return {"ok": True}


def checkpoint(run_id: str, question: str, answer: str,
               matter: str = "", workspace: str | None = None) -> dict:
    d = _find(runs_root(matter, workspace), run_id)
    run = json.loads((d / "run.json").read_text(encoding="utf-8"))
    run["checkpoints"].append({"question": question, "answer": answer})
    (d / "run.json").write_text(json.dumps(run, indent=2), encoding="utf-8")
    log(run_id, "checkpoint", {"question": question[:200]}, d=d)
    return {"ok": True}


def finish_run(run_id: str, status: str, deliverables: list[str] | None = None,
               summary: str = "", matter: str = "", workspace: str | None = None) -> dict:
    d = _find(runs_root(matter, workspace), run_id)
    run = json.loads((d / "run.json").read_text(encoding="utf-8"))
    run["status"] = status
    run["ended"] = datetime.now(timezone.utc).isoformat()
    run["deliverables"] = deliverables or []
    (d / "run.json").write_text(json.dumps(run, indent=2), encoding="utf-8")
    log(run_id, "run_finished", {"status": status}, d=d)

    links = "\n".join(f"- [{Path(p).name}]({Path(p).name})" for p in run["deliverables"])
    record = f"""# Run {run_id} — {run['matter']}

**Asked:** {run['prompt']}

**Status:** {status} · started {run['started']} · ended {run.get('ended', '')}
**Session:** `{run.get('session_id') or 'not captured'}` (replay: `claude --resume <id>`)

## Deliverables
{links or '- (none recorded)'}

## Assumptions & checkpoints
{chr(10).join('- ' + c['question'][:160] for c in run['checkpoints']) or '- none'}

## How to continue
Type a follow-up in the same session, or open `trace.jsonl` beside this file for the
full event log. Debug ladder: RECORD.md -> trace.jsonl -> the Claude session transcript.
"""
    (d / "RECORD.md").write_text(record, encoding="utf-8")
    return {"ok": True, "record": str(d / "RECORD.md")}


def provenance_header(run_id: str, stage: str, agent: str, model: str = "claude",
                      sources: list[str] | None = None, corpus_refs: list[str] | None = None,
                      matter: str = "", workspace: str | None = None) -> dict:
    """The front-matter block every deliverable carries — 'where did this come from'
    without opening a database. Sources are hashed so the chain is checkable."""
    def _sha(p: str) -> str:
        try:
            return hashlib.sha256(Path(p).read_bytes()).hexdigest()[:16]
        except OSError:
            return "absent"
    rows = "\n".join(f"  - path: {s}{chr(10)}    sha256_16: {_sha(s)}"
                     for s in (sources or [])) or "  - (none)"
    refs = "\n".join(f"  - {r}" for r in (corpus_refs or [])) or "  - (none)"
    return {"header": (
        "---\n"
        f"run_id: {run_id}\nstage: {stage}\nagent: {agent}\nmodel: {model}\n"
        f"date: {datetime.now(timezone.utc).isoformat()}\nsources:\n{rows}\n"
        f"corpus_refs:\n{refs}\n---\n")}
