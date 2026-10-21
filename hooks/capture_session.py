# hooks/capture_session.py — PostToolUse on ironfleet_begin_run: patch run.json with the
# native session_id + transcript_path so every run replays in full (`claude --resume <id>`).
# Reads the hook envelope (JSON on stdin); NEVER blocks (exit 0 always) — a missed capture
# degrades to "not captured" in run.json, which run.json states honestly.
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "mcp"))
import records  # noqa: E402


def main() -> None:
    try:
        data = json.loads(sys.stdin.read() or "{}")
        ti = data.get("tool_input") or {}
        run_id = None
        content = ((data.get("tool_response") or {}).get("content") or [{}])[0].get("text", "")
        if content:
            run_id = json.loads(content).get("run_id")
        if run_id and data.get("session_id"):
            records.attach_session(run_id, data["session_id"],
                                   data.get("transcript_path", ""),
                                   matter=ti.get("matter", ""),
                                   workspace=ti.get("workspace"))
    except Exception:                                  # noqa: BLE001 — ledger never blocks
        pass
    print("{}")


if __name__ == "__main__":
    main()
