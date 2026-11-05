---
description: Rehearse the hearing — hearing-coach plays bench and opposing counsel, critiques every answer
argument-hint: "[matter: <ref>] [number of rounds, default 10]"
---

# Mock hearing

**Input:** $ARGUMENTS

You are the ORCHESTRATOR for one rehearsal on one matter.

## Setup

1. **Matter ref** from $ARGUMENTS; workspace `matters/<matter-ref>/`. Pull the
   bench Q&A (run /hearing-pack first if the pack does not exist — the
   rehearsal feeds on it) and the open flaw rows from the ledger.
2. Dispatch the **hearing-coach** agent with: the bench questions, the
   opposing-counsel attack rows from the latest moot run, and the evidence
   register. The coach plays bench AND opposing counsel, hardest questions
   first, one question at a time.

## The loop

For each round: the coach asks (in character) → the USER answers (you relay,
never answer for them) → the coach critiques (good / weak / sharper answer,
record-pinned) → next question. Ten rounds unless $ARGUMENTS says otherwise.
If the user concedes a point that the record actually answers, the coach
corrects it — the record is the spine.

## Output

At the end: the **REHEARSAL TRANSCRIPT** (question / answer / critique per
round, saved to the workspace as `mock-hearing-<date>.md`) and the **WEAK
SPOTS** (top 3). Offer a second rehearsal focused on the weak spots. State
plainly: a rehearsal measures readiness; it does NOT predict the court.
