# tests/test_adapters.py — the per-harness entry points stay in step with the one
# source of truth: same version everywhere, Codex launches the server the way its
# loader does, the Codex hook command gates, and the Hermes plugin registers the
# kit from the same files. Offline; no harness needs to be installed.
import json
import os
import subprocess
import sys
from pathlib import Path

PLUGIN = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PLUGIN / "mcp"))
import server  # noqa: E402

FINAL = "---\nstatus: final\n---\nbody\n"


def _json(rel):
    return json.loads((PLUGIN / rel).read_text(encoding="utf-8"))


def test_every_manifest_carries_the_server_version():
    v = server.VERSION
    assert _json(".claude-plugin/plugin.json")["version"] == v
    assert _json(".claude-plugin/marketplace.json")["plugins"][0]["version"] == v
    assert _json(".codex-plugin/plugin.json")["version"] == v
    assert _json(".cursor-plugin/plugin.json")["version"] == v
    assert _json("gemini-extension.json")["version"] == v
    assert _json("package.json")["version"] == v
    assert f"version: {v}" in (PLUGIN / "plugin.yaml").read_text(encoding="utf-8")


def test_codex_launch_from_plugin_root_handshakes():
    """Codex joins the manifest's relative cwd to the plugin root and passes args
    verbatim — so `python mcp/server.py` from the root must answer initialize."""
    srv = _json(".codex-plugin/plugin.json")["mcpServers"]["ironfleet"]
    assert srv["cwd"] == "." and not Path(srv["args"][0]).is_absolute()
    req = json.dumps({"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}})
    p = subprocess.run([sys.executable, *srv["args"]], cwd=PLUGIN / srv["cwd"],
                       input=req + "\n", capture_output=True, text=True,
                       encoding="utf-8", timeout=120)
    assert '"serverInfo"' in p.stdout


def test_codex_hook_command_gates_via_plugin_root_env():
    hooks = _json("hooks/codex-hooks.json")["hooks"]["PreToolUse"][0]
    assert "apply_patch" in hooks["matcher"]
    cmd = hooks["hooks"][0]["command"].replace("python ", f'"{sys.executable}" ', 1)
    env = {**os.environ, "PLUGIN_ROOT": str(PLUGIN)}
    payload = {"tool_name": "apply_patch", "tool_input": {
        "command": "*** Begin Patch\n*** Add File: a.md\n+status: final\n*** End Patch\n"}}
    p = subprocess.run(cmd, shell=True, env=env, input=json.dumps(payload),
                       capture_output=True, text=True, encoding="utf-8", timeout=60)
    assert p.returncode == 2 and "moot-gate" in p.stderr


class FakeHermes:
    def __init__(self):
        self.skills, self.commands, self.hooks, self.cli, self.injected = {}, {}, {}, {}, []

    def register_skill(self, name, path):
        self.skills[name] = Path(path)

    def register_command(self, name, handler, description="", args_hint=""):
        self.commands[name] = (handler, description)

    def register_hook(self, event, fn):
        self.hooks[event] = fn

    def register_cli_command(self, name, help, setup_fn, handler_fn):
        self.cli[name] = handler_fn

    def inject_message(self, content, role="user", session_key=None):
        self.injected.append(content)
        return True


def _hermes():
    import importlib.util
    spec = importlib.util.spec_from_file_location("ironfleet_hermes", PLUGIN / "__init__.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    ctx = FakeHermes()
    mod.register(ctx)
    return ctx


def test_hermes_registers_the_whole_kit():
    ctx = _hermes()
    assert set(ctx.skills) == {d.name for d in (PLUGIN / "skills").iterdir()
                               if (d / "SKILL.md").is_file()}
    assert set(ctx.commands) == {f"ironfleet-{p.stem}" for p in (PLUGIN / "commands").glob("*.md")}
    assert "ironfleet" in ctx.cli
    handler, desc = ctx.commands["ironfleet-process-case"]
    assert desc and handler("can we win? matter: acme").endswith("started.")
    assert "can we win? matter: acme" in ctx.injected[-1] and "$ARGUMENTS" not in ctx.injected[-1]


def test_hermes_gate_blocks_only_unmarked_final():
    gate = _hermes().hooks["pre_tool_call"]
    blocked = gate("write_file", {"path": "x.md", "content": FINAL})
    assert blocked["action"] == "block" and "moot-gate" in blocked["message"]
    assert gate("write_file", {"path": "x.md", "content": FINAL + "moot-gate: PASSED r1\n"}) is None
    assert gate("terminal", {"command": "echo status: final"}) is None
    assert gate("patch", {"mode": "replace", "path": "nope.md", "old_string": "",
                          "new_string": "status: final\n"})["action"] == "block"
