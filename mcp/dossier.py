# mcp/dossier.py — the case dossier (M5 prototype): eight append-only JSONL registers
# in the matter workspace (or the store root), one event per line — the trace.jsonl
# pattern. No read-modify-write anywhere: state is the last matching line, projections
# are computed at read. Everything here is mechanical and local; the model's judgement
# arrives as DATA (an outcomes row, a strategy version), never as a computed date —
# due dates come from the kernels inside ironfleet_deadline_register, never from here.
from __future__ import annotations

import json
import re
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

from harness.paths import resolve_store_root

ENTITIES = {
    "facts": "facts.jsonl",
    "evidence": "evidence.jsonl",
    "strategy": "strategy.jsonl",
    "proposals": "proposals.jsonl",
    "predictions": "predictions.jsonl",
    "court_events": "court-events.jsonl",
    "deadlines": "deadlines.jsonl",
    "outcomes": "outcomes.jsonl",
}
# the flaw ledger is deliberately absent — that register belongs to M6's moot gate

_DUE_SOON_DAYS = 7


def dossier_root(matter: str, workspace: str | None = None) -> Path:
    """The matter workspace when given, else the store root — never the plugin dir
    (the runs_root rule: plugin updates must not eat case data)."""
    if workspace:
        return Path(workspace) / "dossier"
    root, _source = resolve_store_root()
    return Path(root) / "dossier" / re.sub(r"[^A-Za-z0-9_-]", "_", matter)


def _matter(matter: str) -> str:
    if (not isinstance(matter, str) or not matter or ":" in matter
            or "/" in matter or "\\" in matter):
        raise RuntimeError(f"matter ref must be a non-empty colon-free, path-free "
                           f"ref (e.g. harbour-freight), got {matter!r}")
    return matter


def _entity(entity: str) -> str:
    fname = ENTITIES.get(entity)
    if fname is None:
        raise RuntimeError(f"unknown dossier entity {entity!r} "
                           f"(one of: {', '.join(sorted(ENTITIES))})")
    return fname


def append(matter: str, entity: str, event: dict, workspace: str | None = None,
           actor: str = "case-manager") -> dict:
    """Append one event to one register. Validation at the tool boundary: a bad
    entity or a non-serialisable event fails HERE, loudly — never mid-write, never
    as a torn line."""
    m = _matter(matter)
    fname = _entity(entity)
    if not isinstance(event, dict):
        raise RuntimeError("event must be a JSON object")
    try:
        json.dumps(event)
    except (TypeError, ValueError) as ex:
        raise RuntimeError(f"event is not JSON-serialisable: {ex}") from None
    row = {"ts": datetime.now(timezone.utc).isoformat(), "actor": actor, **event}
    d = dossier_root(m, workspace)
    d.mkdir(parents=True, exist_ok=True)
    with (d / fname).open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(row, ensure_ascii=False) + "\n")
    return row


def _events(d: Path, fname: str) -> list[dict]:
    f = d / fname
    if not f.exists():
        return []
    out = []
    for line in f.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            e = json.loads(line)
        except ValueError:
            continue                       # a torn/corrupt line is skipped, never fatal
        if isinstance(e, dict):
            out.append(e)
    return out


def _deadline_status(due, today: date) -> str:
    try:
        d = date.fromisoformat(str(due))
    except (TypeError, ValueError):
        return "unknown"
    if d < today:
        return "overdue"
    if d <= today + timedelta(days=_DUE_SOON_DAYS):
        return "due_soon"
    return "ok"


def read(matter: str, entity: str, workspace: str | None = None) -> dict:
    """All events of one register plus its mechanical projection: facts → latest
    value per field; strategy → version chain + latest; deadlines → today-relative
    status; predictions → those without an outcomes row yet."""
    m = _matter(matter)
    fname = _entity(entity)
    d = dossier_root(m, workspace)
    events = _events(d, fname)
    out: dict = {"matter": m, "entity": entity, "count": len(events), "events": events}
    if entity == "facts":
        fields: dict[str, dict] = {}
        for e in events:
            if e.get("op") == "set" and e.get("field"):
                fields[str(e["field"])] = e
        out["fields"] = fields
    elif entity == "strategy":
        versions = [e for e in events if isinstance(e.get("version"), int)]
        versions.sort(key=lambda e: e["version"])
        out["versions"] = [e["version"] for e in versions]
        out["latest"] = versions[-1] if versions else None
    elif entity == "deadlines":
        today = date.today()
        out["today"] = today.isoformat()
        out["deadlines"] = [dict(e, status=_deadline_status(e.get("due"), today))
                            for e in events]
    elif entity == "predictions":
        resolved = {e.get("prediction_id")
                    for e in _events(d, ENTITIES["outcomes"])}
        out["unresolved"] = [e.get("prediction_id") for e in events
                             if e.get("prediction_id") not in resolved]
    return out


def debrief(matter: str, event: dict, workspace: str | None = None,
            actor: str = "case-manager") -> dict:
    """Ingest one court event and mechanically assemble the prediction-vs-outcome
    diff: every prediction without an outcomes row, side by side with what the court
    actually said. Whether a prediction MATCHED is judgement — the caller (the
    case-manager) records it as an outcomes row; this only pairs and displays."""
    m = _matter(matter)
    if not isinstance(event, dict) or not event.get("date"):
        raise RuntimeError("court event needs a `date` (YYYY-MM-DD) — it anchors the "
                           "prediction diff and the outcome log")
    row = append(m, "court_events", event, workspace=workspace, actor=actor)
    resolved = {e.get("prediction_id")
                for e in read(m, "outcomes", workspace=workspace)["events"]}
    diff = [{"prediction_id": e.get("prediction_id"),
             "strategy_version": e.get("strategy_version"),
             "claim": e.get("claim"),
             "court_said": {"event_type": event.get("event_type", "hearing"),
                            "date": event.get("date"),
                            "judge_said": event.get("judge_said", ""),
                            "orders": event.get("orders", [])}}
            for e in read(m, "predictions", workspace=workspace)["events"]
            if e.get("prediction_id") not in resolved]
    return {"court_event": row, "diff": diff, "open_count": len(diff),
            "note": "record one outcomes row per diff entry (match true/false, "
                    "actual) via ironfleet_dossier_append entity=outcomes, then "
                    "have the strategist cut strategy vN+1"}
