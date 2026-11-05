# G1 grading + the reproducible benchmark (ROADMAP-0.2.0 G1 "Grading"), extended
# for M5: build a real corpus store from dummy-case-harbour-freight/docs, then run
# ironfleet_verify_document over a draft carrying BOTH kinds of quote — real (must
# come back VERIFIED) and fabricated/paraphrased (must come back NOT_IN_CORPUS).
# Then the M5 dossier loop: two simulated court rounds through server.dispatch —
# debrief → prediction-vs-outcome diff → outcomes rows → strategy v2 → v3, with
# every deadline kernel-computed (a caller-supplied `due` must be refused) — and
# the R-CL2 corpus CRUD roundtrip (delete_docs / reingest).
#
# The headline feature is judged mechanically on this one script's output: a court,
# opposing counsel, or a new user reproduces the proof with one command, no Ollama,
# no network. The G1 verify section needs no sqlite-vec; the M5 lifecycle section
# DOES (it drives the real hybrid search through the store), so run it with the
# harness-core venv python. Room for improvement: a fuller trap set lives in
# tests/test_verify.py; this file is the DEMO/publishable artefact.
"""Usage (from the plugin root):

    python tests/grade_dummy_case.py

Note: NOT `python -m tests.grade_dummy_case` — tests/ has no __init__.py, so it is a
PEP 420 namespace package and loses to a regular `tests` package in site-packages
(found live 2026-10-26: an unrelated ultralytics install shadowed it and its
`import torch` died). pytest tests/ is unaffected — pytest imports by file path.

Exit 0 = every judgement passed, 1 = something got a verdict wrong.
"""
from __future__ import annotations

import sys
import tempfile
from datetime import date
from pathlib import Path

PLUGIN = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PLUGIN / "mcp"))

from harness.corpus import CorpusStore, DocRecord, chunk_text  # noqa: E402
from harness.verify import verify_document  # noqa: E402
from harness.module_e.vendored.court_calendar import court_filing_deadline  # noqa: E402

MATTER = "harbour-freight"
DUMMY_DOCS = PLUGIN / "dummy-case-harbour-freight" / "docs"
ROUNDS = PLUGIN / "dummy-case-harbour-freight" / "court-rounds"
PARAPHRASE_TRAP = '"default interest at a rate of twenty six per cent per annum"'
FABRICATION_TRAP = '"Kaikoura Freight v Reed held that a seller may recover punitive damages"'


def fake1024(texts):                        # deterministic 1024-dim proxy (store dim)
    return [[float((ord(t[i % len(t) or 1]) + i) % 17) for i in range(1024)]
            for t in texts]


def build(store_dir: Path) -> CorpusStore:
    def fake_embed(texts):                     # deterministic 8-dim bag-of-chars proxy
        return [[float(ord(c) % 17) for c in t[:8].ljust(8, "x")] for t in texts]

    store = CorpusStore(store_dir / "corpus.sqlite3")
    sources: list[str] = []
    for f in sorted(DUMMY_DOCS.iterdir()):
        if not f.is_file():
            continue
        text = f.read_text(encoding="utf-8")
        if len(text.split()) < 20:             # the checklist's own floor was 200; the
            continue                           # bench drafts need >20 to split at all
        doc_id = f"doc-{f.stem}"
        embedded = chunk_text(doc_id, text)
        store.ingest(MATTER, DocRecord(doc_id, text, f.name),
                     vectors=fake_embed(embedded), model="fake", provider="grade")
        sources.append(f"{f.name} ({len(embedded)} chunks)")
    print(f"versus {store.doc_count(MATTER)} documents, {store.count(MATTER)} chunks:")
    for s in sources:
        print(f"  - {s}")
    return store


