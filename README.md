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

## First run

1. `/ironfleet-legal:doctor` — verifies Python, sqlite-vec, Ollama + bge-m3 (optional
   reranker), store writability and volume encryption, and prints the exact fix command
   for anything missing.
2. Drop your matter documents in a folder and `/ironfleet-legal:ingest <folder>`.
3. `/ironfleet-legal:process-case process my docs — can I win, and how do I file?`

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
upstream licences — see [ATTRIBUTION.md](ATTRIBUTION.md). One adapted skill
(`nz-contract-reviewer`, CC-BY-NC-ND upstream) is deliberately **not distributed**.

Not legal advice. Output is drafted assistance for legal professionals — a qualified
New Zealand lawyer reviews everything before filing.
