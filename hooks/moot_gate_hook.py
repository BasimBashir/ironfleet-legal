# hooks/moot_gate_hook.py — M6 pre-write gate: nothing is marked final without a
# passed gate. A document declaring itself final (the exact front-matter line
# `status: final`) must carry a `moot-gate: PASSED <run_id>` marker line; a CAPPED
# document is never final — it goes to approval with its flaws listed.
# Harness-agnostic: reads Claude/Codex `tool_input` or Grok `toolInput`, and every
# write shape those harnesses (and the OpenCode/Pi/Hermes adapters) send — whole
# content, old/new pairs, edits[], and apply_patch envelopes. Deny = exit 2 with
# the reason on stderr (Claude Code, Codex and Grok Build all honour it); adapters
# that import this module call `deny_reason()` directly.
# A crashed or unreadable hook NEVER blocks: the gate denies only on the exact
# pattern, everything else allows (a checker that cannot read cannot convict).
import json
import re
import sys
from pathlib import Path

_FINAL = re.compile(r"(?m)^status:\s*final\s*$")
_PASSED = re.compile(r"(?m)^moot-gate:\s*PASSED\s+\S+")
_PATH_KEYS = ("file_path", "filePath", "path", "target_file", "file")
_WHOLE_KEYS = ("content", "contents", "file_text")
_PAIRS = (("old_string", "new_string"), ("oldString", "newString"),
          ("old_str", "new_str"), ("oldText", "newText"))
_PATCH_KEYS = ("command", "patch", "patchText", "input")
_PATCH_FILE = re.compile(r"^\*\*\* (Add|Update|Delete) File: (.+?)\s*$")
REASON = ("blocked: this document declares itself final (`status: final`) but "
          "carries no moot-gate marker — run /moot first; a CAPPED document is "
          "never marked final, it goes to approval with its flaws listed. If the "
          "gate already passed, include the moot-gate: PASSED <run_id> line in "
          "this write.")


def _read(path, cwd=None):
    try:
        p = Path(path)
        if not p.is_absolute() and cwd:
            p = Path(cwd) / p
        return p.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError, TypeError, ValueError):
        return None


def _apply(doc: str, edit: dict) -> str:
    """One replacement; a `new` whose `old` is not found is appended (conservative:
    the text the model tried to write is still judged)."""
    for ok, nk in _PAIRS:
        new = edit.get(nk)
        if isinstance(new, str):
            old = edit.get(ok)
            if isinstance(old, str) and old and old in doc:
                return doc.replace(old, new, 1)
            return doc + "\n" + new
    return doc


def _patch_texts(patch: str, cwd) -> list:
    """The files an apply_patch envelope would leave: Update = current file with the
    `-` lines removed and the `+` lines added; Add = the `+` lines; Delete = nothing."""
    out, cur = [], None
    for line in patch.splitlines():
        m = _PATCH_FILE.match(line)
        if m:
            if cur is not None:
                out.append("\n".join(cur[0] + cur[1]))
            kind, path = m.groups()
            base = (_read(path, cwd) or "") if kind == "Update" else ""
            cur = None if kind == "Delete" else (base.splitlines(), [])
        elif cur is None or line.startswith("*** "):
            continue
        elif line.startswith("+"):
            cur[1].append(line[1:])
        elif line.startswith("-") and line[1:] in cur[0]:
            cur[0].remove(line[1:])
    if cur is not None:
        out.append("\n".join(cur[0] + cur[1]))
    return out


def resulting_texts(tool_input: dict, cwd=None) -> list:
    """Every document text the write would leave behind (empty: not a write)."""
    if not isinstance(tool_input, dict):
        return []
    for k in _PATCH_KEYS:
        v = tool_input.get(k)
        if isinstance(v, str) and "*** Begin Patch" in v:
            return _patch_texts(v, cwd)
    for k in _WHOLE_KEYS:
        if isinstance(tool_input.get(k), str):
            return [tool_input[k]]
    path = next((tool_input[k] for k in _PATH_KEYS if isinstance(tool_input.get(k), str)), None)
    edits = tool_input.get("edits")
    edits = [e for e in edits if isinstance(e, dict)] if isinstance(edits, list) else []
    if any(isinstance(tool_input.get(nk), str) for _ok, nk in _PAIRS):
        edits = [tool_input] + edits
    if not edits:
        return []
    doc = _read(path, cwd) if path else None
    if doc is None:                       # new file: the first old text stands in for it
        doc = next((e[ok] for e in edits for ok, _nk in _PAIRS
                    if isinstance(e.get(ok), str)), "")
    for e in edits:
        doc = _apply(doc, e)
    return [doc]


def deny_reason(tool_input: dict, cwd=None):
    """REASON when the write would leave an unmarked `status: final` document."""
    for text in resulting_texts(tool_input, cwd):
        if _FINAL.search(text) and not _PASSED.search(text):
            return REASON
    return None


def main() -> None:
    if hasattr(sys.stdin, "reconfigure"):
        sys.stdin.reconfigure(encoding="utf-8", errors="replace")
    if hasattr(sys.stderr, "reconfigure"):   # the deny reason carries em-dashes;
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")  # cp1252 would mangle them
    try:
        data = json.loads(sys.stdin.read() or "{}")
        tool_input = data.get("tool_input") or data.get("toolInput") or {}
        reason = deny_reason(tool_input, data.get("cwd"))
    except Exception:                                  # noqa: BLE001 — never convict on a crash
        reason = None
    if reason:
        print(reason, file=sys.stderr)
        sys.exit(2)
    print("{}")


if __name__ == "__main__":
    main()
