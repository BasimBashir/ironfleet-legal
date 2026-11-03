# G1 benchmark — `ironfleet_verify_document` run it yourself

**What this proves:** the 0.2.0 thesis, mechanically. 0.1.0 promised "quotes are verbatim,
grounded in your corpus" and enforced it with a prompt rule. This is the code that
checks it — offline, no LLM, re-runnable by anyone holding the corpus file.

Run it (from the plugin root, with nothing but Python):

```bash
python tests/grade_dummy_case.py
```

No Ollama. No embeddings. No sqlite-vec. No network. It builds a corpus store from this
folder's `docs/`, drafts four documents, and checks every quoted span and every
`[E.n.S.n]` reference against the corpus by byte containment.

## Result — 2026-11-03, Python 3.14, Windows

```
versus 5 documents, 10 chunks:
  - board-minutes.txt (2 chunks)
  - email-thread.txt (2 chunks)
  - invoices.txt (2 chunks)
  - ppsr-search.txt (2 chunks)
  - supply-agreement.md (2 chunks)

  good        ok=True  summary={'verified': 1, 'corrected': 0, 'ungrounded': 0}
             quotes=[{'quote': 'Any amount not paid by its due date bears default interest at 26% per annum from due date until payment', 'verdict': 'VERIFIED', 'source_name': 'supply-agreement.md', 'trust_tier': 'T1', 'synced_at': '2026-11-03T14:35:49.451688+00:00', 'line': 1}]
             refs=[{'ref': '[E1.S1]', 'verdict': 'VERIFIED', 'found_in': 'supply-agreement.md', 'synced_at': '2026-11-03T14:35:49.451688+00:00', 'line': 1}]

  fabricated  ok=False summary={'verified': 0, 'corrected': 0, 'ungrounded': 1}
             quotes=[{'quote': 'Kaikoura Freight v Reed held that a seller may recover punitive damages', 'verdict': 'NOT_IN_CORPUS', 'source_name': None, 'trust_tier': None, 'synced_at': None, 'line': 1}]
             refs=[{'ref': '[E1.S2]', 'verdict': 'NOT_IN_CORPUS', 'found_in': None, 'synced_at': None, 'line': 1}]

  paraphrased ok=False summary={'verified': 0, 'corrected': 0, 'ungrounded': 1}
             quotes=[{'quote': 'default interest at a rate of twenty six per cent per annum', 'verdict': 'NOT_IN_CORPUS', 'source_name': None, 'trust_tier': None, 'synced_at': None, 'line': 1}]
             refs=[{'ref': '[E1.S3]', 'verdict': 'NOT_IN_CORPUS', 'found_in': None, 'synced_at': None, 'line': 1}]

  no-quote-ref ok=False summary={'verified': 0, 'corrected': 0, 'ungrounded': 1}
             quotes=[]
             refs=[{'ref': '[E9.S9]', 'verdict': 'NOT_IN_CORPUS', 'found_in': None, 'synced_at': None, 'line': 1}]

4 drafts checked — PASS: real quotes VERIFIED, both traps NOT_IN_CORPUS
```

(`synced_at` is W2's per-row freshness stamp: the VERIFIED rows carry the ingest time
of the chunk that decided them, the trap rows carry `None` — a quote checked against
fresh corpus says when its authority was last synced, so "current as of <date>" is
part of the machine check, not prose.)

## What each row demonstrates

| Draft | What it is | Verdict | Why it matters |
|---|---|---|---|
| `good` | A real span of `supply-agreement.md`, quoted verbatim | `VERIFIED` from `supply-agreement.md` | A correct draft passes — the check is not a trap that fails everything |
| `fabricated` | A plausible authority that does not exist here | `NOT_IN_CORPUS` | Citation-shaped fabrication is caught. This is the Stanford 2025 finding's failure mode |
| `paraphrased` | Real contract words, reworded inside quote marks | `NOT_IN_CORPUS` | The headline trap: every word is genuine, the span is not. Paraphrase-inside-quotes cannot pass |
| `no-quote-ref` | A `[E.n.S.n]` token with no quoted span | `NOT_IN_CORPUS` | A model that cited from memory gets no credit for the shape of a citation |

`ok=false` is fail-closed by design — an empty corpus or a missing deliverable makes every
quote ungrounded rather than "looks plausible".

## The honest limits of this check

- **Quote fidelity, not legal correctness.** A verbatim quote can still be cited for a
  proposition it does not support — the other half of the hallucination problem. Entailment
  is not in this release; the nearest guard is `ironfleet_objection`'s `MISMATCH` verdict,
  which catches a ref whose draft quote contradicts the corpus sentence the run's evidence
  table pinned it to.
- **`verify_document` says `VERIFIED` / `NOT_IN_CORPUS` / `PRIVILEGED`.** `PRIVILEGED` (G3)
  means the span exists only in privileged-tier (T0/T2) chunks, so quoting it into an open
  deliverable fails the gate. `MISMATCH` is not emitted here — pinning a ref to its sentence
  needs the run's logged evidence table, and that check is `ironfleet_objection`'s (G5),
  which reuses this core.
- **`ok` is a gate, not a score.** It is consumed by a rule that refuses to close a run
  with unverified spans, not by anything that ranks quality.

## Reproduce it in your own matter

```bash
python tests/grade_dummy_case.py          # this benchmark, offline, ~1s
```

Then on real work, stage 8 of `/ironfleet-legal:process-case` calls
`ironfleet_verify_document` on `advice-letter.md` and `win-assessment.md` before stage 9
may close the run — so the output above is what every deliverable is checked against, not
a demo that only runs in this folder.
