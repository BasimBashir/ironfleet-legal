# IronFleet Legal — a NZ paralegal in Claude (and Codex, Grok, OpenCode, Pi, Hermes, …)

One plugin turns Claude — or any of the agent harnesses below — into an end-to-end New
Zealand legal assistant: ingest a matter's
documents into a **local, citation-exact corpus**, run a **nine-stage multi-agent case
pipeline** with one prompt, and get court-ready deliverables — `advice-letter.md`,
`filings-roadmap.md`, `win-assessment.md` (PROCEED vs MINIMUM-DAMAGE), `citation-check.md`,
`closing-summary.md` — every quote verbatim from your own corpus, every deliverable
provenance-stamped, every run leaving a complete paper trail.

## What it does

- **`/ironfleet-legal:process-case <one prompt>`** — the crew runs: intake → research →
  strategy → attack (opposing counsel) → assessment → filings roadmap → advice letter →
  citation check → close. Nine specialist agents, each in its own fresh context, each
  writing its own deliverable, with conditional checkpoints (you are interrupted only
  when it matters).
- **`/ironfleet-legal:ingest <path>`** — files or folders into the matter's RAG store:
  structure-aware chunking, hybrid lexical+vector+citation retrieval, local embeddings.
- **Citation-exact by construction** — drafts emit `[E.n.S.n]` references against corpus
  passages; ungroundable citations are flagged `[NOT IN CORPUS]`, never invented.
- **Everything traceable** — every run writes `run.json` + `trace.jsonl` + `RECORD.md`
  into the matter workspace; every deliverable carries a provenance header; the debug
  ladder is RECORD.md → trace.jsonl → the native Claude session transcript.
- **Fail-closed citation gate** — before the advice letter ships, every quote is
  byte-checked against the corpus (`ironfleet_verify_document`); an adversary
  pre-mortem (`ironfleet_objection`) flags mismatched dates, an uncomputed statutory
  demand, or privileged sources quoted in open documents. Each deliverable carries an
  AI-use disclosure built from the run's own trace.
- **Mechanical-only MCP** — the plugin's local tools (corpus search, quote verifier,
  citator, statutory-demand kernel, without-prejudice detector, working-day deadline
  arithmetic) make ZERO LLM calls. The intelligence is your own Claude account (or
  whatever model your harness runs); embeddings run on your local Ollama. Nothing in
  this plugin egresses.

## Install

Claude Code:
```bash
claude plugin marketplace add BasimBashir/ironfleet-legal
claude plugin install ironfleet-legal@ironfleet-legal --config consent_local_processing=true
```
Claude Desktop / Cowork: Customize → Plugins → **Add marketplace** →
`BasimBashir/ironfleet-legal` → Install. Full first-run walkthrough:
[docs/FRESH-OS-SETUP.md](docs/FRESH-OS-SETUP.md).

### Other harnesses

