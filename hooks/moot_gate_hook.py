# hooks/moot_gate_hook.py — M6 PreToolUse (Write|Edit): nothing is marked final
# without a passed gate. A document declaring itself final (the exact front-matter
# line `status: final`) must carry a `moot-gate: PASSED <run_id>` marker line; a
# CAPPED document is never final — it goes to approval with its flaws listed.
# Deny = exit 2 with the reason on stderr (the Claude Code hook contract).
# A crashed or unreadable hook NEVER blocks: the gate denies only on the exact
# pattern, everything else allows (a checker that cannot read cannot convict).
import json
import re
import sys
from pathlib import Path

_FINAL = re.compile(r"(?m)^status:\s*final\s*$")
_PASSED = re.compile(r"(?m)^moot-gate:\s*PASSED\s+\S+")


def _resulting_text(tool_input: dict):
    """The content the write would leave: Write carries it whole; for an Edit,
    simulate the replacement against the file's current text (missing file ->
    the new_string alone)."""
    if isinstance(tool_input.get("content"), str):
        return tool_input["content"]
    new = tool_input.get("new_string")
    if new is None:
        return None
    try:
        doc = Path(tool_input.get("file_path") or "").read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        doc = tool_input.get("old_string") or ""
    old = tool_input.get("old_string")
    if isinstance(old, str) and old in doc:
        doc = doc.replace(old, new, 1)
    return doc


def main() -> None:
    if hasattr(sys.stdin, "reconfigure"):
        sys.stdin.reconfigure(encoding="utf-8", errors="replace")
    if hasattr(sys.stderr, "reconfigure"):   # the deny reason carries em-dashes;
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")  # cp1252 would mangle them
    try:
        data = json.loads(sys.stdin.read() or "{}")
    except ValueError:
        print("{}")
        return
    text = _resulting_text(data.get("tool_input") or {})
    if isinstance(text, str) and _FINAL.search(text) and not _PASSED.search(text):
        print("blocked: this document declares itself final (`status: final`) but "
              "carries no moot-gate marker — run /moot first; a CAPPED document is "
              "never marked final, it goes to approval with its flaws listed. If the "
              "gate already passed, include the moot-gate: PASSED <run_id> line in "
              "this write.", file=sys.stderr)
        sys.exit(2)
    print("{}")


if __name__ == "__main__":
    main()
