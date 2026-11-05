# TEST-CHECKLIST — harbour-freight (synthetic matter, 2026-10-22)

Copy this whole folder into the Ubuntu VM. All parties are fictional. Every number has
a known right answer so you can judge the pipeline's output mechanically.

## 0. VM preflight (before any plugin command)

```bash
python --version                                   # need 3.10+; if "command not found": sudo apt install python-is-python3
python -c "import sqlite_vec; print('ok')"         # else: python3 -m pip install --user --break-system-packages sqlite-vec==0.1.9
python -c "import pypdf"                           # else same command with pypdf
curl -s http://127.0.0.1:11434/api/tags | grep -o bge-m3   # else: install ollama, ollama pull bge-m3
```

`/ironfleet-legal:doctor` may say "Unknown command" on your CLI build (doctor is a
SKILL, not a command) — instead ask in words: "run the IronFleet doctor preflight".
All six checks green = READY. Reranker down is fine (search degrades, honestly).

## 1. Ingest (fast path first)

```
/ironfleet-legal:ingest <this-folder>/docs matter: harbour-freight
```

Expected: 5 files, ~10-12 chunks, 0 skipped (every file >200 words on purpose — the
ingester records-and-skips shorter files as "scanned"). NOTE: point at the `docs/`
SUBFOLDER only — this checklist file itself must NOT enter the corpus (it holds the
answer key; ingesting it would leak ground truths into retrieval and any drafts).

## 2. Retrieval probe (30 seconds)

Ask in words: "search the harbour-freight corpus for 'default interest 26 per cent'
and show the passages". Expected: verbatim lines from supply-agreement.md / invoices.txt.

## 3. The one-prompt pipeline

```
/ironfleet-legal:process-case Our client Southern Haulage Ltd is owed money by Harbour
Freight Solutions Ltd. Advise: can we win, what do we file, and how do we minimise
damage given the bank? matter: harbour-freight
```

## 4. GROUND TRUTHS — the pipeline is working if the output shows:

1. **Demand amount $126,000** ($64k−$22k + $84k) — NOT $148,000 or $170,000. The
   2019 invoice ($22,000, due 20 Mar 2019) is TIME-BARRED (Limitation Act 2010, 6-year
   money-claim period, expired Mar 2025) and must be excluded; including it invites a
   s 290 "substantial dispute" knock-out. The debtor's 3 Aug 2026 email already
   pleaded "stale, surely there is a time limit".
2. **Statutory demand kernel called** (amount vs the $1,000 minimum; 15 working days
   from service under s 289(2)(d) via the deadline tool).
3. **The 3 Aug 2026 $22,000 payment flagged as a voidable-preference exposure**
   (Companies Act 1993 s 292; the board minutes concede insolvency in Sept 2026, and
   the emails show Southern Haulage KNEW of the hardship → weak s 296(3) defence).
   Authority gold in the corpus: Madsen-Ries v Cooper, McIntosh v Fisk, Levin v Ikiua,
   Camray Farms, Kaikoura Freight, LSF Trustees.
4. **PPSA twist caught**: the client's financing statement (8 Apr 2025) came years
   after the equipment was first delivered (2019) — far outside the PMSI window (PPSA
   s 73(1): perfected within 10 working days of possession) → unperfected 2019 to
   8 Apr 2025 (s 41) and behind the bank, whose Jan 2024 GSA registered first (s 66).
   No insolvency-vesting rule is in the five Acts — [NOT IN CORPUS] is correct there. Portacom/NZ Bloodstock live in
   Set_2 if you ingest it.
5. **26% default interest tested against penalty doctrine** (CCLA 2017), not silently
   claimed.
6. **[NOT IN CORPUS] honesty**: any authority outside the ingested corpus is flagged,
   never silently cited.
7. **Paper trail**: `matters/harbour-freight/runs/<date>-<id>/` with run.json,
   trace.jsonl, RECORD.md; provenance headers on every deliverable.

## 5. Fast vs full corpus

Fast (above): dummy docs only — minutes on CPU. Full: add the key statutes first
(Companies Act 1993.md, Insolvency Act 2006.md, Personal Property Securities Act
1999.md, Limitation Act 2010.md from Desktop/nz — .md only, they duplicate the .pdfs),
then Set_2's 31 judgment PDFs LAST (CPU embedding is slow; expect hours). The run is
answerable from the dummy docs alone; statutes+cases make the citations verbatim-ground.

## 6. Two simulated court rounds (M5 dossier loop, replayable offline)

The dossier loop is graded mechanically by `python tests/grade_dummy_case.py`
(extended for M5): it seeds strategy v1 + predictions, ingests round 1
(`court-rounds/minute-round-1.md`: judgment $126,000 but payment in **20 working
days**, not immediate → prediction miss), cuts strategy v2, ingests round 2
(`court-rounds/minute-round-2.md`: $100,000 part payment received, **balance
$26,000** outstanding → leave to enforce), cuts v3, and asserts the whole chain.
The same rounds replay LIVE with `/ironfleet-legal:debrief matter: harbour-freight`.

Expected dossier end-state (ground truths):

1. **Strategy versions 1→2→3**, each with a `why_changed` naming what the court
   decided that the previous version got wrong.
2. **Outcomes recorded per prediction**: p1 **match=false** (court ordered payment
   in 20 working days, not the predicted immediate payment), p2 **match=true**
   (judgment for the claimant), p3 **match=false** (part payment $100,000 only;
   $26,000 balance outstanding → enforcement path).
3. **Deadlines kernel-dated only**: the payment deadline registered from the
   minute-1 service date (20 working days) comes back equal to
   `ironfleet_filing_deadline` on the same inputs — never a model-invented date
   (a `due` in the tool arguments is refused with an error).
4. **After round 2: no unresolved predictions** (every diff entry has an outcomes
   row) and the enforcement deadline + CMC dates registered from minute-2.
5. The two minute files are synthetic (fictional judge, fictional CIV number) and
   stay OUT of the ingested corpus (same leak rule as this checklist itself).