The same repo installs natively in other agent harnesses — one source of truth, no
copies. Every harness gets the 25 MCP tools and the 27 skills; how the 11 commands,
the 19 stage agents and the moot gate arrive differs, and is spelled out per harness
in [docs/FRESH-OS-SETUP.md §1b](docs/FRESH-OS-SETUP.md#1b-other-harnesses).

| Harness | Install |
|---|---|
| OpenAI Codex (CLI + app) | `codex plugin marketplace add BasimBashir/ironfleet-legal` then `codex plugin add ironfleet-legal@ironfleet-legal` |
| xAI Grok Build | `grok plugin install BasimBashir/ironfleet-legal --trust` |
| GitHub Copilot CLI | `copilot plugin marketplace add BasimBashir/ironfleet-legal` then `copilot plugin install ironfleet-legal@ironfleet-legal` |
| OpenCode (≥ 1.18.29 or 2.x) | add `"ironfleet-legal@git+https://github.com/BasimBashir/ironfleet-legal.git"` to `plugin` (1.x) / `plugins` (2.x) in `opencode.json` |
| Pi | `pi install git:github.com/BasimBashir/ironfleet-legal` |
| Hermes Agent | `hermes plugins install BasimBashir/ironfleet-legal --enable` then `hermes ironfleet setup` |
| DeepSeek Harness (dsh) | `git clone https://github.com/BasimBashir/ironfleet-legal ~/.dsh/ironfleet-legal` then `python ~/.dsh/ironfleet-legal/scripts/install_dsh.py` |
| Cursor (and Grok Bot, which uses Cursor's plugin library) | `cursor-agent plugin marketplace add https://github.com/BasimBashir/ironfleet-legal`, then install from `/plugin` |
| Gemini CLI | `gemini extensions install https://github.com/BasimBashir/ironfleet-legal` |
| Factory Droid | `droid plugin marketplace add https://github.com/BasimBashir/ironfleet-legal` then `droid plugin install ironfleet-legal@ironfleet-legal` |
| Qwen Code | `qwen extensions install BasimBashir/ironfleet-legal:ironfleet-legal` |
| Anything else with MCP + Agent Skills | the one MCP entry + skills path in [FRESH-OS-SETUP §1b](docs/FRESH-OS-SETUP.md#1b-other-harnesses) |

Outside Claude Code, commands are also reachable by name from any harness: ask for
"IronFleet process-case: <your ask>" and the agent fetches the workflow with
`ironfleet_command`. Then run the doctor skill first, as on Claude.

## Commands

The plugin ships eleven commands (type `/ironfleet-legal:` in a session to see them):

| Command | What it does |
|---|---|
| `/ironfleet-legal:doctor` | Preflight: checks this machine and prints the exact fix for anything missing |
| `/ironfleet-legal:ingest <path> [matter: <ref>]` | Your matter documents into the local corpus |
| `/ironfleet-legal:sync-law <folder> [matter: law]` | Statutes/judgments YOU downloaded into the corpus, with a currency date |
| `/ironfleet-legal:process-case <ask> [matter: <ref>]` | The nine-stage crew: one prompt in, court-ready deliverables out |
| `/ironfleet-legal:explain <ref>` | Plain-English walkthrough of a finished run, every passage re-verified |
| `/ironfleet-legal:debrief <matter> [minute]` | Court round in, prediction-vs-outcome diff, strategy vN+1, kernel deadlines |
| `/ironfleet-legal:case-status <matter>` | One-screen dossier card: deadlines, open predictions, latest strategy |
| `/ironfleet-legal:next-actions <matter>` | The do-this-now list: overdue + due-soon deadlines, strategy actions |
| `/ironfleet-legal:moot <matter> <draft>` | The moot gate: attack a draft until it survives, then mark it final-capable (see below) |
| `/ironfleet-legal:hearing-pack <matter>` | The hearing pack: bring list, opening script, bench Q&A, cross-exam plan, objection cheat-sheet |
| `/ironfleet-legal:mock-hearing <matter>` | Rehearsal: the coach plays bench and opposing counsel and critiques every answer you give |

A complete worked example lives in this repo:
[dummy-case-harbour-freight/](dummy-case-harbour-freight/) — five synthetic case
documents engineered with checkable traps (a time-barred invoice, a voidable-preference
payment, a late PPSA registration, a penalty-rate clause), plus
[TEST-CHECKLIST.md](dummy-case-harbour-freight/TEST-CHECKLIST.md) with the ground truths
to grade the output against. Copy that folder onto any machine and run the sequence
below end to end. The citation check is itself a public benchmark anyone can re-run
offline in ~1s — [dummy-case-harbour-freight/verify-report.md](dummy-case-harbour-freight/verify-report.md)
has the command and the current published result.

### `/ironfleet-legal:doctor` — preflight

Verifies the corpus machinery on this machine: MCP server boot (the real test), Python,
sqlite-vec, Ollama + bge-m3, optional reranker, store writability, volume encryption —
and prints the EXACT fix command for anything missing.

```
/ironfleet-legal:doctor
```

Example verdict: `DEGRADED — corpus machinery fully up; optional reranker down (search
degrades to fusion order); volume encryption indeterminate from a non-admin shell
(privileged matters gated until confirmed)`.

### `/ironfleet-legal:ingest <path> [matter: <ref>]` — documents into the corpus

```
/ironfleet-legal:ingest dummy-case-harbour-freight/docs matter: harbour-freight
```

Expected on the dummy case: 5 files, ~10 chunks, 0 skipped (point at the `docs/`
subfolder — TEST-CHECKLIST.md is the answer key and must NOT be ingested). Re-running
is free (sha256 resume). Scanned/no-text files are recorded-and-skipped, never silently
embedded.

### `/ironfleet-legal:process-case <your ask> matter: <ref>` — the whole crew

```
/ironfleet-legal:process-case Our client Southern Haulage Ltd is owed money by Harbour
Freight Solutions Ltd. Advise: can we win, what do we file, and how do we minimise
damage given the bank? matter: harbour-freight
```

One prompt in, nine agent stages out: intake → research → strategy → attack (opposing
counsel) → assess (win probability, PROCEED vs MINIMUM-DAMAGE) → filings roadmap →
advice letter → citation check → close. On the dummy case, a correct run: excludes the
time-barred 2019 invoice, flags the 3 Aug 2026 payment as voidable-preference exposure
(Companies Act 1993 ss 292/296), catches the late PPSA registration (unperfected 2019–2025,
outside the s 73 PMSI window), tests the 26% rate against penalty doctrine, validates any statutory demand
through the kernel ($1,000 minimum; 15 working days), and marks every authority not in
your corpus `[NOT IN CORPUS]`. Deliverables land in `matters/harbour-freight/` with
provenance headers; the run ledger (`run.json`, `trace.jsonl`, `RECORD.md`) lands in
`runs/`.

A typical case takes 25–40 minutes of agent work on a Max plan. Expect one checkpoint
question at most — the crew proceeds on recorded assumptions otherwise.

Re-running process-case on the same matter is safe: an earlier run still marked
`running` is marked `superseded` (with `superseded_by` pointing at the new run), so
the run history never dead-ends on an abandoned folder.

### `/ironfleet-legal:sync-law <folder> [matter: law]` — your law library

Without statutes in the corpus, every legal authority in a run is marked
`[NOT IN CORPUS]` and stays provisional. To ground the law too, download the Acts
yourself (legislation.govt.nz, in your own browser — the plugin never fetches) into a
folder, then:

```
/ironfleet-legal:sync-law nz-statutes
```

Each file is reported NEW or REFRESHED, and the `law` matter gets a currency date that
later verification reports carry ("current as of …"). Judgment copies go to
`matter: law-judgments`, which the citator reads. **NZLII content is never a source,
even downloaded by hand** — its usage policy bars embedding.

### `/ironfleet-legal:explain <ref>` — the walkthrough

```
/ironfleet-legal:explain harbour-freight
```

Reads a finished run back in plain English: the direct answer, then each point of the
advice with the passage quoted, a clickable link to it, the corpus source it matched,
and a fresh verification verdict (re-checked now, not trusted from the run). It adds
no new analysis and writes no file; anything unverified is shown loudly as such.

## What's new in 0.4.0 — the case dossier and the debrief loop

The plugin now keeps a per-matter **case dossier**: eight append-only registers —
facts, evidence, strategy versions, proposals, predictions, court events, deadlines,
outcomes — as local JSONL next to the records ledger, with a `case-manager` agent as
the single writer. On top of it:

- **`/ironfleet-legal:debrief <matter> [minute]`** — after a court round: the minute
  (or order) is ingested, every open prediction is diffed mechanically against what
  the court actually decided, the case-manager records one outcome verdict per
  prediction (match is judgement, stored as data), the strategist cuts strategy
  vN+1, and every new deadline is registered **kernel-computed** — a model-supplied
  date is refused outright.
- **`/ironfleet-legal:case-status <matter>`** — read-only one-screen card: deadline
  clock (ok/due_soon/overdue, computed against today by the tool, never softened by
  the model), open proposals, court rounds, unresolved predictions, latest strategy.
- **`/ironfleet-legal:next-actions <matter>`** — the do-this-now list assembled
  mechanically from three sources: overdue + due-soon deadlines, the latest
  strategy's next actions, and the predictions "watching" for the next round.
- **Corpus CRUD:** `ironfleet_delete_docs` removes one document (docs row, FTS,
  citation keys, vectors) and `ironfleet_reingest` re-ingests an edited source as a
  deliberate replace — sha256 resume alone cannot pick up an edit.
- **Reproducible grading, extended:** `python tests/grade_dummy_case.py` now also
  takes the dummy case through TWO simulated court rounds offline (debrief → diff →
  strategy v2 → v3, outcomes recorded, kernel parity asserted) plus the CRUD
  roundtrip — exit 0 proves the whole loop. See
  [CHANGELOG.md](CHANGELOG.md) for the full history.

## What's new in 0.6.0 — every harness, one source of truth

- **Installs natively in 11 more harnesses** (table above): Codex, Grok Build and
  Copilot read the Claude plugin layout (Codex through its own
  `.codex-plugin/plugin.json`, because it does not expand `${CLAUDE_PLUGIN_ROOT}`);
  OpenCode, Pi and Hermes get thin adapters (`opencode/index.js`, `pi/extension.ts`,
  `__init__.py`) that read the same `skills/`, `commands/`, `agents/` and
  `mcp/server.py`; DeepSeek Harness gets `scripts/install_dsh.py`.
- **The kit travels over MCP:** the server now serves the 11 commands as MCP prompts,
  plus `ironfleet_command` (a command's instructions by name),
  `ironfleet_agent_brief` (a stage agent's brief by name) and `ironfleet_plugin_info`
  — 25 tools. Harnesses that cannot load our agent files still dispatch every stage
  from its exact brief; a stage that has to run inline is logged as such.
- **The moot gate is harness-agnostic:** one script now reads every write shape
  (Claude Write/Edit, Codex `apply_patch`, Grok's camelCase payload, OpenCode, Pi
  `edits[]`, Hermes `write_file`/`patch`). Where a harness runs no pre-write hook,
  the commands tell the agent it is the gate.
- **Fix:** the `nz-statutory-demand-validator` skill's frontmatter did not parse as
  YAML (its metadata loaded empty); it now validates under `claude plugin validate
  --strict`.

## What's new in 0.5.0 — the moot gate and hearing prep

Nothing is marked final without a passed gate. A draft that declares itself final
(the exact line `status: final`) must carry a `moot-gate: PASSED <run_id>` marker —
a **Write/Edit hook denies the write otherwise**. A CAPPED draft (still flawed after
4 attack rounds) is never marked final: it goes to approval with every flaw listed.
The fleet grows to 19 agents (+opposing-counsel, bench, procedural-examiner,
evidence-examiner, hearing-coach) and 22 tools (+`ironfleet_moot_check`,
`ironfleet_flaw_ledger` — the ninth dossier register, append-only, last-status-wins).

- **`/ironfleet-legal:moot <matter> <draft>`** — the gate itself. What it does:
  runs the mechanical pre-pass (`ironfleet_moot_check`: quotes/refs vs the corpus,
  dates vs the run's kernel computations, unregistered exhibits, statutory-demand
  form re-validated by the kernel, citator as informational minors), logs every flaw
  to the ledger, then up to 4 adversarial rounds — the drafting crew fixes or answers
  each attack in prose. How to use:

  ```
  /ironfleet-legal:moot powell-builders matters/powell-builders/advice-letter.md
  ```

  Two consecutive clean rounds → the defensibility report carries
  `moot-gate: PASSED <run_id>` and the draft may be marked final. Open flaws after
  4 rounds → `CAPPED`: the flaws are listed, never hidden, and the draft stays
  non-final. The gate measures the mechanical floor plus judgement rounds — it does
  NOT promise a court accepts the document.
- **`/ironfleet-legal:hearing-pack <matter>`** — what it does: assembles the hearing
  pack from the dossier and the latest moot report — bring list (every registered
  exhibit + copies), opening script (one corpus pin per claim), bench questions with
  model answers (the **bench** agent), cross-examination plan, objection cheat-sheet
  ("if they say X, you say Y" per flaw class), surprise protocol for unverified
  documents. How to use:

  ```
  /ironfleet-legal:hearing-pack powell-builders
  ```

  Run it after `/moot` — a draft that never passed the gate is flagged at the top
  of the pack.
- **`/ironfleet-legal:mock-hearing <matter> [rounds]`** — what it does: rehearsal.
  The **hearing-coach** agent plays bench AND opposing counsel, hardest questions
  first; you answer aloud (the orchestrator relays, never answers for you) and after
  each answer you get good / weak / sharper-answer, pinned to the record. How to use:

  ```
  /ironfleet-legal:mock-hearing powell-builders 10
  ```

  Ends with the rehearsal transcript (saved to the matter workspace) and your top-3
  weak spots; offer of a focused second rehearsal. Feeds on the hearing pack.
- **Seeded-flaw eval, in-repo:** `tests/moot-eval/` holds 30 flawed documents
  (6 per class: wrong deadline, fabricated case, misquote, missing exhibit,
  wrong form) + 4 clean controls; `tests/test_moot_eval.py` runs the gate over all
  34 and holds the line at **≥ 0.90 detection, 0 false positives on the controls**
  — measured 30/30 (1.00) with 0 FPs on this build, deterministic floor only.
  `python tests/grade_dummy_case.py` now grades the gate too (exit 0).

## What changed since 0.1.0

If you installed 0.1.0, refresh the plugin (the installed copy is a cache and does not
update itself), then **start a new Claude session** — the corpus tools bind when a
session starts:

```bash
claude plugin uninstall ironfleet-legal@ironfleet-legal
claude plugin install ironfleet-legal@ironfleet-legal --config consent_local_processing=true
```

Your corpus and past runs are untouched — they live in the plugin's store and your
matter folders, not in the plugin cache. What you will notice:

- **Two new commands:** `/sync-law` (your own law library) and `/explain` (the
  walkthrough). `/doctor` is now typeable on every CLI build.
- **Citation gate:** the advice letter is not finished until every quote verifies
  against the corpus; failures are fixed or ruled on in the run, never smoothed over.
- **Statutory demands are always computed:** a draft that relies on a statutory
  demand without a logged kernel run is objected to mechanically.
- **NZ deadlines respect the Christmas closure** (0.3.2): working-day arithmetic
  skips 25 Dec–2 Jan and the Mondayised early-January days, per Companies Act 1993
  s 2 — earlier versions put a deadline spanning Christmas several working days early.
- **Better paper trail:** `run.json` updates after every stage, stale runs are marked
  superseded, every deliverable (closing summary included) carries a provenance
  header and an AI-use disclosure.
- **Research sweep:** every run now checks limitation, the PPSA registration window,
  every transfer against the voidable-transaction rules, statutory-demand viability
  and penalty doctrine.
- **AU/UK packs:** jurisdiction data for Australia and the UK alongside NZ.
- **Setup:** Linux and macOS work out of the box with the per-OS notes in
  [docs/FRESH-OS-SETUP.md](docs/FRESH-OS-SETUP.md) (macOS needs Homebrew python).

## Privacy (read for privileged work)

Your corpus, records and deliverables live on YOUR machine, under the plugin's store root
(encrypted-volume enforced by doctor). Matter text you share in conversation enters your
Claude account's context — consumer plans retain transcripts up to 30 days (5 years if
model training is enabled); prefer **Team/Enterprise with training OFF** for privileged
matters. In another harness the same applies to whichever model provider it is
configured for: check that provider's retention and training terms, or run a local
model. The plugin ships no corpus content and never phones home.

## Licence & attribution

MIT for the plugin's own code and IronFleet-authored skills; adapted skills carry their
upstream licences — see [ATTRIBUTION.md](ATTRIBUTION.md). Note: one adapted skill
(`nz-contract-reviewer`) is distributed against its upstream's no-derivatives terms at
the repository owner's election — see the attribution note.

Not legal advice. Output is drafted assistance for legal professionals — a qualified
New Zealand lawyer reviews everything before filing.
