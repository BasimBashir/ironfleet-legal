# Fresh-OS setup — IronFleet Legal from zero

> **Current release:** v0.6.0 (2026-11-07) · repo
> [BasimBashir/ironfleet-legal](https://github.com/BasimBashir/ironfleet-legal) ·
> 27 skills (one adapted skill is distributed against its upstream's no-derivatives
> terms at the repo owner's election — see ATTRIBUTION.md), 19 agents, 11 commands,
> 25 mechanical-only MCP tools · installs in Claude Code / Desktop / Cowork and in
> the other harnesses of §1b.

Every step below was executed live on a real Windows 11 box (2026-10-21) and verified
end-to-end: install → doctor → ingest → the full nine-stage pipeline. Frictions found on
the way are recorded inline (marked **FRICTION**). macOS/Linux notes where they differ.

## 0. Prerequisites

| Need | Version | Check |
|---|---|---|
| OS volume encryption | BitLocker/FileVault/crypt ON | `manage-bde -status C:` (Admin) |
| CPython | ≥ 3.10 | `python --version` |
| Git + Node + your harness (Claude Code CLI, or one from §1b) | current | `claude --version` |
| Ollama | any recent | `curl http://127.0.0.1:11434/api/tags` |
| bge-m3 model | — | `ollama pull bge-m3` (~1.2 GB) |
| pypdf (PDF ingest only) | — | `python -m pip install --user pypdf` |

Local models are pinned at `ironfleet-legal`; nothing in the plugin calls a cloud
service. The LLM is your own Claude account.

## 1. Install the plugin (two commands)

```bash
claude plugin marketplace add BasimBashir/ironfleet-legal
claude plugin install ironfleet-legal@ironfleet-legal --config consent_local_processing=true
```

- From a local checkout instead of GitHub: `claude plugin marketplace add ./ironfleet-legal`
  (developer workflow — same as publishing your own fork).
- **FRICTION (recorded):** the consent option is REQUIRED; on CLI ≥ 2.1.281 you can set
  or change it later with `claude plugin configure ironfleet-legal@ironfleet-legal`.
  On older CLIs neither flag may exist (found live 2026-10-26 on macOS CLI 2.1.85:
  `--config` is an unknown option — the earlier "pass it at install time" claim was
  wrong for that build). Install without it and carry on: the pipeline's consent
  reminder is non-blocking by design, and the flag can be set later from a current CLI.
- **FRICTION (recorded):** the installed plugin is a CACHE COPY of the repo
  (`~/.claude/plugins/cache/...`) taken from the repo's **committed** state. After any
  code change: commit, then refresh with
  `claude plugin uninstall ironfleet-legal@ironfleet-legal && claude plugin install ironfleet-legal@ironfleet-legal`.
  (A `marketplace remove && add` alone does NOT refresh an installed plugin; an
  `install` over an existing install is a no-op.)
- **Upgrading from an earlier version (e.g. 0.1.0):** the same uninstall → install,
  then start a NEW Claude session (see §4 — MCP binds at session start). Your corpus
  store and matter folders are outside the plugin cache and survive the upgrade. What
  changed is summarised in the README's "What changed since 0.1.0".

## 1b. Other harnesses

One repo, one source of truth: every harness below reads the same `skills/`,
`commands/`, `agents/`, `mcp/server.py` and `hooks/moot_gate_hook.py`. §0 and §2–§3
(Python, sqlite-vec, Ollama + bge-m3) apply unchanged — the MCP server always runs on
the SYSTEM `python`. After installing, start a NEW session and run the doctor skill
(ask "run the IronFleet doctor"); outside Claude Code it finds the plugin root itself
and checks that the harness actually sees the `ironfleet_*` tools.

**What reaches each harness.** Tools = the 25 `ironfleet_*` MCP tools. Commands =
the 11 workflows. Agents = the 19 stage briefs. Gate = the `status: final` write-deny.
Everywhere: if no slash command shows, ask by name — "IronFleet process-case: <ask>"
— and the agent fetches the workflow with `ironfleet_command`; a stage agent the
harness cannot load is dispatched from `ironfleet_agent_brief`.

### OpenAI Codex (CLI, IDE extension, app)

```bash
codex plugin marketplace add BasimBashir/ironfleet-legal
codex plugin add ironfleet-legal@ironfleet-legal
```

Codex reads `.codex-plugin/plugin.json`: skills, the MCP server (started from the
plugin root, since Codex does not expand `${CLAUDE_PLUGIN_ROOT}`), and
`hooks/codex-hooks.json` (the moot gate on `apply_patch`). Codex asks you to review
new hooks: trust both IronFleet hooks under `/hooks`, or the gate does not run.
Commands: by name (above). Agents: by brief. Skills: `$doctor`, `$nz-court-calendar`, ….
App: Plugins → Add marketplace → `BasimBashir/ironfleet-legal`, then restart Codex.

### xAI Grok Build (`grok`)

```bash
grok plugin install BasimBashir/ironfleet-legal --trust
```

Grok reads the Claude layout as-is: skills, commands (`/ironfleet-legal:process-case`),
agents, `.mcp.json` and `hooks/hooks.json` (its Write/Edit matcher maps to Grok's
`search_replace`; the gate reads Grok's camelCase payload). Press `r` in the Plugins
tab or start a new session. Updates: `grok plugin update`.

### GitHub Copilot CLI

```bash
copilot plugin marketplace add BasimBashir/ironfleet-legal
copilot plugin install ironfleet-legal@ironfleet-legal
```

Copilot reads `.claude-plugin/` (manifest, marketplace, `.mcp.json`, skills, commands,
hooks). Copilot loads agents only from `*.agent.md` files, so stages dispatch from
`ironfleet_agent_brief`. If `/mcp` shows the ironfleet server failing to start, your
build does not expand `${CLAUDE_PLUGIN_ROOT}` in plugin MCP args — add it by hand
with the generic entry below.

### OpenCode (≥ 1.18.29, or 2.x)

Add to `opencode.json` (global `~/.config/opencode/opencode.json` or the project's):

```json
{ "plugins": ["ironfleet-legal@git+https://github.com/BasimBashir/ironfleet-legal.git"] }
```

On OpenCode 1.x the key is `plugin` (singular). Restart OpenCode. The plugin
(`opencode/index.js`) registers the MCP server, the 27 skills, the 11 commands
(`/process-case`, …), the 19 agents as subagents (1.x; on 2.x stages dispatch from
`ironfleet_agent_brief`) and the moot gate on `write`/`edit`/`patch`. Check with
`opencode mcp list` → `ironfleet connected`. Older than 1.18.29: upgrade
(`opencode upgrade`) — earlier builds cannot load the plugin's export shape.

### Pi

```bash
pi install git:github.com/BasimBashir/ironfleet-legal
pi install npm:pi-subagents
```

The package (`package.json` → `pi`) brings the 27 skills, the 11 commands as prompt
templates (`/process-case <ask>`), and `pi/extension.ts`: the MCP bridge Pi core lacks
(all 25 tools) plus the moot gate on Pi's `write`/`edit`. `pi-subagents` gives the
nine stages their own contexts; without it each stage runs inline and the run record
says so. `/reload` or a new session after installing.

### Hermes Agent (Nous Research)

```bash
hermes plugins install BasimBashir/ironfleet-legal --enable
hermes ironfleet setup
```

The plugin registers the 27 skills, the 11 commands as `/ironfleet-process-case`,
`/ironfleet-ingest`, … (namespaced so they never shadow Hermes built-ins) and the moot
gate on `write_file`/`patch`. Hermes keeps MCP servers in `config.yaml`, so
`hermes ironfleet setup` runs `hermes mcp add ironfleet --command python --args
<plugin>/mcp/server.py` for you (`hermes mcp test ironfleet` to check). Stages
dispatch through `delegate_task` from `ironfleet_agent_brief`. Hermes runs on
macOS/Linux/WSL2.

### DeepSeek Harness (`dsh`)

```bash
git clone https://github.com/BasimBashir/ironfleet-legal ~/.dsh/ironfleet-legal
python ~/.dsh/ironfleet-legal/scripts/install_dsh.py --profile web
```

dsh has no installer for third-party bundles; the script backs up and appends two
entries to `~/.dsh/profiles/<profile>/cordis.patch.yml`: the first-party MCP client on
this checkout's server, and a skill provider over `skills/` and `commands/` (dsh loads
flat Markdown skills, so the 11 commands arrive as skills). Re-running is a no-op.
Check: `dsh --profile web --dump-config` lists `ironfleet-mcp` and
`ironfleet-skills`. Gate: dsh 0.1.1 ships no Claude-hooks bridge, so the agent
enforces it from the commands' instructions. Update with `git pull` in the checkout.

### Cursor (and Grok Bot)

`cursor-agent plugin marketplace add https://github.com/BasimBashir/ironfleet-legal`,
then `/plugin` → install (in the app: Customize → Install). Grok Bot shares your
Cursor plugin library — install it in Cursor, not in Grok Bot chat. Cursor reads
`.cursor-plugin/plugin.json` (skills, commands, agents, `.mcp.json`). Cursor's hook
format differs from Claude's, so the gate is instruction-enforced here.

### Gemini CLI

```bash
gemini extensions install https://github.com/BasimBashir/ironfleet-legal
```

`gemini-extension.json` starts the MCP server via `${extensionPath}` and loads
`AGENTS.md` as context. Commands arrive as the server's MCP prompts (`/process-case`);
gate instruction-enforced. Update: `gemini extensions update ironfleet-legal`.

### Factory Droid, Qwen Code

Both convert Claude plugins at install:
`droid plugin marketplace add https://github.com/BasimBashir/ironfleet-legal` then
`droid plugin install ironfleet-legal@ironfleet-legal`;
`qwen extensions install BasimBashir/ironfleet-legal:ironfleet-legal`.

### Any other harness with MCP + Agent Skills

Clone the repo, then give your harness one stdio MCP server and one skills folder:

```json
{ "mcpServers": { "ironfleet": { "command": "python",
  "args": ["/ABSOLUTE/PATH/ironfleet-legal/mcp/server.py"] } } }
```

Skills: point the harness at `/ABSOLUTE/PATH/ironfleet-legal/skills` (or symlink each
folder into its skills root — `~/.agents/skills` is read by many). Commands and
agents arrive through `ironfleet_command` / `ironfleet_agent_brief`; `AGENTS.md`
explains the kit to the agent.

### How each install was verified (2026-11-07)

| Harness | Evidence |
|---|---|
| Claude Code / Desktop / Cowork | live runs since 0.1.0; `claude plugin validate --strict` passes on 0.6.0 |
| OpenCode | LIVE on 1.18.25: MCP `connected`, 11 commands + 19 agents + skills in the resolved config, gate blocks an unmarked final write (adapter loaded through a test shim — 1.18.25 predates the export shape; 2.x path checked against the 2.x plugin API docs, not run) |
| DeepSeek Harness | LIVE on dsh 0.1.1-rc.2: patch composes in `--dump-config`; no model session run |
| Codex | server launch + hook command exercised offline exactly as Codex's loader invokes them (`tests/test_adapters.py`); install not run |
| Pi | extension run under Node against a stand-in Pi host: 25 tools bridged, calls and errors round-trip, gate blocks; not run inside Pi |
| Hermes | `register()` run against a stand-in plugin context (`tests/test_adapters.py`); not run inside Hermes |
| Grok Build, Copilot CLI, Cursor, Gemini CLI, Droid, Qwen | built from each harness's published docs/source; not run |

## 2. Python deps for the corpus machinery

```bash
python -m pip install --user sqlite-vec==0.1.9
python -m pip install --user pypdf        # only if you will ingest PDFs
```

**FRICTION (recorded):** sqlite-vec is the one non-stdlib import; without it the
corpus tools fail LOUD (`RuntimeError: sqlite-vec is a hard dependency`) — that is
by design; `/ironfleet-legal:doctor` prints this exact fix. On PEP 668 environments —
Ubuntu 23.04+ AND macOS Homebrew python — add `--break-system-packages` to both
pip commands.

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

(A thin command wrapper now makes this typeable; if your CLI build still says
"Unknown command", ask in words — "run the IronFleet doctor preflight" — the skill
invokes from its description.)

Check 1 is the real test: it runs the MCP server's own handshake. Everything else is
subordinate. Notes: (a) the encryption check needs elevated rights on Windows (BitLocker)
— from a normal terminal it reports "indeterminate" and privileged matters stay gated
(fail-closed, by design); (b) the privacy boundary is always stated (plaintext Claude
Code transcripts under `~/.claude/projects/`, 30-day default cleanup).

**FRICTION (recorded, found live on Ubuntu): MCP binds at session start.** Fixing
anything check 1 names (interpreter alias, missing module) inside the CURRENT session
does not restore the tools — `/reload-plugins` is not enough for plugin MCP servers.
After any fix: exit and start a fresh `claude` session, then re-run doctor.

## Placeholder cheat-sheet — what you actually type

Placeholders appear in angle brackets. You replace the WHOLE bracket (and the brackets
themselves) with your text — never type the `<` `>`.

| Placeholder | What goes there | Example |
|---|---|---|
| `<your ask …>` / `<ask>` | Your question or instruction to the legal crew, in plain English. This is the ONE prompt that runs the whole pipeline. | `process my docs — can I win, and how do I file?` |
| `<ref>` / `<colon-free-ref>` / `<matter-ref>` | A matter reference: the short name for THIS case. Letters, digits and dashes only — **no colons, spaces or slashes** (Windows forbids them in folder names; the store keys on it). Keep it stable: every later command for the same case reuses the same ref. | `powell-builders`, `acme-2026`, `smith-estate` |
| `<folder-or-file>` / `<path>` / `<folder>` | Where your documents live — a single file OR a whole folder (folders are ingested recursively; PDF/DOCX/TXT/MD all fine). Relative paths work from the folder Claude is running in. | `matter-docs`, `C:\cases\powell\emails.pdf` |
| `[matter: <ref>]` | The OPTIONAL tail you append to a command to name the matter. Square brackets in the docs mean "you may leave this off" — if you do, the plugin derives a ref from the file/folder name and tells you what it chose. | `… matter: powell-builders` |
| `KEY=VALUE` | The install-time consent flag: the KEY is literally `consent_local_processing`, the VALUE literally `true`. Type it exactly as shown; nothing to substitute. | `--config consent_local_processing=true` |
| `<date>` / `<run-id>` / `<id>` | NOT typed by you — these label things the plugin produces (a run folder like `runs/20261021-a3f2c1/`) or your session id for `claude --resume <id>`. When one matters, the tool prints the real value; copy that. | — |
| `ironfleet-legal:<name>` (agent rows, prompt output) | Internal naming you never type: plugin-prefixed agent names appear in the transcript when stages run. | — |

One naming rule that saves pain: pick the matter `<ref>` once, keep it colon-free, and
use it everywhere — ingest, process-case, and follow-up sessions on the same case all
key the corpus, the workspace and the run history off it.

## 5. Ingest a matter

The repo ships a complete test fixture — [dummy-case-harbour-freight/](../dummy-case-harbour-freight/)
with [TEST-CHECKLIST.md](../dummy-case-harbour-freight/TEST-CHECKLIST.md) (synthetic
parties, checkable ground truths). Copy it onto the machine and run:

```
/ironfleet-legal:ingest dummy-case-harbour-freight/docs matter: harbour-freight
```

Generic form: `/ironfleet-legal:ingest <folder-or-file> matter: <colon-free-ref>`

Verified live: 5 markdown/text docs → 10 chunks, sha256-idempotent, zero skips.
**FRICTION (recorded):** files under 200 words are RECORDED-AND-SKIPPED (the
scanned-source floor) — a short note will not silently enter the corpus; give it real
content or merge it into a larger file. PDFs ride the same chain (MarkItDown → pypdf →
raw text) in a killable subprocess; a hang is skipped, never stuck.

**Answer-key hygiene:** ingest the `docs/` subfolder, never the fixture's root folder —
the root also holds TEST-CHECKLIST.md (the answer key) and verify-report.md, and once
they are in the corpus the run can read them (found live 2026-11-04).

### 5b. Optional: your law library (`/sync-law`)

Without statutes in the corpus, every legal authority a run cites is `[NOT IN CORPUS]`
and provisional. To ground the law, download the Acts yourself from
legislation.govt.nz (your own browser — the plugin never fetches; NZLII is never a
source, even downloaded by hand) into a folder, then:

```
/ironfleet-legal:sync-law nz-statutes
```

Generic form: `/ironfleet-legal:sync-law <folder> [matter: law|law-judgments]` —
statutes default to matter `law`; judgment copies go to `law-judgments` (what the
citator reads). The command reports each file NEW or REFRESHED and states the matter's
currency date. For the dummy case, the statutes it turns on are listed in
TEST-CHECKLIST.md §5.

## 6. Run the pipeline

```
/ironfleet-legal:process-case Our client Southern Haulage Ltd is owed money by Harbour
Freight Solutions Ltd. Advise: can we win, what do we file, and how do we minimise
damage given the bank? matter: harbour-freight
```

Generic form: `/ironfleet-legal:process-case <your ask> matter: <ref>` — grade the run
against the checklist's seven ground truths.

One prompt in; nine agent stages out (intake → research → strategy → attack → assess →
filings → advice → verify → close); deliverables land in `matters/<ref>/` with
provenance headers; the run ledger (`run.json` + `trace.jsonl` + `RECORD.md`) lands in
the same workspace's `runs/`. Expect 25–40 minutes of agent work.

Live verification (2026-10-21, the run that produced this guide): stages land their
deliverables progressively — `case-summary.md`, `fact-questions.md`, `research-memo.md`,
`case-theory.md` were on disk mid-run with the `runs/` ledger writing alongside.

Completion record (2026-11-04, Windows 11, public install, five Acts ingested into the
matter): 9/9 stages, 10 deliverables, verify gate 22 verified / 0 ungrounded, all seven
checklist ground truths met. The run caught a working-day gap in the deadline kernel
(fixed in 0.3.2) and three citation errors in the checklist itself (corrected).

### 6b. Walk through the result (`/explain`)

```
/ironfleet-legal:explain harbour-freight
```

Reads the finished run back in plain English — the answer, then each point with its
passage, a link to it, the corpus source, and a verdict re-verified now. Writes no file.

## 6c. New in 0.5.0: the moot gate, hearing pack, mock hearing (`/moot`, `/hearing-pack`, `/mock-hearing`)

Three new commands close the loop from draft to courtroom, plus five new agents
(opposing-counsel, bench, procedural-examiner, evidence-examiner, hearing-coach) and
two new tools (`ironfleet_moot_check`, `ironfleet_flaw_ledger`). The rule they
enforce: **nothing is marked final without a passed gate** — a draft saying
`status: final` without a `moot-gate: PASSED <run_id>` line is refused by a Write
hook before it lands.

### `/moot` — attack the draft before the court does

What it does: a mechanical pre-pass (every quote and authority checked against your
corpus, every date against the kernel-computed deadlines, every exhibit against the
evidence register, any statutory demand re-validated by the kernel), every flaw
logged to the ninth dossier register, then up to four adversarial rounds where the
crew fixes each attack or answers it in prose. How to use:

```
/ironfleet-legal:moot powell-builders matters/powell-builders/advice-letter.md
```

Two consecutive clean rounds → the defensibility report carries
`moot-gate: PASSED <run_id>` and the draft may be marked final. Still flawed after
four rounds → `CAPPED`: the flaws are listed, never hidden, and the draft stays
non-final until you rule on them. The gate measures the mechanical floor plus the
judgement rounds — it does NOT promise a court accepts the document.

### `/hearing-pack` — everything you bring to the hearing

What it does: assembles the pack from the dossier and the moot report — the bring
list (every registered exhibit with copies count), a three-sentence opening script
(one corpus pin per claim), likely bench questions with model answers, a
cross-examination plan, an objection cheat-sheet ("if they say X, you say Y" per
flaw class), and the surprise protocol for documents not in the record. How to use:

```
/ironfleet-legal:hearing-pack powell-builders
```

Run it after `/moot` — the pack flags at the top if the draft never passed the gate.

### `/mock-hearing` — the rehearsal

What it does: the hearing-coach plays bench AND opposing counsel, hardest questions
first, one question at a time. You answer; the coach critiques each answer (what was
good, what was weak, the sharper record-pinned answer) and never answers for you.
How to use:

```
/ironfleet-legal:mock-hearing powell-builders 10
```

Ends with the rehearsal transcript saved to the matter workspace and your top-3 weak
spots; it will offer a focused second rehearsal. Requires `/hearing-pack` first —
the rehearsal feeds on its bench Q&A.

## 7. Headless / CI driving (optional, how this was verified)

```bash
claude -p "/ironfleet-legal:ingest matter-docs matter: powell-builders" \
  --allowedTools "mcp__plugin_ironfleet-legal_ironfleet__*"
claude -p "/ironfleet-legal:process-case <ask> matter: <ref>" \
  --allowedTools "mcp__plugin_ironfleet-legal_ironfleet__*,Task,Read,Write,Edit,Glob,Grep"
claude -p "run the IronFleet doctor preflight" \
  --allowedTools "Bash,Read,Glob,Grep,mcp__plugin_ironfleet-legal_ironfleet__*"
```

The doctor needs `Bash` in `--allowedTools` — its checks run `curl`, `python -c` and
`manage-bde` themselves (found live 2026-10-26: scoped to the MCP wildcard alone, the
doctor honestly printed "NOT RUN — blocked" for every shell check instead of guessing;
only check 2 passed).

**FRICTION (recorded):** a headless `process-case` on a freshly-ingested SYNTHETIC
fixture may still pause at the safety checkpoint — the fixture documents are labeled
SYNTHETIC and the stage agent cannot see that you ingested them moments earlier.
Send one follow-up `claude -p` confirming the corpus is intentional and the run
completes; the first run folder is marked `superseded` with `superseded_by` pointing
at the new run_id, so the debug ladder never dead-ends on an abandoned folder.

**FRICTION (recorded):** on a machine whose Claude Code authenticates through a local
gateway (`apiKeyHelper` + `ANTHROPIC_BASE_URL` in settings.json), the standalone CLI
may report `Not logged in` when its own OAuth has expired. The env-key route works
without changing any file: export `ANTHROPIC_API_KEY` from your key-helper for the
child process. Otherwise run `claude /login` once interactively.

## Claude Desktop / Cowork

Customize → Plugins → **Add marketplace** → `BasimBashir/ironfleet-legal` → Install. Cowork
runs the local stdio MCP because the session is on your machine; claude.ai chat ignores
local MCP servers (skills and agents still work there, with the corpus honestly
degraded — drafts carry `[NO CORPUS STORE — attach documents directly]`).

## macOS notes (from the SL tester's fresh run, 2026-10-26)

- **Use Homebrew python** (`brew install python@3.12`) — the python.org/Apple framework
  build cannot LOAD SQLite extensions (`enable_load_extension` missing), so sqlite-vec
  imports but never loads and ingest fails. Install §2's deps on brew's python with
  `--break-system-packages`, and point the `python` alias at it.
- **`python` vs `python3`:** macOS ships `python3` only; the plugin's MCP config
  invokes `python`. Fix: brew's python provides both once linked, or
  `ln -sf "$(command -v python3)" /usr/local/bin/python`.
- **Ollama must be RUNNING:** launch the app (`open -a Ollama`) or `ollama serve`;
  installed-but-not-started fails doctor check 5 until :11434 answers.
- Store path: `~/Library/Application Support/IronFleet/harness` — doctor resolves it;
  never hand-build it.
- Volume encryption is FileVault (`fdesetup status`) — doctor check 9.

## Linux notes (verified live on fresh Ubuntu 24.04 in a VM, 2026-10-22)

- **`python` vs `python3`:** Ubuntu ships `python3` only; the plugin's MCP config
  invokes `python`. Fix (either): `sudo apt install python-is-python3`, or no-sudo
  `mkdir -p ~/.local/bin && ln -sf "$(command -v python3)" ~/.local/bin/python`.
  Same story on macOS without a `python` alias. Doctor check 1 names this exactly.
- **PEP 668:** Ubuntu 23.04+ refuses bare pip user installs
  (`externally-managed-environment`). Add `--break-system-packages` to the pip
  commands in §2.
- **Store path case matters:** Linux uses lowercase `~/.local/share/ironfleet/harness`
  (XDG). Doctor resolves it via the plugin's own code — never hand-build the path.
- **markitdown is optional** (rich-format parsing); plaintext/markdown/PDF corpora
  never need it. `yaml` is likewise never needed by the plugin's own tools.
- CPU-only embedding in a VM is slow: a 5-document matter is minutes; a 30-judgment
  corpus is hours. Start matters small.

## Windows notes

- Install CPython from python.org with "Add to PATH" — the installer provides `python`.
- The encryption check (`manage-bde`) needs an **Administrator** terminal; from a
  normal one it reports indeterminate and privileged matters stay gated.
- **Ollama** (found live 2026-10-26): the installer is ~1.6 GB — not a few-hundred-MB
  download. It silent-installs, but a first-run ONBOARDING WINDOW still opens
  ("Create an account" → "Run Ollama"): choose the local/no-account option or just
  close it — the background service and the `ollama` CLI work regardless of whether
  that window is dismissed.
- If `ollama` is "not found" right after a silent install, open a NEW terminal —
  PATH is cached per-shell (or call it by full path
  `%LOCALAPPDATA%\Programs\Ollama\ollama.exe`).
