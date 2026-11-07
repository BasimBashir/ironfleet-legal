---
description: Run the moot gate on a draft — mechanical pre-pass, agent attack rounds, then PASSED or CAPPED
argument-hint: "[matter: <ref>] [path to the draft]"
---

# Moot gate

**Input:** $ARGUMENTS

You are the ORCHESTRATOR for one moot-gate run on one draft. The principle:
nothing is marked final without a passed gate, and a CAPPED draft is never
marked final — it goes to approval with its flaws listed. The gate's floor is
mechanical (kernels + corpus); the rounds are adversarial judgement on top.
Agents named below are dispatched per the dispatch rule: Claude Code
`ironfleet-legal:<name>`; elsewhere your harness's subagent `<name>`, or
`ironfleet_agent_brief` handed to a fresh subagent; inline only when the harness has
no subagents (log an `exception` event saying so). Where the harness runs no
pre-write hook (see docs/FRESH-OS-SETUP.md per harness), YOU are the gate: never
write `status: final` into a document without its `moot-gate: PASSED` line.

## Setup

1. **Matter ref + draft path** from $ARGUMENTS (colon-free ref; workspace
   `matters/<matter-ref>/`). Read the draft. If either is missing, ask.
2. **Mechanical pre-pass:** `ironfleet_moot_check` (matter, path). It runs the
   objection pass (quotes/refs/dates vs the corpus and the run's kernel
   computations), the citator (informational, minor severity, never blocks),
   and the moot-checks (unregistered exhibits, statutory-demand form). Fix the
   CRITICAL/material rows it can fix by editing the draft (real corpus quotes,
   kernel dates, registered exhibits, valid form terms) and re-run until the
   mechanical pass is clean or only prose-answerable rows remain.
3. **The ledger:** append every flaw row to the flaw ledger
   (`ironfleet_flaw_ledger` op=append: flaw_id F1.., class, severity, doc,
   detector). A row the drafter answered in prose is `dismissed` — but ONLY
   with the answer written next to it; a fixed row is `fixed`.

## Rounds (max 4)

Each round, in order: **opposing-counsel** attacks the current draft + flaw
rows; **procedural-examiner** and **evidence-examiner** attack their lanes.
The drafter (you) fixes or answers every CRITICAL/MAJOR attack, re-runs
`ironfleet_moot_check`, and appends the ledger updates. A round is clean when
the mechanical pass is clean AND no agent holds a CRITICAL/MAJOR attack.

## Verdict

- **PASSED <rounds>**: two consecutive clean rounds. Append the marker line
  `moot-gate: PASSED <run_id>` to the defensibility report and the draft
  (the Write hook DENIES any `status: final` write without this marker).
- **CAPPED**: after 4 rounds open CRITICAL/material flaws remain. Write the
  cap report: the flaws (id, class, severity, detector, round), the answers
  attempted, and what each needs (operator ruling, form kernel, new evidence).
  NEVER mark a CAPPED draft final. The hook enforces this.

## Defensibility report (write it either way)

flaws found & fixed (table: id, class, severity, detector, round, status) ·
open flaws (never hidden) · residual risks · "their arguments & your answers"
(one row per opposing-counsel attack) · verdict `PASSED <rounds>` or `CAPPED`
· the `moot-gate:` marker line. Close the run honestly: the gate measures the
mechanical floor plus judgement rounds — it does NOT promise a court accepts
the document.
