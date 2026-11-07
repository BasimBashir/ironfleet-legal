# Changelog

## 0.6.0 (2026-11-07, unpublished)

Every harness, one source of truth:

- Native install paths for Codex (`.codex-plugin/plugin.json`, `hooks/codex-hooks.json`),
  Grok Build / Copilot CLI / Droid / Qwen (the existing Claude layout), Cursor
  (`.cursor-plugin/`), Gemini CLI (`gemini-extension.json`), OpenCode
  (`package.json` + `opencode/index.js`, V1 and V2 plugin APIs), Pi (`package.json`
  `pi` key + `pi/extension.ts` MCP bridge), Hermes Agent (`plugin.yaml` +
  `__init__.py`), DeepSeek Harness (`scripts/install_dsh.py`). `AGENTS.md` explains
  the kit to any agent.
- MCP server: commands served as MCP prompts; new tools `ironfleet_command`,
  `ironfleet_agent_brief`, `ironfleet_plugin_info` (25 tools).
- Moot gate reads every harness's write shape (Write/Edit, `apply_patch`, camelCase
  `toolInput`, `edits[]`, `write_file`/`patch`) and exposes `deny_reason()` for
  in-process adapters.
- Commands carry a harness-neutral dispatch rule; doctor finds the plugin root
  outside Claude Code.
- Fix: `nz-statutory-demand-validator` frontmatter was invalid YAML.
- Tests: 128 (adapters, prompts, gate shapes); grader exit 0.

## 0.4.0 (2026-11-05, unpublished)

The case dossier and the debrief loop (M5 prototype):

- **Case dossier:** eight append-only JSONL registers per matter — facts, evidence,
  strategy versions, proposals, predictions, court events, deadlines, outcomes —
  stored next to the records ledger, projections computed at read (latest fact per
  field, version chain, ok/due_soon/overdue, unresolved predictions).
- **Six new MCP tools:** `ironfleet_dossier_append`, `ironfleet_dossier_read`,
  `ironfleet_debrief_ingest` (the mechanical prediction-vs-outcome diff),
  `ironfleet_deadline_register` (kernel-computed only — a caller-supplied `due` is
  refused), `ironfleet_delete_docs`, `ironfleet_reingest`.
- **Three new commands:** `/debrief` (court round in → diff → outcomes → strategy
  vN+1 → kernel deadlines), `/case-status`, `/next-actions`; plus a `case-manager`
  agent as the single dossier writer.
- **Corpus CRUD:** per-document delete (docs row, FTS chunks, citation keys,
  vectors) and edited-source re-ingest as a deliberate replace.
- **Grading extended:** `python tests/grade_dummy_case.py` now takes the dummy case
  through two simulated court rounds (strategy v1→v3, outcomes recorded, kernel
  parity asserted) and the CRUD roundtrip, fully offline — exit 0 proves the loop.

## 0.3.2 (2026-11-04)

- NZ working-day arithmetic skips the Christmas closure (25 Dec–2 Jan and the
  Mondayised early-January days) per Companies Act 1993 s 2 / PPSA s 16 — a
  deadline spanning Christmas no longer lands several working days early.
- Answer-key citations in the dummy case corrected; docs cover all commands.

## 0.3.1

- SL-test feedback: kernel-use objection (a draft relying on a statutory demand
  without a logged kernel run is objected to mechanically), live run ledger,
  stale runs marked superseded with `superseded_by`, per-OS setup notes.

## 0.3.0

- Citation-auditable release: the fail-closed citation gate (advice letter does not
  ship until every quote verifies), `/sync-law` for operator-downloaded statutes
  and judgments, `/explain` walkthrough, MCP resources (corpus + run ledger),
  AU/UK jurisdiction packs, Linux/macOS setup.

## 0.1.0

- Initial public release: nine-stage `/process-case` crew, local citation-exact
  RAG corpus, `/ingest`, `/doctor`, mechanical-only MCP tools, run ledgers.
