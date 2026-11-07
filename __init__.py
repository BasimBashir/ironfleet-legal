"""IronFleet Legal — Hermes Agent plugin entry point (`register(ctx)`).

Hermes installs this repo with `hermes plugins install BasimBashir/ironfleet-legal`.
Everything registered here is read from the plugin's own files — the same skills,
commands and moot gate Claude Code uses. The MCP server is added once with
`hermes ironfleet setup` (Hermes keeps MCP servers in config.yaml, not in plugins).
"""
import importlib.util
import subprocess
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent
_SERVER = _ROOT / "mcp" / "server.py"
_WRITE_TOOLS = ("write_file", "patch")


def _load_gate():
    spec = importlib.util.spec_from_file_location(
        "ironfleet_moot_gate", _ROOT / "hooks" / "moot_gate_hook.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _split(text: str):
    """(frontmatter dict, body) — top-level `key: value` lines only."""
    meta = {}
    if text.startswith("---"):
        head, _, text = text[3:].partition("\n---")
        for line in head.splitlines():
            k, sep, v = line.partition(":")
            if sep and not line.startswith(" "):
                meta[k.strip()] = v.strip().strip('"')
        text = text.lstrip("\n")
    return meta, text


def _command(ctx, name: str, body: str):
    def handler(raw_args: str, *, session_key: str = "") -> str:
        text = body.replace("$ARGUMENTS", (raw_args or "").strip())
        if ctx.inject_message(text, role="user", session_key=session_key or None):
            return f"IronFleet /{name} started."
        return f"Could not queue /{name} — send this as your message:\n\n{text}"
    return handler


def _cli_setup(subparser):
    subs = subparser.add_subparsers(dest="ironfleet_command")
    subs.add_parser("setup", help="Register the ironfleet MCP server with Hermes")
    subs.add_parser("status", help="Show where the plugin lives")
    subparser.set_defaults(func=_cli)


def _cli(args):
    if getattr(args, "ironfleet_command", None) == "setup":
        # The SYSTEM python (where sqlite-vec is installed), never Hermes's own venv.
        cmd = ["hermes", "mcp", "add", "ironfleet", "--command", "python",
               "--args", str(_SERVER)]
        print("Running:", " ".join(cmd))
        sys.exit(subprocess.call(cmd))
    print(f"IronFleet Legal plugin root: {_ROOT}\nMCP server: python {_SERVER}\n"
          "Next: `hermes ironfleet setup`, then a new session and /ironfleet-doctor.")


def register(ctx):
    gate = _load_gate()

    for d in sorted((_ROOT / "skills").iterdir()):
        if (d / "SKILL.md").is_file():
            ctx.register_skill(d.name, d / "SKILL.md")

    for p in sorted((_ROOT / "commands").glob("*.md")):
        meta, body = _split(p.read_text(encoding="utf-8"))
        ctx.register_command(f"ironfleet-{p.stem}", handler=_command(ctx, p.stem, body),
                             description=meta.get("description", ""),
                             args_hint=meta.get("argument-hint", ""))

    def moot_gate(tool_name, args, task_id="", **_kw):
        if tool_name not in _WRITE_TOOLS:
            return None
        try:
            from agent.runtime_cwd import resolve_agent_cwd   # Hermes: the session's folder
            cwd = str(resolve_agent_cwd())
        except Exception:                                    # noqa: BLE001 — older Hermes
            cwd = None
        try:
            reason = gate.deny_reason(args if isinstance(args, dict) else {}, cwd)
        except Exception:                                    # noqa: BLE001 — never convict on a crash
            reason = None
        return {"action": "block", "message": reason} if reason else None

    ctx.register_hook("pre_tool_call", moot_gate)
    ctx.register_cli_command(name="ironfleet", help="IronFleet Legal setup",
                             setup_fn=_cli_setup, handler_fn=_cli)
