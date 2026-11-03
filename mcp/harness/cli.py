# mcp/harness/cli.py — W3 operator CLI (ROADMAP-0.2.0): the operator surface for
# corpus-side state no MCP tool exposes. stdlib only. Run from the plugin repo root:
#   python mcp/harness/cli.py reclassify-tier <matter> <T0|T1|T2|T3>
#   python mcp/harness/cli.py bind-tier <matter> <T0|T1|T2|T3|clear>
#   python mcp/harness/cli.py sync-version [X.Y.Z]
# reclassify-tier stamps an already-ingested matter's docs (the G3 deferred surface);
# bind-tier writes the ingest-time default tier (matter.json at the store root, the
# default t_ingest_docs falls back to); sync-version stamps the three hardcoded
# version copies (plugin.json, marketplace.json, server.py VERSION) to one value —
# the "no build step syncs them yet" note at server.VERSION is this command.
from __future__ import annotations

import json
import re
import sqlite3
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_ROOT / "mcp"))

from harness.corpus import CorpusStore, _OPENNESS  # noqa: E402
from harness.paths import resolve_store_root  # noqa: E402


def reclassify_tier(matter: str, tier: str, root=None) -> dict:
    if tier not in _OPENNESS:
        return {"ok": False, "error": f"tier must be one of {sorted(_OPENNESS)}"}
    root = Path(root) if root else resolve_store_root()[0]
    store = CorpusStore(Path(root) / "corpus.sqlite3")
    try:
        n = store.set_tier(matter, tier)
    except sqlite3.OperationalError:
        return {"ok": False, "error": f"matter {matter!r} has no ingested corpus "
                                      f"at {root} to re-tier"}
    return {"ok": True, "matter": matter, "tier": tier, "docs": n, "root": str(root)}


def bind_tier(matter: str, tier: str, root=None) -> dict:
    if tier != "clear" and tier not in _OPENNESS:
        return {"ok": False, "error": f"tier must be one of {sorted(_OPENNESS)} "
                                      f"or 'clear'"}
    path = Path(root) / "matter.json" if root else \
        resolve_store_root()[0] / "matter.json"
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        data = {}
    if not isinstance(data, dict):
        data = {}
    if tier == "clear":
        data.pop(matter, None)
    else:
        row = data.get(matter)
        data[matter] = dict(row if isinstance(row, dict) else {}, trust_tier=tier)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    return {"ok": True, "matter": matter, "bound": data.get(matter),
            "file": str(path)}


def sync_version(ver: str | None = None, root=None) -> dict:
    """Stamp all three version copies. No arg: re-sync from plugin.json (repairs a
    drifted marketplace.json/server.py); an arg sets all three."""
    root = Path(root) if root else _ROOT
    pj = root / ".claude-plugin" / "plugin.json"
    mk = root / ".claude-plugin" / "marketplace.json"
    sp = root / "mcp" / "server.py"
    try:
        current = json.loads(pj.read_text(encoding="utf-8"))["version"]
    except (OSError, ValueError, KeyError) as ex:
        return {"ok": False, "error": f"cannot read {pj}: {ex}"}
    ver = ver or current
    if not re.fullmatch(r"\d+\.\d+\.\d+", ver):
        return {"ok": False, "error": f"version must be X.Y.Z, got {ver!r}"}
    changed: dict[str, str] = {}
    if ver != current:
        data = json.loads(pj.read_text(encoding="utf-8"))
        data["version"] = ver
        pj.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
        changed[str(pj)] = f"{current} -> {ver}"
    try:
        mk_data = json.loads(mk.read_text(encoding="utf-8"))
        old = mk_data["plugins"][0]["version"]
        if old != ver:
            mk_data["plugins"][0]["version"] = ver
            mk.write_text(json.dumps(mk_data, indent=2) + "\n", encoding="utf-8")
            changed[str(mk)] = f"{old} -> {ver}"
    except (OSError, ValueError, KeyError, IndexError) as ex:
        return {"ok": False, "error": f"cannot update {mk}: {ex}", "changed": changed}
    src = sp.read_text(encoding="utf-8")
    new = re.sub(r'(?m)^VERSION = "[^"]*"', f'VERSION = "{ver}"', src)
    if new != src:
        sp.write_text(new, encoding="utf-8")
        changed[str(sp)] = f"-> {ver}"
    return {"ok": True, "version": ver, "changed": changed}


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    fns = {"reclassify-tier": (reclassify_tier, 2),
           "bind-tier": (bind_tier, 2),
           "sync-version": (sync_version, 0)}
    if not argv or argv[0] not in fns or len(argv) - 1 < fns[argv[0]][1]:
        print(__doc__.strip(), file=sys.stderr)
        return 2
    out = fns[argv[0]][0](*argv[1:])
    print(json.dumps(out, ensure_ascii=False))
    return 0 if out.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
