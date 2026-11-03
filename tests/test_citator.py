# tests/test_citator.py — W3: the cites join over a synthetic law-judgments matter.
# Mechanical, offline: CorpusStore with no vectors (the citator reads only the
# docs/fts/cites tables). Every shape the self-vs-citing rule must survive: a
# heading-shaped authority, later/earlier/year-unknown citing judgments, a statute
# pin promoted from its provision chunk, and the fail-closed empty corpus.
import sys
from pathlib import Path

PLUGIN = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PLUGIN / "mcp"))

from harness.citator import citator, citing_judgments                  # noqa: E402
from harness.corpus import CorpusStore, DocRecord, chunk_text          # noqa: E402


def fake_embed(texts):                      # same offline proxy as test_smoke.py
    return [[float(ord(c) % 17) for c in t[:8].ljust(8, "x")] for t in texts]


def _ingest(store, matter, doc_id, text):
    store.ingest(matter, DocRecord(doc_id, text, f"{doc_id}.txt"),
                 vectors=fake_embed(chunk_text(doc_id, text)),
                 model="fake", provider="test")


AUTH = ("HARBOUR FREIGHT LTD V MARINE LOGISTICS LTD [2018] NZSC 5\n\n"
        "Contract — discharge — repudiation. The appellant shipped cargo under a "
        "charterparty and the respondent refused the berth at the port of loading.\n\n"
        + ("The charterparty clause governed the delivery schedule at the port and "
           "the demurrage followed the freight contract. The trial judge held the "
           "berth refusal repudiatory and awarded damages on the market freight. ") * 8)

_CITE = ("In Harbour Freight Ltd v Marine Logistics Ltd [2018] NZSC 5 the Supreme "
         "Court held a berth refusal repudiatory and the demurrage followed. ")
CITE_B = ("PORT AUTHORITY V STEVEDORE SERVICES [2022] NZCA 99\n\n"
          "Appeal — agency — whether the stevedore was the port authority's agent "
          "for notice purposes.\n\n" + _CITE * 6)
CITE_C = ("COASTAL CARRIERS V HARBOURMASTER [2019] NZHC 77\n\n"
          "Judicial review — mooring levies — whether the levy was lawfully set.\n\n"
          + _CITE * 6)
CITE_D = ("RIVERSIDE MILLS V GRAIN BOARD [2017] NZSC 31\n\n"
          "Contract — penalty rates — whether the storage rate was a penalty.\n\n"
          + _CITE * 6)
# cites by name only, no neutral citation anywhere: the year-unknown bucket
CITE_E = ("RE MARINE SALVAGE SERVICES\n\n"
          "Salvage — remuneration — whether the salvage convention applied.\n\n"
          + ("In Harbour Freight Ltd v Marine Logistics Ltd the Supreme Court held "
             "a berth refusal repudiatory and the salvage claim followed the "
             "charterparty. ") * 6)

PROV = ("Personal Property Securities Act 1999, s 6\n\n"
        + ("Meaning of security interest: a security interest in personal property "
           "is provided for by this section and the attachment rules follow the "
           "agreement of the parties at the time value is given. ") * 10)
CITE_S = ("BANK V TRADER CO [2020] NZHC 12\n\n"
          "Security — attachment — when the interest attached on delivery.\n\n"
          + ("The plaintiff held a security interest under Personal Property "
             "Securities Act 1999, s 6 and the interest attached on delivery of "
             "the goods to the debtor. ") * 8)

CASE_Q = "Harbour Freight Ltd v Marine Logistics Ltd [2018] NZSC 5"
PIN_Q = "Personal Property Securities Act 1999, s 6"


def _corpus(tmp_path):
    store = CorpusStore(tmp_path / "corpus.sqlite3")
    for did, text in (("j-auth", AUTH), ("j-b", CITE_B), ("j-c", CITE_C),
                      ("j-d", CITE_D), ("j-e", CITE_E), ("prov", PROV),
                      ("j-s", CITE_S)):
        _ingest(store, "law-judgments", did, text)
    return store


def test_later_citing_judgments(tmp_path):
    out = citing_judgments("law-judgments", CASE_Q, store=_corpus(tmp_path))
    assert out["ok"] is True
    assert out["authority"]["in_corpus"] is True
    assert out["authority"]["year"] == "2018"
    got = {c["doc_id"]: c for c in out["citing"]}
    assert set(got) == {"j-b", "j-c", "j-d", "j-e"}      # the authority itself never
    assert got["j-b"]["later"] is True and got["j-c"]["later"] is True
    assert got["j-d"]["later"] is False                  # [2017]: cites a future case
    assert got["j-e"]["later"] is None                   # no neutral citation at all
    assert out["summary"] == {"citing_docs": 4, "later": 2, "same_or_earlier": 1,
                              "year_unknown": 1}


def test_query_without_year_falls_back_to_corpus(tmp_path):
    out = citing_judgments("law-judgments",
                           "Harbour Freight Ltd v Marine Logistics Ltd",
                           store=_corpus(tmp_path))
    assert out["authority"]["year"] == "2018"            # from the corpus doc's header
    assert out["summary"]["later"] == 2


def test_statute_pin_authority(tmp_path):
    out = citing_judgments("law-judgments", PIN_Q, store=_corpus(tmp_path))
    assert out["authority"]["in_corpus"] is True          # the provision chunk itself
    assert {c["doc_id"] for c in out["citing"]} == {"j-s"}
    assert out["citing"][0]["later"] is None              # statutes carry no decision year


def test_no_citation_span_rejected(tmp_path):
    store = CorpusStore(tmp_path / "corpus.sqlite3")
    out = citing_judgments("law-judgments", "the big shipping case", store=store)
    assert out["ok"] is False and "no citation span" in out["error"]


def test_empty_matter_fails_closed(tmp_path):
    store = CorpusStore(tmp_path / "corpus.sqlite3")      # store exists, matter doesn't
    out = citing_judgments("law-judgments", "A v B", store=store)
    assert out["ok"] is False and "empty corpus" in out["error"]
    assert citing_judgments("", "A v B", store=store)["ok"] is False


def test_path_mode_reports_every_authority(tmp_path):
    draft = tmp_path / "advice.md"
    draft.write_text(f"The leading authority is {CASE_Q}; the interest attached "
                     f"under {PIN_Q}.\n", encoding="utf-8")
    out = citator("law-judgments", path=str(draft), store=_corpus(tmp_path))
    assert out["ok"] is True
    by_key = {a["key"]: a for a in out["authorities"]}
    assert len(by_key) == 2
    assert by_key["case:harbour freight ltd v marine logistics ltd"]["later_citing"] == 2
    assert by_key["personal property securities act|1999|6"]["citing_docs"] == 1
    assert out["summary"]["with_later_citations"] >= 1
