# ROADMAP 0.2.0 — IronFleet Legal (the citation-auditable release)

> **Purpose:** the 0.1.0 → 0.2.0 continuation anchor. A new chat session starts here.
> **DONE convention (same as [NEXT_STEPS.md](../NEXT_STEPS.md)):** when a step completes, wrap it in
> `~~strikethrough~~` and append `— DONE <date> (<commit/notes>)`. Both the user and Claude update
> this file. Nothing else needs re-explaining.
> Last updated: 2026-11-03
>
> **START HERE if a step is done in either section AND still has its full body in
> "Next steps" — it is not done until struck there too.**
> **ROADMAP COMPLETE AND PUBLISHED (2026-11-03):** 0.2.0 (G1–G6), 0.2.5 (W1–W3) and
> 0.3.0 (L1–L2) are all built and struck below; the version is 0.3.0 in all three
> synced copies (`sync-version 0.3.0`), the post-0.1.0 work (G1..L2) shipped as one
> commit on `main`, and the leftover publish-time step is CLOSED. **NZLII is ruled
> OUT permanently, even as manually-downloaded content** (embedding it breaches its
> usage policy regardless of who fetched the files). Read the "Where we are" block
> below before touching anything, and never re-litigate the two mechanical-only
> rulings named there.

## Where we are (read this first in a new session)

- **0.1.0 is PUBLIC** at `github.com/BasimBashir/ironfleet-legal` (2026-10-21). Smoke 9/9 green.
  **NO Claude co-author** on this repo (user instruction).
- **The 0.2.0 thesis (from the 2026-10-26 web analysis):** 0.1.0's differentiator is a *promise* —
  "quotes are verbatim, grounded in your corpus". That promise is enforced by a **prompt rule**
  (the process-case house rules), never by code. Stanford's 2025 hallucination study found even
  leading commercial legal research RAG tools fabricate citations; the NZ Supreme Court warned on
  AI in June 2026 ("human oversight, not human abdication") and 2026 rules push disclosure +
  certification of AI use in filings.
  **0.2.0 converts the promise into a PROOF: a mechanical, offline, re-runnable check that any
  opposing counsel, court or regulator can run against a deliverable and see green.** That is the
  product nobody has built, and it is what the 2026 compliance environment rewards.
- **Release shape:** 0.2.0 = **G1..G6** (defensibility). 0.2.5 = **W1..W3** (the world).
  0.3.0 = **L1..L2** (loved).
- **Two rulings already in force and NEVER re-litigated:** mechanical-only MCP (zero LLM calls in
  `mcp/`), local-only embeddings/rerank (`LOCAL_ONLY_TASKS`), and consent-gated install.

## Completed (struck through — do not redo)

