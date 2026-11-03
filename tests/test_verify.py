# tests/test_verify.py — G1: the ground-truth citation checker (ROADMAP-0.2.0).
# Offline against a real CorpusStore with the fake embedder the smoke suite already
# uses — no Ollama, no sqlite-vec (verify reads the FTS tables only), no network.
import sys
from pathlib import Path

import pytest

PLUGIN = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PLUGIN / "mcp"))

from harness.corpus import CorpusStore, DocRecord, chunk_text  # noqa: E402
from harness.verify import verify_document  # noqa: E402

BODY = ("Harbour Freight Solutions Ltd agreed to pay default interest at the rate of "
        "twenty-six per cent per annum on all overdue amounts. The seller would deliver "
        "the equipment in two instalments during 2019. Clause 14 of the agreement governs "
        "the consequences of any substantial failure to perform the contract in full.")
SOURCE = "THE SUPPLY AGREEMENT TERMS\n\n" + BODY


@pytest.fixture
def store(tmp_path):
    def fake_embed(texts):                     # deterministic 8-dim bag-of-chars proxy
        return [[float(ord(c) % 17) for c in t[:8].ljust(8, "x")] for t in texts]

    s = CorpusStore(tmp_path / "corpus.sqlite3")          # no vectors: verify is FTS-only
    embedded = chunk_text("doc-a", SOURCE)
    s.ingest("harbour-freight", DocRecord("doc-a", SOURCE, "supply-agreement.md"),
             vectors=fake_embed(embedded), model="fake", provider="test")
    return s


def _draft(tmp_path, body: str, name="advice-letter.md") -> str:
    p = tmp_path / name
    p.write_text(body, encoding="utf-8")
    return str(p)


def test_verbatim_quote_verifies(store, tmp_path):
    p = _draft(tmp_path, 'The agreement says "default interest at the rate of '
                         'twenty-six per cent per annum on all overdue amounts" [E1.S1].')
    out = verify_document("harbour-freight", p, store=store)
    assert out["ok"] is True
    assert out["summary"] == {"verified": 1, "corrected": 0, "ungrounded": 0}
    assert out["refs"][0]["verdict"] == "VERIFIED" and out["refs"][0]["line"] == 1
    assert out["quotes"][0]["source_name"] == "supply-agreement.md"


def test_fabricated_quote_is_not_in_corpus(store, tmp_path):
    p = _draft(tmp_path, 'In *Kaikoura Freight v Reed* the court held that "a seller may '
                         'recover punitive damages where the buyer repudiates without '
                         'cause" [E1.S2].')
    out = verify_document("harbour-freight", p, store=store)
    assert out["ok"] is False
    assert out["summary"]["ungrounded"] == 1
    assert out["refs"][0]["verdict"] == "NOT_IN_CORPUS"
    assert out["quotes"][0]["source_name"] is None


def test_paraphrase_inside_quote_marks_is_not_in_corpus(store, tmp_path):
    """The headline trap: the words are all real, the span is not verbatim."""
    p = _draft(tmp_path, 'Interest accrues as "default interest at a rate of twenty six '
                         'per cent per annum on all overdue sums".')
    out = verify_document("harbour-freight", p, store=store)
    assert out["ok"] is False and out["summary"]["ungrounded"] == 1


def test_ref_with_no_quoted_span_is_ungrounded(store, tmp_path):
    """A model that cited from memory: the ref carries no quote, so nothing grounds it."""
    p = _draft(tmp_path, "The debtor is exposed under s 292 of the Insolvency Act 2006 "
                         "[E3.S2] on the preference analysis.")
    out = verify_document("harbour-freight", p, store=store)
    assert out["ok"] is False
    assert out["summary"]["ungrounded"] == 1 and not out["quotes"]
    assert out["refs"][0]["ref"] == "[E3.S2]"


def test_line_wrapped_curly_quoted_span_verifies(store, tmp_path):
    p = _draft(tmp_path, 'He said “default interest at the rate of\n'
                         ' twenty-six per cent per annum on all overdue amounts”.')
    out = verify_document("harbour-freight", p, store=store)
    assert out["ok"] is True and out["summary"]["verified"] == 1


def test_quote_shorter_than_the_floor_is_not_a_claim(store, tmp_path):
    p = _draft(tmp_path, 'Clause 14 bites "in full" of the obligation.')
    out = verify_document("harbour-freight", p, store=store)
    assert out["ok"] is True
    assert out["summary"] == {"verified": 0, "corrected": 0, "ungrounded": 0}


def test_every_ref_is_reported_even_when_two_share_one_quote(store, tmp_path):
    """summary counts CITATION INSTANCES: a quote carries its own count only when no ref
    cites it, so one quote cited twice is 2 (two things in the draft to check) but a
    quote restated anywhere without a ref is still counted once."""
    p = _draft(tmp_path, 'Interest runs at "default interest at the rate of twenty-six '
                         'per cent per annum" [E1.S1] and again [E1.S1].')
    out = verify_document("harbour-freight", p, store=store)
    assert len(out["refs"]) == 2 and len(out["quotes"]) == 1
    assert [r["verdict"] for r in out["refs"]] == ["VERIFIED", "VERIFIED"]
    assert out["summary"] == {"verified": 2, "corrected": 0, "ungrounded": 0}
    assert out["ok"] is True


def test_a_bad_quote_cited_twice_is_never_understated(store, tmp_path):
    """The property that justifies instance-counting: a fail-closed gate must report
    every place the draft asserts it, not 'one bad quote somewhere'."""
    p = _draft(tmp_path, 'Interest runs at "default interest at a rate of twenty six per '
                         'cent per annum" [E1.S1] and again [E1.S1].')
    out = verify_document("harbour-freight", p, store=store)
    assert out["summary"]["ungrounded"] == 2
    assert [r["verdict"] for r in out["refs"]] == ["NOT_IN_CORPUS"] * 2
    assert out["ok"] is False


def test_missing_deliverable_is_loud(store, tmp_path):
    out = verify_document("harbour-freight", str(tmp_path / "nope.md"), store=store)
    assert out["ok"] is False and "not found" in out["error"]
    assert out["summary"]["ungrounded"] == 0


def test_no_matter_bound_fails_closed(store, tmp_path):
    out = verify_document("", _draft(tmp_path, 'x "a quote long enough to count here"'),
                          store=store)
    assert out["ok"] is False and out["error"] == "no matter bound"


def test_matter_with_no_corpus_reports_zero_chunks(store, tmp_path):
    """Never "looks plausible": an ungrounded quote against an empty corpus."""
    p = _draft(tmp_path, 'The agreement says "default interest at the rate of '
                         'twenty-six per cent per annum on all overdue amounts".')
    out = verify_document("matter-never-ingested", p, store=store)
    assert out["ok"] is False
    assert out["corpus_chunks"] == 0 and out["summary"]["ungrounded"] == 1
