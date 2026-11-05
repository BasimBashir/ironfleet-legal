---
description: The do-this-now list — open deadlines, the latest strategy's next actions, unresolved predictions
argument-hint: "[matter: <ref>]"
---

# Next actions (M5 dossier loop)

**Matter:** $ARGUMENTS

Mechanical assembly, read-only: three sources, one ranked list, no new opinions.

1. **Resolve the matter + workspace** (same rules as `/process-case`). Empty
   argument → ask.
2. **Gather the three sources:**
   - `ironfleet_dossier_read` entity=deadlines — keep status `overdue` and
     `due_soon` (the tool computed them against today; do not recompute);
   - `ironfleet_dossier_read` entity=strategy — the latest version's
     `next_actions`, in its own order;
   - `ironfleet_dossier_read` entity=predictions — the `unresolved` ids with their
     claims (each is waiting on the next court round, not on the user — list them
     as "watching", not "doing").
3. **Render:**

```
## Do now — <matter>

1. [overdue <due>] <what> — <rule> — <missed_consequence>
2. [due_soon <due>] <what> — <rule>
3. [strategy v<N>] <next_action>
...

Watching (resolved by the court, not by you):
- <prediction_id> (v<version>): <claim>
```

Overdue first, then due_soon by date, then the strategy's next actions. If all
three sources are empty, say exactly that: "no open deadlines, no next_actions in
the latest strategy, no unresolved predictions — run /debrief after the next court
round."

## House rules (binding)

- Read-only: never appends, never registers.
- Every date shown carries the kernel rule string from its register row.
- Do not invent a next action the strategy does not list; if the list is stale,
  say so and point at /debrief.
