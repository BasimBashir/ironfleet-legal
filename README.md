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
- **Fail-closed citation gate** — before the advice letter ships, every quote is
  byte-checked against the corpus (`ironfleet_verify_document`); an adversary
  pre-mortem (`ironfleet_objection`) flags mismatched dates, an uncomputed statutory
  demand, or privileged sources quoted in open documents. Each deliverable carries an
  AI-use disclosure built from the run's own trace.
- **Mechanical-only MCP** — the plugin's local tools (corpus search, quote verifier,
  citator, statutory-demand kernel, without-prejudice detector, working-day deadline
  arithmetic) make ZERO LLM calls. The intelligence is your own Claude account;
  embeddings run on your local Ollama. Nothing in this plugin egresses.

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

The plugin ships five commands (type `/ironfleet-legal:` in a session to see them):

| Command | What it does |
|---|---|
| `/ironfleet-legal:doctor` | Preflight: checks this machine and prints the exact fix for anything missing |
| `/ironfleet-legal:ingest <path> [matter: <ref>]` | Your matter documents into the local corpus |
| `/ironfleet-legal:sync-law <folder> [matter: law]` | Statutes/judgments YOU downloaded into the corpus, with a currency date |
| `/ironfleet-legal:process-case <ask> [matter: <ref>]` | The nine-stage crew: one prompt in, court-ready deliverables out |
| `/ironfleet-legal:explain <ref>` | Plain-English walkthrough of a finished run, every passage re-verified |

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
matters. The plugin ships no corpus content and never phones home.

## Licence & attribution

MIT for the plugin's own code and IronFleet-authored skills; adapted skills carry their
upstream licences — see [ATTRIBUTION.md](ATTRIBUTION.md). Note: one adapted skill
(`nz-contract-reviewer`) is distributed against its upstream's no-derivatives terms at
the repository owner's election — see the attribution note.

Not legal advice. Output is drafted assistance for legal professionals — a qualified
New Zealand lawyer reviews everything before filing.
