# tests/test_moot_hook.py — the moot-gate PreToolUse hook (Write|Edit): nothing is
# ever marked `status: final` without a moot-gate: PASSED marker. A CAPPED document
# never passes. Subprocess, stdio envelope, offline.
import json
import subprocess
import sys
from pathlib import Path

HOOK = Path(__file__).resolve().parents[1] / "hooks" / "moot_gate_hook.py"


def run_hook(payload: dict) -> subprocess.CompletedProcess:
    return subprocess.run([sys.executable, str(HOOK)],
                          input=json.dumps(payload), capture_output=True,
                          text=True, encoding="utf-8", timeout=60)


def write_payload(content: str, path: str = "C:/tmp/advice.md") -> dict:
    return {"tool_name": "Write", "tool_input": {"file_path": path, "content": content}}


FINAL = "---\nstatus: final\n---\n\nAdvice body.\n"
FINAL_PASSED = ("---\nstatus: final\n---\n\nAdvice body.\n\n"
                "moot-gate: PASSED run-20261105-abc123\n")
FINAL_CAPPED = ("---\nstatus: final\n---\n\nAdvice body.\n\n"
                "moot-gate: CAPPED run-20261105-abc123\n")


def test_denies_final_without_marker():
    p = run_hook(write_payload(FINAL))
    assert p.returncode == 2
    assert "/moot" in p.stderr


def test_allows_final_with_passed_marker():
    p = run_hook(write_payload(FINAL_PASSED))
    assert p.returncode == 0 and json.loads(p.stdout) == {}


def test_refuses_capped_even_with_marker_line():
    p = run_hook(write_payload(FINAL_CAPPED))
    assert p.returncode == 2


def test_allows_prose_mentions_of_final():
    p = run_hook(write_payload("The court entered a final order; final order quoted.\n"))
    assert p.returncode == 0 and json.loads(p.stdout) == {}


def test_allows_ordinary_non_final_write():
    p = run_hook(write_payload("# draft advice\n\nworking notes\n"))
    assert p.returncode == 0


def test_edit_denies_new_final_line(tmp_path):
    f = tmp_path / "advice.md"
    f.write_text("# advice draft\n", encoding="utf-8")
    p = run_hook({"tool_name": "Edit",
                  "tool_input": {"file_path": str(f), "old_string": "# advice draft\n",
                                 "new_string": "# advice draft\nstatus: final\n"}})
    assert p.returncode == 2


def test_edit_allows_when_file_already_has_marker(tmp_path):
    f = tmp_path / "advice.md"
    f.write_text(FINAL_PASSED, encoding="utf-8")
    p = run_hook({"tool_name": "Edit",
                  "tool_input": {"file_path": str(f), "old_string": "Advice body.",
                                 "new_string": "Advice body, with a closing note."}})
    assert p.returncode == 0


def test_edit_denies_when_target_file_already_final_unmarked(tmp_path):
    f = tmp_path / "advice.md"
    f.write_text(FINAL, encoding="utf-8")
    p = run_hook({"tool_name": "Edit",
                  "tool_input": {"file_path": str(f), "old_string": "Advice body.",
                                 "new_string": "Advice body, polished."}})
    assert p.returncode == 2


def test_garbage_stdin_never_blocks():
    p = subprocess.run([sys.executable, str(HOOK)], input="not json{",
                       capture_output=True, text=True, encoding="utf-8", timeout=60)
    assert p.returncode == 0
