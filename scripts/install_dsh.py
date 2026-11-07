"""Wire IronFleet Legal into a DeepSeek Harness (dsh) profile.

    python scripts/install_dsh.py [--profile web] [--patch-file PATH]

dsh has no plugin installer for third-party bundles, so this appends two loader
entries to the profile's patch layer (~/.dsh/profiles/<profile>/cordis.patch.yml,
backed up first): the first-party MCP client pointed at this checkout's
mcp/server.py, and a filesystem skill provider over skills/ and commands/ (dsh reads
flat Markdown skill files, so the 11 commands load as skills). Idempotent: entries
already present are left alone. Stdlib only.
"""
import argparse
import json
import os
import shutil
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MARK = "id: ironfleet-mcp"


def block(root: Path) -> str:
    q = lambda p: json.dumps(str(p).replace("\\", "/"))       # noqa: E731 — a YAML-safe string
    return (
        "# IronFleet Legal (scripts/install_dsh.py)\n"
        "- insert:\n"
        "    - id: ironfleet-mcp\n"
        "      name: '@deepseek-ai/dsh-mcp-client'\n"
        "      config:\n"
        "        serverName: ironfleet\n"
        "        transport: stdio\n"
        "        command: python\n"
        f"        args: [{q(root / 'mcp' / 'server.py')}]\n"
        f"        cwd: {q(root)}\n"
        "        toolCallTimeoutMs: 600000\n"
        "    - id: ironfleet-skills\n"
        "      name: '@deepseek-ai/dsh-skill-filesystem'\n"
        "      config:\n"
        "        providerName: ironfleet\n"
        "        includeDefaultRoots: false\n"
        f"        customSkillDirs: [{q(root / 'skills')}, {q(root / 'commands')}]\n")


def merge(existing: str, root: Path) -> str:
    """The patch layer with our entries added. The layer is a top-level YAML array:
    an empty `[]` is replaced, a block-style list is appended to; a non-empty
    flow-style list cannot be appended to safely, so it is refused."""
    if MARK in existing:
        return existing
    body = [ln for ln in existing.splitlines() if ln.strip() and not ln.lstrip().startswith("#")]
    if body == ["[]"] or not body:
        kept = [ln for ln in existing.splitlines() if ln.strip() != "[]"]
        return "\n".join(kept).rstrip() + "\n" + block(root)
    if body[0].lstrip().startswith("["):
        raise SystemExit("cordis.patch.yml holds a non-empty flow-style list; convert it to "
                         "block style (one `- ` entry per line) and re-run.")
    return existing.rstrip() + "\n" + block(root)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--profile", default="web")
    ap.add_argument("--patch-file", help="write here instead of the profile's patch layer")
    a = ap.parse_args()
    home = Path(os.environ.get("DSH_HOME") or Path.home() / ".dsh")
    target = Path(a.patch_file) if a.patch_file else home / "profiles" / a.profile / "cordis.patch.yml"
    if not a.patch_file and not target.parent.is_dir():
        raise SystemExit(f"no dsh profile at {target.parent} — run `dsh {a.profile}` once first")
    existing = target.read_text(encoding="utf-8") if target.exists() else "[]\n"
    merged = merge(existing, ROOT)
    if merged == existing:
        print(f"already wired: {target}")
        return
    if target.exists():
        backup = target.with_suffix(f".yml.bak-{time.strftime('%Y%m%d-%H%M%S')}")
        shutil.copy2(target, backup)
        print(f"backup: {backup}")
    target.write_text(merged, encoding="utf-8")
    print(f"wired IronFleet into {target}\nverify: dsh --profile {a.profile} --dump-config "
          "(look for ironfleet-mcp and ironfleet-skills), then start a new dsh session.")


if __name__ == "__main__":
    sys.exit(main())
