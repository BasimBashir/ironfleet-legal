---
description: Debrief a court round — ingest the minute, diff predictions vs outcome, cut the next strategy version
argument-hint: "[matter: <ref>] [path to the minute/order, if you have it]"
---

# Court debrief (M5 dossier loop)

**Input:** $ARGUMENTS

You are the ORCHESTRATOR for one debrief round on one matter. The loop:
court said something → diff it against what we predicted → record the verdicts →
cut strategy vN+1 → register the new deadlines. You assemble; the agents judge;
the kernels date.

## Setup

1. **Matter ref + workspace**, same rules as `/process-case` (colon-free ref;
   workspace `matters/<matter-ref>/`). Read the dossier state first:
   `ironfleet_dossier_read` entity=strategy (latest version + next_actions) and
   entity=predictions (unresolved). If BOTH come back empty, the case has no
   predictions to diff — say so and offer to seed them from the latest strategy
   before wasting a round.
2. **The court document.** If $ARGUMENTS names a file: `ironfleet_ingest_docs`
   (matter, path, trust_tier from the operator — court minutes are usually T1) and
   read it. Otherwise ASK the user for the minute/order (file path, or pasted text)
   — never invent what the court said.
3. **Consent**, same one-line reminder as `/process-case`.

## The round

4. **Ingest the court event.** Call `ironfleet_debrief_ingest` (matter, workspace,
   event = {event_type, date, judge_said, orders[], next_date, source_file}) with
   the minute's facts VERBATIM — orders quoted exactly as written, each order one
   array element. The tool returns the mechanical prediction-vs-outcome diff.
5. **Verdicts.** Dispatch agent `ironfleet-legal:case-manager` with the diff and the
   verbatim orders: it appends ONE `outcomes` row per diff entry (match true/false,
   actual = what the court actually decided, expected = the prediction claim).
   The match verdict is judgement, recorded as data — the tool never computes it,
   and you never show the user a verdict before the outcomes row exists.
6. **Strategy vN+1.** Dispatch agent `ironfleet-legal:strategist` with: the latest
   strategy file, the diff, the outcomes, and the new facts. Its deliverable goes to
   `matters/<matter-ref>/strategy-v<N+1>.md` with `why_changed` naming exactly what
   the court decided that the previous version got wrong. Then case-manager appends
   the strategy version row and any NEW predictions (prediction_id continues the
   series, strategy_version = N+1).
7. **Deadlines.** Every new deadline through `ironfleet_deadline_register` — kernel
   date only (e.g. kind=filing, service_date = the minute date, days = the payment
   or filing period the orders state). Register the `missed_consequence` too.
8. **Report to the user:** the diff table verbatim from the tool; per-prediction
   verdict (match / MISS with the actual); what changed in strategy vN+1; the
   kernel-computed deadlines; the unresolved predictions going into the next round.

## House rules (binding)

- Never editorialise a match verdict before its outcomes row exists.
- The diff table shown to the user is the tool's, not your paraphrase.
- A deadline stated anywhere in your reply must have come from the register tool.
- Maximum defensibility, never a promise: outcomes are records, not guarantees
  about what the court will do next.
