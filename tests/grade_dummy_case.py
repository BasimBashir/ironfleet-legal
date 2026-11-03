# G1 grading + the reproducible benchmark (ROADMAP-0.2.0 G1 "Grading"):
# build a real corpus store from dummy-case-harbour-freight/docs, then run
# ironfleet_verify_document over a draft carrying BOTH kinds of quote — real (must
# come back VERIFIED) and fabricated/paraphrased (must come back NOT_IN_CORPUS).
#
# The headline feature is judged mechanically on this one script's output: a court,
# opposing counsel, or a new user reproduces the proof with one command, no Ollama,
# no sqlite-vec, no network. Room for improvement: a fuller trap set lives in
# tests/test_verify.py; this file is the DEmo/publishable artefact.
"""Usage (from the plugin root):

    python tests/grade_dummy_case.py

Note: NOT `python -m tests.grade_dummy_case` — tests/ has no __init__.py, so it is a
PEP 420 namespace package and loses to a regular `tests` package in site-packages
(found live 2026-10-26: an unrelated ultralytics install shadowed it and its
`import torch` died). pytest tests/ is unaffected — pytest imports by file path.

Exit 0 = the checker passed every judgement, 1 = it got a verdict wrong.
"""
from __future__ import annotations

import sys
import tempfile
from pathlib import Path

PLUGIN = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PLUGIN / "mcp"))

from harness.corpus import CorpusStore, DocRecord, chunk_text  # noqa: E402
from harness.verify import verify_document  # noqa: E402

MATTER = "harbour-freight"
DUMMY_DOCS = PLUGIN / "dummy-case-harbour-freight" / "docs"
PARAPHRASE_TRAP = '"default interest at a rate of twenty six per cent per annum"'
FABRICATION_TRAP = '"Kaikoura Freight v Reed held that a seller may recover punitive damages"'


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


def main() -> int:
    tmp = Path(tempfile.mkdtemp(prefix="g1-grade-"))
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
    checks, failures = 0, []
    for label, body in paths:
        p = tmp / f"{label}.md"
        p.write_text(f"{body}\n", encoding="utf-8")
        got = verify_document(MATTER, str(p), store=store)
        print(f"  {label:<11} ok={got['ok']!s:<5} summary={got['summary']}")
        print(f"             quotes={got['quotes']}\n             refs={got['refs']}\n")
        checks += 1
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

    print(f"\n{checks} drafts checked — "
          f"{'PASS: real quotes VERIFIED, both traps NOT_IN_CORPUS' if not failures else 'FAIL'}")
    for f in failures:
        print(f"  - {f}")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
