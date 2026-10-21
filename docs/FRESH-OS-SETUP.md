# Fresh-OS setup — IronFleet Legal from zero

Every step below was executed live on a real Windows 11 box (2026-10-21) and verified
end-to-end: install → doctor → ingest → the full nine-stage pipeline. Frictions found on
the way are recorded inline (marked **FRICTION**). macOS/Linux notes where they differ.

## 0. Prerequisites

| Need | Version | Check |
|---|---|---|
| OS volume encryption | BitLocker/FileVault/crypt ON | `manage-bde -status C:` (Admin) |
| CPython | ≥ 3.10 | `python --version` |
| Git + Node + Claude Code CLI | current | `claude --version` |
| Ollama | any recent | `curl http://127.0.0.1:11434/api/tags` |
| bge-m3 model | — | `ollama pull bge-m3` (~1.2 GB) |
| pypdf (PDF ingest only) | — | `python -m pip install --user pypdf` |

Local models are pinned at `ironfleet-legal`; nothing in the plugin calls a cloud
service. The LLM is your own Claude account.

## 1. Install the plugin (two commands)

```bash
claude plugin marketplace add <you>/ironfleet-legal
claude plugin install ironfleet-legal@ironfleet-legal --config consent_local_processing=true
```

- From a local checkout instead of GitHub: `claude plugin marketplace add ./ironfleet-legal`.
- **FRICTION (recorded):** the consent option is REQUIRED; on CLI ≥ 2.1.281 you can set
  or change it later with `claude plugin configure ironfleet-legal@ironfleet-legal` — on
  older CLIs pass `--config KEY=VALUE` at install time (verified working).
- **FRICTION (recorded):** the installed plugin is a CACHE COPY of the repo
  (`~/.claude/plugins/cache/...`) taken from the repo's **committed** state. After any
  code change: commit, then refresh with
  `claude plugin uninstall ironfleet-legal@ironfleet-legal && claude plugin install ironfleet-legal@ironfleet-legal`.
  (A `marketplace remove && add` alone does NOT refresh an installed plugin; an
  `install` over an existing install is a no-op.)

## 2. Python deps for the corpus machinery

```bash
python -m pip install --user sqlite-vec==0.1.9
python -m pip install --user pypdf        # only if you will ingest PDFs
```

**FRICTION (recorded):** sqlite-vec is the one non-stdlib import; without it the
corpus tools fail LOUD (`RuntimeError: sqlite-vec is a hard dependency`) — that is
by design; `/ironfleet-legal:doctor` prints this exact fix.

## 3. Embedding model tag

The server embeds with model name `bge-m3` (override with env `IRONFLEET_EMBED_MODEL`).
If your box already has a differently-tagged bge-m3 (e.g. `bge-m3:567m`), either
`ollama pull bge-m3` or alias instantly: `ollama cp bge-m3:567m bge-m3` (verified).
Override knobs: `IRONFLEET_OLLAMA_URL` (default `http://127.0.0.1:11434`),
`IRONFLEET_RERANK_URL` (default `http://127.0.0.1:8778`).

## 4. First-run doctor (in any Claude session with the plugin)

```
/ironfleet-legal:doctor
```

Verified live verdict: `DEGRADED` with only the optional reranker missing — corpus
machinery fully up. Notes: (a) the BitLocker check needs an **elevated** terminal; from
a normal one it reports "indeterminate" and privileged matters stay gated (fail-closed,
by design); (b) the privacy boundary is always stated (plaintext Claude Code transcripts
under `~/.claude/projects/`, 30-day default cleanup).

## 5. Ingest a matter

```
/ironfleet-legal:ingest <folder-or-file> matter: <colon-free-ref>
```

Verified live: 5 markdown/text docs → 10 chunks, sha256-idempotent, zero skips.
**FRICTION (recorded):** files under 200 words are RECORDED-AND-SKIPPED (the
scanned-source floor) — a short note will not silently enter the corpus; give it real
content or merge it into a larger file. PDFs ride the same chain (MarkItDown → pypdf →
raw text) in a killable subprocess; a hang is skipped, never stuck.

## 6. Run the pipeline

```
/ironfleet-legal:process-case process my docs — can I win, and how do I file? matter: <ref>
```

One prompt in; nine agent stages out (intake → research → strategy → attack → assess →
filings → advice → verify → close); deliverables land in `matters/<ref>/` with
provenance headers; the run ledger (`run.json` + `trace.jsonl` + `RECORD.md`) lands in
the same workspace's `runs/`. Expect 25–40 minutes of agent work.

## 7. Headless / CI driving (optional, how this was verified)

```bash
claude -p "/ironfleet-legal:ingest matter-docs matter: powell-builders" \
  --allowedTools "mcp__plugin_ironfleet-legal_ironfleet__*"
claude -p "/ironfleet-legal:process-case <ask> matter: <ref>" \
  --allowedTools "mcp__plugin_ironfleet-legal_ironfleet__*,Task,Read,Write,Edit,Glob,Grep"
```

**FRICTION (recorded):** on a machine whose Claude Code authenticates through a local
gateway (`apiKeyHelper` + `ANTHROPIC_BASE_URL` in settings.json), the standalone CLI
may report `Not logged in` when its own OAuth has expired. The env-key route works
without changing any file: export `ANTHROPIC_API_KEY` from your key-helper for the
child process. Otherwise run `claude /login` once interactively.

## Claude Desktop / Cowork

Customize → Plugins → **Add marketplace** → `<you>/ironfleet-legal` → Install. Cowork
runs the local stdio MCP because the session is on your machine; claude.ai chat ignores
local MCP servers (skills and agents still work there, with the corpus honestly
degraded — drafts carry `[NO CORPUS STORE — attach documents directly]`).
