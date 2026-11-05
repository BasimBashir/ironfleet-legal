---
description: Assemble the hearing pack — what to bring, opening script, bench Q&A, cross-exam plan, objection cheat-sheet
argument-hint: "[matter: <ref>] [hearing date, if set]"
---

# Hearing pack

**Input:** $ARGUMENTS

You are the ORCHESTRATOR for the hearing pack on one matter. Everything in the
pack must trace to the dossier, the moot-gate report, or the evidence register
— nothing is asserted from memory of "how hearings usually go".

## Setup

1. **Matter ref** from $ARGUMENTS; workspace `matters/<matter-ref>/`. Read the
   dossier (strategy latest, facts, evidence, deadlines with today-relative
   status) and the latest defensibility report. A draft that never passed the
   moot gate gets flagged AT THE TOP of the pack.
2. **Bring list:** every registered exhibit (label + file), copies count, the
   draft + defensibility report, the run ledger run_id. Dates in the pack come
   from `ironfleet_dossier_read` entity=deadlines (kernel-sourced), never from
   you.

## The pack

1. **Opening script** — three sentences: who we act for, what we seek, why on
   the record (one corpus pin per claim).
2. **Bench questions & answers** — dispatch the **bench** agent on the matter;
   paste its Q&A verbatim. Flag any Q the record cannot answer — that is a
   risk to carry, not to hide.
3. **Cross-examination plan** — for each opposing witness/document: the three
   questions that make the gap (from the evidence-examiner's attacks).
4. **Objection cheat-sheet** — the moot-gate flaw classes as one-line "if they
   say X, you say Y" rows, each with the record pin.
5. **Surprise protocol** — what to do if they raise an authority or exhibit
   NOT in the record: ask for adjournment to verify; never argue an unverified
   document on its feet. State plainly: the pack prepares the hearing; it does
   NOT promise the court accepts anything.
