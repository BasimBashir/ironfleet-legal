---
name: doctor
description: IronFleet preflight — verify everything the corpus machinery needs on this machine (Python, sqlite-vec, Ollama + bge-m3, optional reranker, store writable, volume encryption) and print the EXACT fix command for anything missing. Use at first install, when corpus tools fail, or whenever the user asks to check the setup.
license: MIT
compatibility: Claude Code, Claude Desktop, Claude Cowork
metadata:
  version: 1.0.0
  rung: R-CL1
---

# IronFleet doctor

Run each check in order with the local shell (Bash). For every FAILED check, print the
exact fix command shown. End with the verdict line: `READY` (all passed), `DEGRADED`
(core works, optional pieces missing), or `BLOCKED` (something the fixes below must
cure). Never install anything without telling the user what and why.

1. **MCP server boots (the real readiness test — everything else is subordinate).**
   Run the server's actual handshake with the plugin's interpreter exactly as the
   plugin's `.mcp.json` names it (`python`):
   `echo '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2025-06-18","capabilities":{},"clientInfo":{"name":"doctor","version":"0"}}}' | python "${CLAUDE_PLUGIN_ROOT}/mcp/server.py"`
   PASS = the reply contains `"serverInfo"`. If `python` itself is missing (ENOENT),
   the OS fixes are: Ubuntu/Debian `sudo apt install python-is-python3` (or no-sudo
   `mkdir -p ~/.local/bin && ln -sf "$(command -v python3)" ~/.local/bin/python`);
   macOS `ln -sf "$(command -v python3)" /usr/local/bin/python` (or brew's python);
   Windows: install CPython from python.org with "Add to PATH".
   If it crashes on an import, fix the NAMED module (`python -m pip install --user
   --break-system-packages <module>` on PEP 668 distros) and re-run this check.
   After ANY fix here: the session must be RESTARTED — plugin MCP servers bind at
   session start, so a repair inside the current session is invisible to it. Say this
   explicitly in the verdict.
2. **Python version** — `python --version` → need 3.10+.
   Fix: install CPython 3.12+ (python.org on Windows; distro python3 on Linux; Xcode
   CLT or brew on macOS).
3. **sqlite-vec** — `python -c "import sqlite_vec; print(sqlite_vec.__version__)"`.
   Fix: `python -m pip install --user sqlite-vec==0.1.9` (add `--break-system-packages`
   on PEP 668 distros — Ubuntu 23.04+).
4. **PDF support (optional)** — `python -c "import pypdf"`.
   Fix: `python -m pip install --user pypdf` (same PEP 668 caveat). Only needed to
   ingest PDFs; markitdown is likewise optional (rich formats; gracefully skipped).
5. **Ollama up** — fetch `http://127.0.0.1:11434/api/tags` (curl or python urllib).
   Fix: start Ollama; if not installed, https://ollama.com then `ollama pull bge-m3`.
6. **Embedding model** — the tags list must include `bge-m3`.
   Fix: `ollama pull bge-m3` (an existing differently-tagged bge-m3 can be aliased:
   `ollama cp bge-m3:567m bge-m3`).
7. **Reranker (optional)** — fetch `http://127.0.0.1:8778/v1/rerank` reachability
   (a TCP connect that answers anything counts). Down = fine: search degrades to
   fusion order, honestly noted in results.
   Fix (to enable): llama-server with `--reranking --pooling rank` on :8778 and the
   official ggml-org `qwen3-reranker-0.6b` GGUF.
8. **Store writable** — resolve the store root the way the PLUGIN does (never hand-build
   the path — the Linux dir is lowercase `ironfleet` under XDG, Windows is
   `%LOCALAPPDATA%\IronFleet\harness`, macOS is `~/Library/Application Support/IronFleet/harness`):
   `python -c "import sys; sys.path.insert(0,'${CLAUDE_PLUGIN_ROOT}/mcp'); from harness.paths import resolve_store_root; r,s=resolve_store_root(); print(r)"`,
   then write+delete a probe file there. Fix: check permissions; the directory is
   created on first write.
9. **Volume encryption (CR-7 parity)** — Windows: `manage-bde -status C:` (Protection On);
   macOS: `fdesetup status` (FileVault On); Linux: `lsblk -o NAME,TYPE,FSTYPE` — the
   store's device must show `crypt` (LUKS); plain ext4 on a bare partition is
   UNENCRYPTED. Unencrypted → **refuse to run privileged matters** unless the user
   states the override; print and record the override exactly as
   `IronFleet store on an UNENCRYPTED volume — override acknowledged by user <date>`
   (the `-AcceptUnencryptedStore` honesty rule). A throwaway VM for testing is the
   user's call — say the override is theirs to make, once, explicitly.
10. **Privacy boundary (state, always)** — Claude Code keeps session transcripts in
   PLAINTEXT under `~/.claude/projects/` (30-day default cleanup; Desktop/Cowork-started
   sessions exempt by default). The plugin's own files stay on this machine and inherit
   the volume-encryption posture of check 9. For privileged work: Team/Enterprise plan,
   model training OFF.

## Degraded mode (what still works when the MCP server cannot start)

Skills and agents always run — they are pure Claude. Only the corpus machinery
(`ironfleet_corpus_search`, `ironfleet_ingest_docs`) needs this server. Without it,
drafts must carry `[NO CORPUS STORE — attach documents directly]` instead of citations.
Check 1 (the server boot) IS the degraded-mode test: if it fails, fix it, then START A
NEW SESSION — the current session will not see the repair.
