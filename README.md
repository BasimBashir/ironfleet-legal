# IronFleet Legal — a NZ paralegal in Claude

One plugin turns Claude into an end-to-end New Zealand legal assistant: ingest a matter's
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
- **Mechanical-only MCP** — the plugin's local tools (corpus search, statutory-demand
  kernel, without-prejudice detector, working-day deadline arithmetic) make ZERO LLM
  calls. The intelligence is your own Claude account; embeddings run on your local
  Ollama. Nothing in this plugin egresses.

## Install

Claude Code:
```bash
claude plugin marketplace add BasimBashir/ironfleet-legal
claude plugin install ironfleet-legal@ironfleet-legal --config consent_local_processing=true
```
Claude Desktop / Cowork: Customize → Plugins → **Add marketplace** →
`BasimBashir/ironfleet-legal` → Install. Full first-run walkthrough:
[docs/FRESH-OS-SETUP.md](docs/FRESH-OS-SETUP.md).

## Commands

The plugin ships three commands (type `/ironfleet-legal:` in a session to see them).
A complete worked example lives in this repo:
[dummy-case-harbour-freight/](dummy-case-harbour-freight/) — five synthetic case
documents engineered with checkable traps (a time-barred invoice, a voidable-preference
payment, a late PPSA registration, a penalty-rate clause), plus
[TEST-CHECKLIST.md](dummy-case-harbour-freight/TEST-CHECKLIST.md) with the ground truths
to grade the output against. Copy that folder onto any machine and run the sequence
below end to end.

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
(Insolvency Act ss 292/296), catches the late PPSA registration (s 40's 20-business-day
window), tests the 26% rate against penalty doctrine, validates any statutory demand
through the kernel ($1,000 minimum; 15 working days), and marks every authority not in
your corpus `[NOT IN CORPUS]`. Deliverables land in `matters/harbour-freight/` with
provenance headers; the run ledger (`run.json`, `trace.jsonl`, `RECORD.md`) lands in
`runs/`.

A typical case takes 25–40 minutes of agent work on a Max plan. Expect one checkpoint
question at most — the crew proceeds on recorded assumptions otherwise.

## Privacy (read for privileged work)

Your corpus, records and deliverables live on YOUR machine, under the plugin's store root
(encrypted-volume enforced by doctor). Matter text you share in conversation enters your
Claude account's context — consumer plans retain transcripts up to 30 days (5 years if
model training is enabled); prefer **Team/Enterprise with training OFF** for privileged
matters. The plugin ships no corpus content and never phones home.

## Licence & attribution

MIT for the plugin's own code and IronFleet-authored skills; adapted skills carry their
upstream licences — see [ATTRIBUTION.md](ATTRIBUTION.md). Note: one adapted skill
(`nz-contract-reviewer`) is distributed against its upstream's no-derivatives terms at
the repository owner's election — see the attribution note.

Not legal advice. Output is drafted assistance for legal professionals — a qualified
New Zealand lawyer reviews everything before filing.