def g1_verify(tmp: Path, failures: list[str]) -> None:
    store = build(tmp)
    print(f"store: {tmp / 'corpus.sqlite3'}\n")

    paths = [
        # the 'correct run': a REAL span of contract prose from supply-agreement.md, so
        # the benchmark passes a quotation a court would actually read — and fails
        # loudly the day that document's wording drifts.
        ("good", 'Interest accrues as "Any amount not paid by its due date bears '
                 'default interest at 26% per annum from due date until payment" '
                 '[E1.S1] (clause 3).'),
        ("fabricated", f"the court held that {FABRICATION_TRAP} [E1.S2]."),
        ("paraphrased", f"Interest runs as {PARAPHRASE_TRAP} [E1.S3]."),
        ("no-quote-ref", "The 2019 statement is time-barred [E9.S9]."),
    ]
    for label, body in paths:
        p = tmp / f"{label}.md"
        p.write_text(f"{body}\n", encoding="utf-8")
        got = verify_document(MATTER, str(p), store=store)
        print(f"  {label:<11} ok={got['ok']!s:<5} summary={got['summary']}")
        print(f"             quotes={got['quotes']}\n             refs={got['refs']}\n")
        if label == "good" and not got["ok"]:
            failures.append(f"{label}: a real verbatim quote must come back OK, got "
                            f"{got['summary']}")
        if label != "good" and got["ok"]:
            failures.append(f"{label}: the trap draft must NOT be 'ok'")
        if label == "good" and not any(
                q["source_name"] == "supply-agreement.md" and q["verdict"] == "VERIFIED"
                for q in got["quotes"]):
            failures.append(f"{label}: the verified quote must come from "
                            f"supply-agreement.md, got {got['quotes']}")