- **au/uk compliance day-type ruling — DONE 2026-11-03** (user ruled CALENDAR days;
  closes W1's named limitation). The pack key is renamed honestly
  `compliance_period_working_days` → `compliance_period_days` with a new
  `compliance_period_day_type` ("working" nz / "calendar" au/uk — Corporations Act
  2001 s 459F is 21 plain days after service; the UK ground is three weeks, IA 1986
  s 123(1)(a)): the kernel dispatches `svc + timedelta(days=n)` for calendar packs and
  the working-day calendar for nz; an unknown day_type in a pack raises. Result keys
  renamed with it, and the G5 objection contract follows: `_KERNEL_TOOLS` reads
  `compliance_period_days`, `_PERIOD` accepts an optional "working" so calendar
  phrasings parse, and both hardcoded "working days" objection details are gone
  (period text quotes the draft's own words). OLD traces' statutory_demand events
  carry the old payload key, so the period check skips on them — date checks
  unaffected (house rule: old traces degrade honestly). Skill doc, tool description
  and process-case stage-6 wording updated. Court filing deadlines untouched (their
  own working-day rule was never named by the ruling). Suite 60/60 (+2 dispatch
  tests: au/uk 21 calendar from Mon 2 Mar → 2026-03-23; nz stays
  `add_working_days`-equal), grader PASS 4/4 by file path, MCP dispatch live-checked
  (au: 21/calendar/s 459F; nz: 15/working). Uncommitted, same as everything.

- ~~**W2. `/sync-law` — statute + judgment corpus sync**~~ — DONE 2026-11-03, RESHAPED
  by the operator-supplied ruling (user, 2026-11-03): legislation.govt.nz stays closed
  to automation (bot-gated, step 0 verdict stands) — **the user downloads the law files
  themselves, in their own browser, into a local folder, and the harness ingests that
  folder.** So the fetch half the step imagined is replaced by the operator, and the
  build is: (a) NEW `commands/sync-law.md` — the thin wrapper the step asked for, minus
  any fetching: baseline (`ironfleet_list_docs`) → `ironfleet_ingest_docs` (REUSE, per
  the step's own "do not write a second ingest" rule — that rule is why no
  `law_ingest.py` module exists once fetching died) → per-file NEW/REFRESHED report →
  freshness statement → `bind-tier law T3` via the W3 operator CLI. Matter `law` for
  statutes, `law-judgments` for judgments — the matter W3's citator reads, so the
  citator has a real corpus path the moment the operator downloads. (b) Step 3 landed:
  `verify_document` envelopes carry per-row `synced_at` plus a top-level `freshness`
  (the newest ingest ts among the chunks that decided a VERIFIED verdict — the
  "current as of <date>" sentence). No schema change: docs rows have carried
  `ts` + `sha256` since the first vendored drop; legacy read-only corpora keep working
  (the G3 fallback select gains the same `d.ts`, which predates G3). (c) **NZLII stays
  NO-GO as content even when downloaded manually** — creating embeddings of its content
  breaches its usage policy regardless of who fetched the files; recorded in
  sync-law.md so no future run "solves" the block by hand. (d) Licence honesty:
  legislation.govt.nz's copyright page was never machine-read (bot-gated) — the
  operator reads the terms at download time (expected CC BY 4.0 for NZ legislation,
  unverified ASSUMPTION) and records what the page says on first download. Uncommitted.

- ~~**W3. Citator-lite + operator CLI**~~ — DONE 2026-11-03 (both halves BUILT; the
  citator's target matter `law-judgments` waits on W2's operator-supplied judgments,
  so proofs are synthetic-corpus only. (a) NEW `mcp/harness/citator.py` — the cites
  join over the corpus's ALREADY-DERIVED `cites_<m>` tables, zero new storage: the
  query names an authority (case span or statute pin, both through
  `corpus._citation_keys`), the join lists ingested judgments whose text cites it,
  each flagged `later` from its OWN neutral-citation year `[YYYY]` (bare years never
  counted; statutes have no decision year so their citing rows are honestly
  `year_unknown`). Self-vs-citing: a doc whose FIRST chunk heading carries the
  authority's key is the authority's own doc; with no heading match anywhere,
  first-chunk body matches whose year agrees with the string's are promoted (the
  provision shape — pin in body, no year — and duplicate same-year ingests). Named
  shortcut: a citing judgment whose first chunk is heading-less AND names the
  authority in the same year, with the authority absent from the corpus, lands in
  the authority bucket — upgrade to an ingest-stamped identity column if a real
  corpus trips on it. One prose-shape amendment, additive by the house's own rule:
  a sentence-initial "In X v Y [year] ..." swallows the leading `In` into the stored
  join key, so the query adds the `case:in <key>` VARIANT as an extra candidate
  (never a merge of two distinct authorities). Two modes: `authority=<one citation>`
  and `path=<deliverable>` (every authority the draft names, one summary row per
  key, citing detail only where citing_docs>0). Informational BY DESIGN: ok stays
  true — a later citing judgment does not invalidate a deliverable, treatment is a
  human reading call (citator-lite, per the roadmap; a treatment citator is not W3).
  Fail-closed loud on: no matter bound, unrecognised citation span, matter with no
  ingested corpus ("an empty corpus cannot clear an authority"), and a pre-citation-
  amendment corpus with no cites table (re-index first). Registered as
  `ironfleet_citator` (14th tool) + smoke set; one conditional sentence wired into
  process-case.md stage 8 (runs only when a law-judgments corpus exists — W2 is
  blocked, so most matters have none and the rule must not fail those runs).
  (b) NEW `mcp/harness/cli.py` — the operator CLI (`python mcp/harness/cli.py
  <subcommand>`): `reclassify-tier <matter> <T0-T3>` (the G3 deferred re-tiering
  surface, backed by new `CorpusStore.set_tier` — same effect as re-ingesting with
  a tier, no re-parse or re-embed), `bind-tier <matter> <T0-T3|clear>` (writes
  `matter.json` at the store root — THE G3 deferred binding surface — read back by
  new `corpus.bound_tier()`, and `t_ingest_docs`' default order is now: the call's
  trust_tier, then the binding, then T1), and `sync-version [X.Y.Z]` (stamps the
  three hardcoded version copies — plugin.json, marketplace.json, server.py
  VERSION — the exact gap named in server.py's own comment; no arg re-syncs from
  plugin.json and repairs drift). Tier args validated against `_OPENNESS`; writes
  all carry explicit `encoding="utf-8"`. Live-run on the real tree: sync-version
  drift check ok (changed {}), bind/clear roundtrip on the real store root,
  reclassify of a never-ingested matter errors loud with exit 1. Tests: 11 new
  (`tests/test_citator.py` 6, `tests/test_operator_cli.py` 5 — including an
  OFFLINE end-to-end ingest-default proof via HARNESS_HOME + patched `embed_fn`)
  + a citator fail-closed smoke test; suite 58/58; grader PASS 4/4 by file path.
  Uncommitted, same as G3–G6/W1.)

- ~~**0.1.0 publish**~~ — DONE 2026-10-21 (`nz-contract-reviewer` CC-BY-NC-ND flagged; VM run
  graded PASS; smoke 9/9).
- ~~**G1. `ironfleet_verify_document`**~~ — DONE 2026-10-26 (NEW `mcp/harness/verify.py`:
  pure stdlib, FTS-tables-only, byte containment; registered in `server.py` TOOLS +
  handler; added to `test_smoke.py`; stage 8 of `process-case.md` calls it on both
  deliverables + a fail-closed house rule barring `finish_run` on unverified spans;
  grading `python tests/grade_dummy_case.py` PASS 4/4 on the dummy case; benchmark
  published as `dummy-case-harbour-freight/verify-report.md`; suite 23/23).
  **Two deliberate deviations from the spec:** (a) no `MISMATCH` verdict is emitted — it
  needs the run's evidence table, which `records.py` does not persist (grep: zero readers
  of `evidence_window()`'s table); lands with G5. (b) `summary` counts CITATION INSTANCES,
  not claims, because it feeds a fail-closed gate and under-counting a failure is the only
  dangerous direction. Note the benchmark script must be run by FILE PATH
  (`python tests/grade_dummy_case.py`) — `tests/` has no `__init__.py`, so `-m tests.x`
  loses to an unrelated `tests` package in site-packages.
- ~~**G2. Fail-closed gate — the pipeline refuses to emit an unverified deliverable**~~ —
  DONE 2026-10-30 (no new code: the binding rule already landed with G1's step-3 wiring —
  stage 8 mandates `ironfleet_verify_document` on both deliverables, and the process-case.md
  house rule "Verified before closing (G1+G2, fail-closed)" bars `ironfleet_finish_run` until
  both envelopes return `ok: true` or every `NOT_IN_CORPUS`/`MISMATCH` is fixed in the draft
  or logged as a ruled exception via `ironfleet_log_event` naming ref, quote and ruling;
  wording follows the DEGRADED-MODE shape — degrade loudly, never silently; the
  ruled-exception path keeps a designed `[NOT IN CORPUS]` authority closable). The mechanical
  block inside `finish_run` remains out of scope per the struck section below.
- ~~**G3. Trust tier on the corpus**~~ — DONE 2026-10-30 (NEW `quotable_tier` in
  `corpus.py` — one openness rank `T0 privileged < T2 internal < T1 open (default) <
  T3 public`, unknown values rank below T0, fail-closed; `docs` table gains
  `trust_tier TEXT DEFAULT 'T1'` via in-place `PRAGMA table_info`-guarded
  `ALTER TABLE` (house migration style), self-healing on every read path;
  `DocRecord`/`CorpusHit` carry `trust_tier: str = "T1"`. `t_ingest_docs` stamps an
  optional `trust_tier`. `ironfleet_corpus_search` gains `min_tier` (default T1):
  passages stay readable at every tier and carry `trust_tier`, the QUOTABLE
  authorities list drops T0/T2/unknown. `verify_document` is tier-aware: a span in
  ANY open-enough chunk VERIFIES (identical bytes already exist in an open source),
  a span living only in privileged chunks returns a NEW verdict `PRIVILEGED`,
  counted as ungrounded (ok=false) and NEVER closable via the ruled-exception path
  (process-case.md house rule + stage 8 updated; the server `remedy` text says so).
  Legacy pre-G3 corpus read read-only (the court's bare box) reads as T1 — the
  column's own declared DEFAULT — so the G1 grader still passes unchanged
  (PASS 4/4; suite 29/29, 6 new in `tests/test_trust_tier.py`). Dead duplicated
  summary block after `verify_document`'s return deleted.
  **One deviation from the spec:** the "matter already bound a tier (matter.json)"
  ingest default is NOT implemented — no writer of `matter.json` exists anywhere in
  the tree, so there is nothing to default FROM; the binding surface lands with W3's
  operator CLI, same place as re-tiering an already-ingested corpus).
- ~~**G4. `ironfleet_disclosure` — the 2026 AI-use certification block**~~ — DONE
  2026-10-30 (NEW `disclosure_block()` in `mcp/records.py` — the roadmap's sanctioned
  "function in records.py" option, it is ledger reading. Renders the block
  mechanically from `run.json` + `trace.jsonl`, zero new storage: run/matter/status/
  period/session, stages listed ONLY if a `stage_end` event evidences them — the
  grading criterion holds by construction — declared-but-unended stages flagged in
  their own loud section, tools / verify verdicts / corpus refs rendered only from
  logged `tool_result` / `exception` events, then the certification sentence +
  signature line. Registered as `ironfleet_disclosure` (11th tool) + smoke set.
  process-case.md wiring: per-stage logging tightened to named events
  (`stage_start {stage, agent}` / `stage_end {stage, file, digest}`); stage 6 embeds
  the block at the top of `filings-roadmap.md` and logs each deadline computation as
  `tool_result`; stage 8 logs each verify envelope as `tool_result` — without that
  the verdicts were not mechanically renderable, so it is required by the spec, not
  gold-plating. Suite 31/31 (2 new in `tests/test_disclosure.py`); G1 grader still
  PASS 4/4. Uncommitted, same as G3.)
- ~~**G5. `ironfleet_objection` — the adversary's three failure modes as a tool**~~ —
  DONE 2026-10-30 (NEW `mcp/harness/objection.py`: (a)+(b) reuse G1's
  `verify_document` core byte-for-byte; (c) reads the kernel computations stage 6
  already logs as flat `tool_result` events (`ironfleet_filing_deadline` →
  `deadline`/`days`; `ironfleet_statutory_demand` → `compliance_deadline`/
  `compliance_period_working_days`), dates normalised from ISO, NZ prose and
  day-first slashes; the MISSING direction fires only when the draft speaks of
  deadlines at all (an attack brief cannot omit a deadline), a context-line
  assertion no computation produced is objected, and a logged `service_date` is a
  fact, not an objection. **G1's deferred MISMATCH verdict lands here:** a stage
  that drafts with [E.n.S.n] refs now logs its evidence table (house-rule mandate:
  log_event event `evidence`, payload `{table: {ref: sentence}}`); objection pins
  each ref to its sentence — a contradicting draft quote is MISMATCH, a quote-less
  ref verifies through its pinned corpus-grounded sentence, and a table sentence
  nowhere in the corpus is loud NOT_IN_CORPUS. Registered as `ironfleet_objection`
  (13th tool) + smoke set; wired at stage 4 (attack brief — the mechanical check
  runs before advice is drafted) and stage 8 (advice-letter + filings-roadmap,
  where kernel dates live). Suite 43/43 (12 new in `tests/test_objection.py`);
  G1 grader still PASS 4/4. Uncommitted, same as G3/G4.)

## Next steps (in order)

### ~~G1. `ironfleet_verify_document` — the ground-truth citation checker (the headline feature)~~
- **DONE 2026-10-26** — struck in "Completed" above with the full record. **Do not redo,
  and do not re-derive the two deviations recorded there** (no `MISMATCH` until the run's
  evidence table is persisted; `summary` counts citation instances, not claims).
- **Why:** the corpus contract is currently a house *rule*. A model that ignores it produces
  paraphrase-inside-quote-marks and citation-shaped fabrications, and nothing in 0.1.0 catches it.
  This tool makes the deliverable self-checking: mechanical, no LLM, runs offline, repeatable.
- **Connect (files to touch, in order):**
  1. **NEW `mcp/harness/verify.py`** — pure stdlib. Input: `{matter, path}` (deliverable file).
     Steps: read the file; collect every `[E<n>.<m>]`-style reference token the draft carries
     (reuse `_REF_TOKEN` at [corpus.py:592](../../mcp/harness/corpus.py)); for each, resolve the
     (doc_id, passage) the run's evidence table recorded and **byte-compare the quoted span
     against the corpus chunk text**; also every double-quoted span `"..."` longer than N words
     must be a substring of a corpus chunk of this matter. Verdict per ref:
     `VERIFIED | NOT_IN_CORPUS | MISMATCH`. Output envelope: `{ok, refs:[{ref, verdict, found_in,
     line}], quotes:[{quote, verdict, source_name}], summary:{verified, corrected, ungrounded}}`.
     **Shortcut:** byte-substring containment, not NLI entailment — a verbatim quote is the
     contract; *whether the passage supports the proposition* is G6's job. Upgrade to NLI when
     G6 lands.
  2. **Register it** in `TOOLS` at [server.py:132](../mcp/server.py) — one tuple
     `("ironfleet_verify_document", <desc>, _schema({matter, path}, ["matter","path"]), t_verify_document)`
     plus a `t_verify_document(a)` handler in the same style as `t_filing_deadline`
     ([server.py:57](../mcp/server.py)). Add it to the `<= names` set in
     [test_smoke.py:20](../tests/test_smoke.py).
  3. **Wire it into the pipeline** so it is *load-bearing*, not decorative: in
     [commands/process-case.md](../commands/process-case.md) stage 8 (verify), state that the
     citation agent MUST call it on `advice-letter.md` and `win-assessment.md`, and that stage 9
     may not write `closing-summary.md` if the envelope has any `MISMATCH` or `NOT_IN_CORPUS`
     beyond those recorded and ruled on. One paragraph, house-rules section.
- **Grading:** run it against [dummy-case-harbour-freight/](../dummy-case-harbour-freight/) after a
  real run — every trap must be caught; a *correct* run must come back all-`VERIFIED`. Publish
  that output as the benchmark artefact (feeds L2).
- **Not in this step:** entailment/NLI, cross-matter verification, repair of a failing draft.
  **Risk:** if the deliverable has no evidence table (a model that quoted from memory), the tool
  must say `NOT_IN_CORPUS` loudly and never fall back to "looks plausible".

### ~~G2. Wire the fail-closed gate — the pipeline must refuse to emit an unverified deliverable~~
- **DONE 2026-10-30** — struck in "Completed" above with the full record; body kept for
  context, do not redo. Zero diff beyond the house-rule label: the rule was already
  load-bearing in [process-case.md](commands/process-case.md).
- **Why:** a checker nobody gates is a suggestion. This is the line that makes 0.2.0 defensible.
- **Connect:** same [process-case.md](../commands/process-case.md) house rules — one binding rule:
  *stage 9 (close) does not call `ironfleet_finish_run` until `ironfleet_verify_document` has been
  run on both deliverables AND every `MISMATCH`/`NOT_IN_CORPUS` is either fixed or recorded as a
  ruled exception with a trace event*. Fail-closed wording borrows the existing DEGRADED-MODE
  paragraph's shape — degrade loudly, never silently.
- **Not in this step:** a hard technical block. 0.1.0's precedent is the orchestrator honours the
  contract in prose and logs violations; a mechanical block inside `finish_run` is G3.
- **Risk:** interrupts the crew flow mid-run; keep the exception path (ruled + logged) so a
  legitimate `[NOT IN CORPUS]` authority (marked as such by design) still closes.

### ~~G3. Trust tier on the corpus — WP-classified text must never leak into an open deliverable~~
- **DONE 2026-10-30** — struck in "Completed" above with the full record; body kept
  for context, do not redo. Note the one deviation recorded there (matter.json
  binding deferred to W3 — no writer exists).
- **Why:** the WP kernel classifies correspondence *as it arrives*, but the store keeps whatever
  was ingested with no tier marker, so privileged text can be quoted into an open deliverable.
- **Connect:**
  1. **Schema:** `docs` table at [corpus.py:246](../mcp/harness/corpus.py) gains a
     `trust_tier TEXT DEFAULT 'T1'` column (idempotent `ALTER TABLE` guarded by a
     `PRAGMA table_info` check, same in-place style as the existing migrations); `DocRecord` at
     [corpus.py:101](../mcp/harness/corpus.py) gains `trust_tier: str = "T1"`.
  2. **Ingest:** `t_ingest_docs` ([server.py:60](../mcp/server.py)) accepts optional `trust_tier`
     and passes it through; when the matter already bound a tier (matter.json), default to it.
  3. **Search:** `ironfleet_corpus_search` ([corpus.py:517](../mcp/harness/corpus.py)) gains a
     `min_tier` filter (default: exclude `T0`/`T2` privileged rows from the *quotable* authorities
     list, keep them in passages if explicitly asked). Fail-closed: an unknown tier is excluded.
  4. **Verify:** G1's `verify_document` rejects a quote whose chunk is below `min_tier`.
- **Not in this step:** re-classifying an existing corpus (an operator CLI is W3).

### ~~G4. `ironfleet_disclosure` — the 2026 AI-use certification block~~
- **DONE 2026-10-30** — struck in "Completed" above with the full record; body kept
  for context, do not redo. The ledger contract the block renders from: stages need
  `stage_end {stage, file, digest}` events; verdicts/refs need `tool_result` events
  (process-case.md now mandates both).
- **Why:** 2026 NZ rules require disclosure + certification of AI use in filings. This emits the
  artefact mechanically from the run ledger — zero new storage, pure rendering.
- **Connect:**
  - **NEW `mcp/harness/disclosure.py`** (or a function in `records.py`, it is ledger reading):
    render from `runs/<id>/run.json` + `trace.jsonl` a markdown block: run id, matter, model,
    agent per stage, tools called, corpus refs used, which documents were verified by
    `ironfleet_verify_document` and their verdicts, and the sentence "no AI system made any
    decision or filing; a named human reviewed and certified this document" + a signature line.
  - **Register** in `TOOLS` + smoke set; **reference it** in process-case stage 6 (filings) so the
    roadmap deliverable includes it for every court filing.
- **Grading:** the block must be self-consistent against the trace (a stage listed in the
  disclosure must have a `stage_end` event).

### ~~G5. `ironfleet_objection` — promotion of the adversary's three failure modes to a tool~~
- **DONE 2026-10-30** — struck in "Completed" above with the full record. One stale
  pointer to note: the original text sent you to
  [skills/nz-differential-review/](../skills/nz-differential-review/) for the three
  failure modes, but that skill is the SECURITY differential review — the modes live
  in this section's own spec text, which is what was encoded.

### ~~G6. Version bump + the published benchmark (L1 prep, lands here)~~
- **DONE 2026-10-30** (version 0.1.0 → **0.2.0** in `.claude-plugin/plugin.json`,
  `.claude-plugin/marketplace.json` and `server.py` `VERSION`, with a move-together comment
  at the constant — no build step syncs them yet, that is W3; `docs/FRESH-OS-SETUP.md`
  header refreshed to match (release line + 13-tool count, both had drifted);
  `dummy-case-harbour-freight/verify-report.md` re-published from a fresh grader run —
  output now carries G3's `trust_tier`, and the limits section was rewritten to be true
  post-G3/G5 (PRIVILEGED verdict; MISMATCH lives in `ironfleet_objection`, not
  `verify_document`). Grader PASS 4/4; suite 43/43. Uncommitted, same as G3/G4/G5.
  Note: the G1-era note "entailment is G6's job" did NOT happen — G6 is version+benchmark
  only; entailment remains unscheduled (named here so it is not silently dropped).)

## 0.2.5 — the world (after G1..G6 are green)

### ~~W1. Law-pack data files — jurisdiction from hardcoded to data~~
- **DONE 2026-10-30** (no new loader — as spec'd, the work was data + strings. (a) The au/uk
  values were VERIFIED against current sources before touching anything, not "completed" by
  guesswork: AU's $4,000 threshold is CORRECT (raised from $2,000 July 2021 — Finlaysons;
  confirmed by 2026-dated guides; an earlier session-memory claim of $10,000 was wrong and
  was caught by the search), UK's £750 / three weeks are CORRECT and the ref was precisioned
  to **s 123(1)(a)** (the deeming ground that carries the £750 + 3 weeks; s 123(1)(e) is the
  cash-flow test, a different thing); uk interest ref now says "8% + Bank of England base
  rate" (the bare "8.00" was the statutory uplift, not a rate). New pack fields, all three
  files: `statutory_demand.compliance_statute_ref` (nz: Companies Act 1993 s 241(4)(a); au:
  Corporations Act 2001 s 459F; uk: IA 1986 s 123(1)(a)) + new `without_prejudice` section
  with `privilege_statute_ref` (nz: Evidence Act 2006 s 57; au: Evidence Act 1995 s 131; uk:
  common law). (b) The two NZ-hardcoded strings are gone: `companies_act.py` lost its
  nz-only branch (every jurisdiction now routes through the loader — identical values for nz,
  since nz.json already held 1000.00/15) and its `PRESCRIBED_MINIMUM` /
  `DEFAULT_COMPLIANCE_PERIOD` constants (no external callers, grep-verified); the "s 289"
  issue-string and both statute names now come from the pack and land in the result dict as
  additive `statute_ref` / `compliance_statute_ref` keys (G5's readers read named keys, safe).
  `without_prejudice_detector.py` takes an optional `jurisdiction` payload field (default nz;
  `kernel_tools` passes payloads straight through, so no caller changes) and the WP reasoning
  interpolates the pack's `privilege_statute_ref`. NEW `tests/test_jurisdictions.py` — the
  round-trip: each declared jurisdiction loads, prints its statute refs, kernel output
  carries pack refs, WP default stays nz. Suite 46/46; grader PASS 4/4. Uncommitted, same as
  G3–G6. **One named limitation, NOT silently dropped:** au/uk compliance periods are
  CALENDAR days under their statutes (s 459F: 21 days; IA 1986 s 123(1)(a): three weeks) but
  the kernel computes WORKING days for every jurisdiction (`compliance_period_working_days` +
  `add_working_days`). Fixing that is a kernel-contract change (a day-type field +
  calendar-days branch in the deadline math), outside W1's data-files scope — needs a ruling
  before W3's operator CLI, since an au/uk deadline computed today overstates by ~8 days.)
- **Current state (already partly done — read before building):** `JurisdictionLoader`
  ([vendored/jurisdiction_loader.py](../mcp/harness/module_e/vendored/jurisdiction_loader.py))
  already loads `nz`/`au`/`uk` JSON + holiday tables and the four kernels
  (`statutory_demand`, `filing_deadline`, WP, interest/limitation/penalty thresholds) already
  route through it. **The work is NOT a loader build — it is (a) completing the au/uk config
  files against real statute, and (b) moving the two remaining NZ-hardcoded strings** (the s 289 /
  s 241(4)(a) names inside
  [vendored/companies_act.py](../mcp/harness/module_e/vendored/companies_act.py) and the WP
  detector's Evidence Act 2006 s57 markers in
  [vendored/without_prejudice_detector.py](../mcp/harness/module_e/vendored/without_prejudice_detector.py))
  **out of the kernels and into the pack files.**
- **Connect:** `mcp/harness/module_e/vendored/data/config/jurisdictions/<code>.json` gains the
  statutory-names/marker fields; the kernels read them; add a `jurisdictions` round-trip test
  (each declared jurisdiction loads and prints its statute refs).

### ~~W2. `/sync-law` — statute + judgment corpus sync (the biggest usability unlock)~~
- **DONE 2026-11-03** — struck in "Completed" above with the full record; body kept
  for context, do not redo. The RESHAPE: the operator downloads, the harness ingests
  (never fetches); `commands/sync-law.md` + verify freshness landed.
- **Why:** 0.1.0 is "bring your own authority". This makes authority current and present.
- ~~**BLOCKED ON A LICENCE/FEED CHECK FIRST — do not build before ruling:** the 2026-10-26 web
  analysis could NOT confirm legislation.govt.nz's current XML/API endpoints or its reuse terms
  (that search fell back to model memory, which is not evidence); NZLII's terms likewise.
  **Step 0 is a manual check by the user (or a WebFetch the user sanctions):** fetch
  `https://www.legislation.govt.nz` and `https://www.nzlii.org`, record (a) the exact bulk/XML
  download path or absence of one, (b) the licence (expect CC BY 4.0 or similar for NZ
  legislation; **verify, do not assume** — the R1 research hit a 403 fetching the licence page),
  (c) whether a court/registry judgment feed exists. Record the findings here before Step 1.~~
  — **STEP 0 CLOSED 2026-10-30 (check run; verdict mixed).** **NZLII = hard NO-GO:** its live
  Copyright & Usage Policy (nzlii.org/copyright.html, fetched 2026-10-30) bars AI-related use
  across the entire collection — §6(b)(ii) names creating embeddings / vector representations /
  semantic indexes; §6(b)(iv) bars automated querying where results are stored/cached/reused;
  §6(b)(v) bars integration into legal research/drafting systems; case-law is REP-blocked for
  automated agents (§1(e)). Against the checklist: (a) feed paths — moot for NZLII, access is
  prohibited regardless of what exists; (b) licence — no open re-use licence is granted on
  that page, it is a prohibitions policy; (c) judgment feed — irrelevant while the policy
  stands. **legislation.govt.nz = UNVERIFIED (user ruled skip):** the site bot-gates automation
  (curl → 202 challenge on every path from this box; the root loads server-side and confirms
  PCO's "Legislative data" + "Copyright" pages exist, but their content would not fetch —
  reader 500s). The expected CC BY 4.0 stays an ASSUMPTION until a human browser visit to
  `/copyright` records it here; do not retry automated fetches. Note: the walls are bot/WAF
  gating, not region — nzlii `/about.html` + `/databases` returned 200 from this box.
- **Step 1 — statutes (only after the licence is recorded):**
  - NEW `mcp/harness/law_ingest.py` — download/pull the statute feed, split per provision
    (DLM anchor body already lands in the chunk at [corpus.py:269](../mcp/harness/corpus.py)),
    embed 1:1 through the existing `embed_fn` path ([localstack.py:35](../mcp/harness/localstack.py)),
    ingest into a dedicated `law` matter via `CorpusStore.ingest` — **reuse the existing ingest
    path, do not write a second one**.
  - NEW command `commands/sync-law.md` — a thin orchestrator wrapper that calls the tool with a
    `matter: law` target and reports new/changed/unchanged provisions.
  - Registration: optionally expose as a tool (`ironfleet_sync_law`) or keep it a
    command+script; **decide on the mechanical-only rule — a command runs in the user's session,
    so a command keeps `mcp/` LLM-free if the *parsing* is mechanical**. Recommendation: script
    + command, not a tool, so no fetching logic lands in the MCP server.
- **Step 2 — judgments:** same shape, NZLII / Courts of NZ source, ingested as a `law-judgments`
  matter, with the case-name join keys the corpus already derives
  (`_case_key` at [corpus.py:166](../mcp/harness/corpus.py)).
  **Step 0 verdict kills the NZLII half:** NZLII's usage policy bars AI/embedding use — do not
  build an NZLII fetcher. The source must become operator-supplied judgments, or an open
  Courts-of-NZ feed if one ever exists (unverified).
- **Step 3 — freshness:** record a `synced_at` + source sha per provision in the `docs` table so
  `verify_document` can say "this authority is current as of <date>" — that sentence is what a
  court wants to see.
- **Not in this step:** a full citator with treatment signals (W3).

### ~~W3. Citator-lite + operator CLI~~
- **DONE 2026-11-03** — struck in "Completed" above with the full record; body kept
  for context, do not redo. Both halves BUILT; the citator waits on W2 for a real
  `law-judgments` matter to run against.
- **Why:** closes the "authority exists but is no longer good law" half of the Stanford finding.
- **Connect:** a `cites` join over the `law-judgments` matter (the `cites` table already exists at
  [corpus.py:251](../mcp/harness/corpus.py)): for a cited authority, list later judgments in the
  corpus that cite it. `NEW mcp/harness/citator.py`, tool `ironfleet_citator`, plus a
  `reclassify_tier` operator CLI mirroring the existing `harness vectors|corpus` CLI shape
  (used by G3 to re-tier an already-ingested corpus).

## 0.3.0 — loved

### ~~L1. `/explain` — the plain-English walkthrough~~
- **DONE 2026-11-03** (NEW [commands/explain.md](commands/explain.md) — the one command the
  spec asked for, zero MCP surface. It locates the closed run's workspace (`closing-summary.md`
  present, else STOP — /explain renders a run, never reconstructs one), re-runs
  `ironfleet_verify_document` FRESH on `advice-letter.md` + `win-assessment.md` rather than
  trusting citation-check.md's pasted envelopes (re-runnability is the proof; a disagreement is
  stated in one loud line first), then walks the user through the answer: the direct answer from
  closing-summary, then each material point as verbatim passage + clickable
  `[E.n.S.n](advice-letter.md:N)` link + `found_in` source + VERIFIED badge, and the W2
  `freshness` sentence once when the envelope carries it. NOT_IN_CORPUS / MISMATCH / PRIVILEGED
  render loudly with any ruled-exception note (PRIVILEGED never softened, G3); MCP-down renders
  `[UNVERIFIED]` in place of verdicts — the DEGRADED shape. Writes NO file: the run's document
  set stays canonical, the walkthrough is the reply. No Python touched — suite 60/60 unchanged,
  grader PASS 4/4 by file path. Uncommitted, same as everything.)
- One command: after a run, walk the user through the answer with clickable citation highlights —
  "here is why the 2019 invoice was excluded, here is the statute, here is the passage", each
  passage self-verified by G1. Renders the deliverable, not a new analysis.
- **Connect:** NEW `commands/explain.md`; no new MCP surface (reads run + corpus).

### ~~L2. MCP resources + the published interop benchmark~~
- **DONE 2026-11-03** (a) **Resources:** `ironfleet://corpus/<matter>/<doc_id>` (a doc's
  row + full text, its FTS chunks rejoined in row order) and
  `ironfleet://runs/<run_id>/<file>` (run.json / trace.jsonl / RECORD.md — name
  allowlist, read-only). Two new CorpusStore reads (`matters`, `doc_text`) — **zero new
  storage**: D1 keeps no matter registry, so the per-matter table suffix IS the key and
  the URI carries the mangled form (`m-res` → `m_res`; `_mtable` round-trips either
  spelling to the same table). Run discovery reads the `runs/.index` pointers begin_run
  already writes — `records.run_dir_by_id` validates the run_id against a strict regex
  BEFORE it joins a path (a resource URI from any MCP client is untrusted input).
  `initialize` now declares `capabilities.resources`; a missing resource is a JSON-RPC
  **-32002** error (the MCP-spec shape, not the tools/call isError envelope — L2's
  audience is non-Claude clients); no pagination (named skip: 7,353 resources on the
  real store ride one stdio line, fine at stdio scale). (b) **Interop bug found by the
  live check and fixed at the root:** `main()` now reconfigures stdin/stdout to UTF-8 —
  on Windows a host that leaves cp1252 in place crashed the server writing ANY
  response containing a non-cp1252 char (corpus text carries U+2010); tools/call had
  the same latent bug, not just resources. (c) **Benchmark:** verify-report.md
  re-published from a fresh grader run — PASS 4/4, and the output now shows W2's
  `synced_at` (present on VERIFIED rows, `None` on the trap rows — freshness is part of
  the machine check); README's dummy-case section now links the report as the public
  benchmark. Tests: suite **62/62** (+2 in test_smoke.py: resource-level corpus/run
  round-trip with fail-closed reads, and a wire-level test through `main()` covering
  capabilities, list/read envelopes, -32002 and unknown-method); grader PASS 4/4 by
  file path; live-checked against the real store (initialize + list over the wire: 7,353
  resources; a real Copyright Act 1994 s 134 provision read back clean). Uncommitted,
  same as everything.
- `resources/` exposure of the corpus and the run ledger so non-Claude MCP clients can browse them
  (stdio `resources/list` + `resources/read` in [server.py](../mcp/server.py) — a new branch in
  `main()`).
- Publish the dummy-case G1 output as a public benchmark everyone can run, turning the internal
  eval suite into an external standard.

## Not in this roadmap (named, so they are not silently dropped)

- **Cloud/other-jurisdiction LLM providers** — the plugin is deliberately local + the user's own
  Claude account; a provider registry is a different product (that is the harness line, not this one).
- **Court e-filing / Te Au Reka integration** — an external API, auth, and a trust boundary this
  plugin has no business crossing mechanically; the filings roadmap points a human at it.
- **Replacing the agents with a single model** — the nine-stage crew is the measured architecture.
- **Any change to the harness-core tree** — this file governs the plugin repo only.

## The one-line thesis to keep on the tin

0.1.0 = "quotes are verbatim" (a promise). 0.2.0 = "here is the machine check that proves it"
(a proof any court can run). Everything above is in service of that one sentence.