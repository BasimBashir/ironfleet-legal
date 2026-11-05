---
description: One-screen case status — dossier registers, deadline clock, open predictions, latest strategy
argument-hint: "[matter: <ref>]"
---

# Case status (M5 dossier loop)

**Matter:** $ARGUMENTS

You are the READ-ONLY reporter for one matter's dossier. You append nothing.

1. **Resolve the matter + workspace** (same rules as `/process-case`; colon-free
   ref, workspace `matters/<matter-ref>/`). If the argument is empty, ask.
2. **Read every register** — `ironfleet_dossier_read` for facts, evidence, strategy,
   proposals, predictions, court_events, deadlines, outcomes (eight calls).
   Also `ironfleet_list_docs` for corpus shape if the user asks about documents.
3. **Render the status card** (mark down, in this order):

```
## Case status — <matter>   (dossier read <today>)

**Latest strategy:** v<N> — <why_changed> (<file>)
**Deadlines:** <due>: <what> — <status ok/due_soon/overdue>   (or "none registered")
**Open proposals:** <status: proposal>                        (or "none")
**Court rounds:** <N> — latest <date>: <event_type>, <first order…>
**Unresolved predictions:** <id> (v<version>): <claim>        (or "none — all resolved")
**Facts of record:** <field>: <latest value>                  (top 5 by recency)
**Outcomes so far:** <n> recorded, <m> matches
```

4. **Then one line of honesty:** anything the dossier does NOT know (e.g. no
   predictions yet, no deadline clock running) and what would fix it.

## House rules (binding)

- Every date you show comes from a register; deadlines show the kernel rule string.
- Statuses (`ok/due_soon/overdue`) are the tool's projection against today — never
  recomputed or softened by you.
- Read-only: this command never appends to the dossier, never registers a deadline.