def m5_lifecycle(tmp: Path, failures: list[str]) -> None:
    """Two simulated court rounds through server.dispatch, fully offline: seed
    strategy v1 + predictions, debrief round 1 (minute fixture), outcomes rows,
    strategy v2 + a new prediction, kernel deadlines, debrief round 2, outcome,
    strategy v3 — then the R-CL2 CRUD roundtrip on a fresh dummy doc."""
    import os
    os.environ["HARNESS_HOME"] = str(tmp / "m5")   # own store: G1's build() already
    import harness.localstack as localstack        # ingested dummy docs into tmp/
    import server
    localstack.embed_fn = fake1024        # module attr: t_ingest_docs re-imports per call

    def run(tool: str, args: dict) -> dict:
        return server.dispatch(tool, args)

    def app(entity: str, event: dict) -> dict:
        return run("ironfleet_dossier_append",
                   {"matter": MATTER, "entity": entity, "workspace": ws, "event": event})

    def want(cond: bool, msg: str) -> None:
        if not cond:
            failures.append(msg)

    ws = str(tmp / "matters" / "harbour-freight")

    # the two synthetic minute fixtures carry the ground truths the loop is graded on
    m1 = (ROUNDS / "minute-round-1.md").read_text(encoding="utf-8")
    m2 = (ROUNDS / "minute-round-2.md").read_text(encoding="utf-8")
    want("20 working days" in m1, "fixture round 1 lost its needle: '20 working days'")
    want("$100,000" in m2 and "$26,000" in m2,
         "fixture round 2 lost its needles: '$100,000'/'$26,000'")

    # seed: opening strategy v1 + two predictions to be diffed against round 1
    app("strategy", {"version": 1, "file": "strategy-v1.md",
                     "why_changed": "opening strategy after the statement of claim",
                     "next_actions": ["prove the debt, seek summary judgment"]})
    app("predictions", {"prediction_id": "p1", "strategy_version": 1,
                        "claim": "The court orders the judgment sum payable "
                                 "IMMEDIATELY on entry."})
    app("predictions", {"prediction_id": "p2", "strategy_version": 1,
                        "claim": "Judgment is entered for the claimant "
                                 "(Powell Builders)."})

    # round 1 (2026-11-05): judgment yes, immediacy no — p1 must pair as a miss
    d1 = run("ironfleet_debrief_ingest", {"matter": MATTER, "workspace": ws, "event": {
        "event_type": "minute", "date": "2026-11-05",
        "judge_said": "judgment entered for the plaintiff in $126,000; immediate "
                      "enforcement REFUSED; time to pay: 20 working days",
        "orders": ["judgment for the plaintiff in the sum of $126,000",
                   "payment within 20 working days of the date of this minute",
                   "costs reserved; memoranda within 10 working days if not agreed"],
        "source_file": "court-rounds/minute-round-1.md"}})
    want(d1["open_count"] == 2, f"round-1 diff must carry both seeded predictions, "
                                f"got open_count={d1['open_count']}")
    want([e["prediction_id"] for e in d1["diff"]] == ["p1", "p2"],
         f"round-1 diff ids wrong: {[e['prediction_id'] for e in d1['diff']]}")

    # the case-manager records the verdicts as DATA (match is judgement, never computed)
    app("outcomes", {"prediction_id": "p1", "match": False, "court_date": "2026-11-05",
                     "actual": "payment within 20 working days, not immediately",
                     "expected": d1["diff"][0]["claim"]})
    app("outcomes", {"prediction_id": "p2", "match": True, "court_date": "2026-11-05",
                     "actual": "judgment entered for the plaintiff",
                     "expected": d1["diff"][1]["claim"]})

    # strategy v2 (what the court decided that v1 got wrong) + one new prediction
    app("strategy", {"version": 2, "file": "strategy-v2.md",
                     "why_changed": "court refused immediate enforcement; pivot to "
                                    "the time-to-pay window and enforcement readiness",
                     "next_actions": ["watch the 20-working-day window",
                                      "prepare leave-to-enforce papers"]})
    app("predictions", {"prediction_id": "p3", "strategy_version": 2,
                        "claim": "The defendant pays the full $126,000 within the "
                                 "20-working-day window."})

    # deadlines are kernel-computed only — and a caller-supplied due is refused
    k1 = court_filing_deadline(date(2026, 11, 5), 20).isoformat()
    reg1 = run("ironfleet_deadline_register", {"matter": MATTER, "workspace": ws,
              "what": "judgment sum payable", "service_date": "2026-11-05",
              "days": 20, "missed_consequence": "leave to enforce without further "
              "hearing"})
    want(reg1["due"] == k1, f"round-1 payment deadline must equal the kernel's "
                            f"({k1}), got {reg1['due']}")
    try:
        run("ironfleet_deadline_register", {"matter": MATTER, "workspace": ws,
            "what": "model-invented", "service_date": "2026-11-05",
            "due": "2026-12-01"})
        failures.append("deadline_register ACCEPTED a caller-supplied 'due' — the "
                        "kernel-only rule is broken")
    except RuntimeError:
        print("  kernel-only refusal: caller-supplied 'due' refused, as designed")

    # round 2 (2026-12-08): part payment only — p3 must pair, and only p3
    d2 = run("ironfleet_debrief_ingest", {"matter": MATTER, "workspace": ws, "event": {
        "event_type": "minute", "date": "2026-12-08",
        "judge_said": "part payment $100,000 received 27 November 2026 within the "
                      "window; balance $26,000 outstanding; LEAVE TO ENFORCE granted",
        "orders": ["part payment of $100,000 recorded (received 2026-11-27)",
                   "leave to enforce granted for the outstanding balance of $26,000",
                   "costs $1,500 to the plaintiff within 10 working days",
                   "defendant evidence within 15 working days"],
        "next_date": "2027-02-10",
        "source_file": "court-rounds/minute-round-2.md"}})
    want(d2["open_count"] == 1 and d2["diff"][0]["prediction_id"] == "p3",
         f"round-2 diff must carry exactly p3, got "
         f"{[e['prediction_id'] for e in d2['diff']]}")

    app("outcomes", {"prediction_id": "p3", "match": False, "court_date": "2026-12-08",
                     "actual": "part payment $100,000 only; $26,000 balance "
                               "outstanding — leave to enforce granted",
                     "expected": d2["diff"][0]["claim"]})
    app("strategy", {"version": 3, "file": "strategy-v3.md",
                     "why_changed": "defendant short-paid within the window; move to "
                                    "executing the granted leave to enforce for the "
                                    "balance",
                     "next_actions": ["enforce the $26,000 balance",
                                      "file evidence on the security registration"]})

    # round-2 kernel deadlines (costs 10 wd, evidence 15 wd from the minute date)
    for what, days in (("costs $1,500 payable", 10),
                       ("defendant evidence filed and served", 15)):
        reg = run("ironfleet_deadline_register", {"matter": MATTER, "workspace": ws,
                  "what": what, "service_date": "2026-12-08", "days": days})
        want(reg["due"] == court_filing_deadline(date(2026, 12, 8), days).isoformat(),
             f"round-2 deadline '{what}' drifted from the kernel: {reg['due']}")

    # end-state assertions: the whole chain, one read each
    strat = run("ironfleet_dossier_read", {"matter": MATTER, "entity": "strategy",
                                           "workspace": ws})
    want(strat["versions"] == [1, 2, 3], f"strategy chain must be [1, 2, 3], got "
                                         f"{strat['versions']}")
    preds = run("ironfleet_dossier_read", {"matter": MATTER, "entity": "predictions",
                                           "workspace": ws})
    want(preds["unresolved"] == [], f"every prediction must have an outcomes row by "
                                    f"round 2, unresolved={preds['unresolved']}")
    dl = run("ironfleet_dossier_read", {"matter": MATTER, "entity": "deadlines",
                                        "workspace": ws})
    want(len(dl["deadlines"]) >= 3 and all(r.get("source") == "kernel"
                                           for r in dl["deadlines"]),
         f"every registered deadline must be kernel-sourced, got "
         f"{[(r.get('what'), r.get('source')) for r in dl['deadlines']]}")
    court = run("ironfleet_dossier_read", {"matter": MATTER, "entity": "court_events",
                                           "workspace": ws})
    want(court["events"][-1].get("next_date") == "2027-02-10",
         "minute-2 CMC date must ride the court event as next_date")
    for r in dl["deadlines"]:
        print(f"  deadline: {r['due']}  {r['what']}  [{r.get('source')}]")

    # R-CL2 CRUD roundtrip on a fresh dummy doc (delete → search empties → reingest)
    doc = tmp / "supply-agreement.md"
    doc.write_text("SUPPLY AGREEMENT (grading fixture)\n\nThe supplier agrees to "
                   "deliver freight services and the customer agrees to pay the "
                   "invoice within 20 working days of invoice. Any amount not paid "
                   "by its due date bears default interest at 26 per cent per annum "
                   "from due date until payment. " * 20, encoding="utf-8")
    ing = run("ironfleet_ingest_docs", {"matter": MATTER, "path": str(doc)})
    want(ing["ingested"] == ["supply-agreement.md"],
         f"CRUD ingest failed: {ing.get('ingested')} / {ing.get('skipped')}")
    s1 = run("ironfleet_corpus_search", {"matter": MATTER, "rerank": False,
                                         "query": "default interest 26 per cent"})
    want(bool(s1["passages"]), "search must hit the ingested doc before delete")
    dele = run("ironfleet_delete_docs", {"matter": MATTER, "name": "supply-agreement.md"})
    s2 = run("ironfleet_corpus_search", {"matter": MATTER, "rerank": False,
                                         "query": "default interest 26 per cent"})
    want(bool(dele["removed"]) and s2["passages"] == [],
         f"delete must remove the doc from search, got removed={dele.get('removed')} "
         f"passages={len(s2['passages'])}")
    reing = run("ironfleet_reingest", {"matter": MATTER, "path": str(doc)})
    s3 = run("ironfleet_corpus_search", {"matter": MATTER, "rerank": False,
                                         "query": "default interest 26 per cent"})
    # replaced=[] is honest here: we deleted first, so nothing existed to replace —
    # the true edit-then-reingest replace-in-place case is tests/test_dossier.py's
    want(reing["ingested"] == ["supply-agreement.md"] and bool(s3["passages"]),
         f"reingest must restore search after a delete, got "
         f"ingested={reing.get('ingested')} passages={len(s3['passages'])}")
    print(f"  CRUD: delete removed {dele['chunks']} chunks / {dele['vectors']} "
          f"vectors; reingest restored search (replaced={reing['replaced']} - "
          f"empty because we deleted first)")


def main() -> int:
    tmp = Path(tempfile.mkdtemp(prefix="g1-grade-"))
    failures: list[str] = []

    print("=== G1 verify: real quotes VERIFIED, traps NOT_IN_CORPUS ===\n")
    g1_verify(tmp, failures)
    print(f"G1 section: {'PASS' if not failures else 'FAIL'}")

    print("\n=== M5 dossier loop: two simulated court rounds + R-CL2 CRUD ===\n")
    m5_lifecycle(tmp, failures)

    if failures:
        print(f"\nFAIL: {len(failures)} judgement(s) wrong:")
        for f in failures:
            print(f"  - {f}")
        return 1
    print("\nPASS: G1 quotes graded, two court rounds debriefed (strategy v1->v3, "
          "outcomes recorded, kernel-only deadlines, no unresolved predictions), "
          "CRUD roundtrip clean")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
