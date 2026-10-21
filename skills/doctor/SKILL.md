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

1. **Python** — `python --version` → need 3.10+.
   Fix: install CPython 3.12 from python.org (tick "Add to PATH").
2. **sqlite-vec** — `python -c "import sqlite_vec; print(sqlite_vec.__version__)"`.
   Fix: `pip install --user sqlite-vec==0.1.9` (one-time, network needed only here).
3. **PDF support (optional)** — `python -c "import pypdf"`.
   Fix: `pip install --user pypdf` (only needed to ingest PDFs).
4. **Ollama up** — fetch `http://127.0.0.1:11434/api/tags` (curl or python urllib).
   Fix: start Ollama; if not installed, https://ollama.com then `ollama pull bge-m3`.
5. **Embedding model** — the tags list must include `bge-m3`.
   Fix: `ollama pull bge-m3`.
6. **Reranker (optional)** — fetch `http://127.0.0.1:8778/v1/rerank` reachability
   (a TCP connect that answers anything counts). Down = fine: search degrades to
   fusion order, honestly noted in results.
   Fix (to enable): llama-server with `--reranking --pooling rank` on :8778 and the
   official ggml-org `qwen3-reranker-0.6b` GGUF.
7. **Store writable** — resolve the store root the way the plugin does
   (`%LOCALAPPDATA%\IronFleet\harness` on Windows, `~/Library/Application Support/IronFleet/harness`
   on macOS, XDG data dir on Linux; `HARNESS_HOME` overrides) and write+delete a probe
   file. Fix: check permissions; the directory is created on first write.
8. **Volume encryption (CR-7 parity)** — Windows: `manage-bde -status C:` (Protection On);
   macOS: `fdesetup status` (FileVault On); Linux: `lsblk -o NAME,TYPE` shows `crypt` on
   the store's device. Unencrypted → **refuse to run privileged matters** unless the user
   states the override; print and record the override exactly as
   `IronFleet store on an UNENCRYPTED volume — override acknowledged by user <date>`
   (the `-AcceptUnencryptedStore` honesty rule).
9. **Privacy boundary (state, always)** — Claude Code keeps session transcripts in
   PLAINTEXT under `~/.claude/projects/` (30-day default cleanup; Desktop/Cowork-started
   sessions exempt by default). The plugin's own files stay on this machine and inherit
   the volume-encryption posture of check 8. For privileged work: Team/Enterprise plan,
   model training OFF.

## Degraded mode (what still works when the MCP server cannot start)

Skills and agents always run — they are pure Claude. Only the corpus machinery
(`ironfleet_corpus_search`, `ironfleet_ingest_docs`) needs this server. Without it,
drafts must carry `[NO CORPUS STORE — attach documents directly]` instead of citations.
Doctor failing on 2/4/5 predicts degraded mode: fix before running a matter.
