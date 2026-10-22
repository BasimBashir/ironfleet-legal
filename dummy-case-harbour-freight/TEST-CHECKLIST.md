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
   from service under s 241(4)(a) via the deadline tool).
3. **The 3 Aug 2026 $22,000 payment flagged as a voidable-preference exposure**
   (Insolvency Act 2006 s 292; the board minutes concede insolvency in Sept 2026, and
   the emails show Southern Haulage KNEW of the hardship → weak s 296 defence).
   Authority gold in the corpus: Madsen-Ries v Cooper, McIntosh v Fisk, Levin v Ikiua,
   Camray Farms, Kaikoura Freight, LSF Trustees.
4. **PPSA twist caught**: the client's financing statement (8 Apr 2025) came years
   after the equipment was first delivered (2019) — far outside PPSA s 40's
   20-business-day perfection window → interest unperfected/vests in insolvency; the
   bank's Jan 2024 GSA is first-in-time and perfected. Portacom/NZ Bloodstock live in
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
