# tests/test_operator_cli.py — W3 operator CLI: reclassify-tier stamps an ingested
# matter in place; bind-tier writes matter.json and t_ingest_docs defaults to it
# (proven end to end OFFLINE: HARNESS_HOME + a patched embed_fn, the test_smoke
# pattern); sync-version stamps the three version copies on a synthetic tree.
import json
import sys
from pathlib import Path

import pytest

PLUGIN = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PLUGIN / "mcp"))

from harness.cli import bind_tier, reclassify_tier, sync_version        # noqa: E402
from harness.corpus import CorpusStore, DocRecord, bound_tier, chunk_text  # noqa: E402


def fake_embed(texts):
    base = [[float(ord(c) % 17) for c in t[:8].ljust(8, "x")] for t in texts]
    return [v * 128 for v in base]        # _stores() builds a dim=1024 VectorStore


def _ingest(store, matter, doc_id, text, tier="T1"):
    store.ingest(matter, DocRecord(doc_id, text, f"{doc_id}.txt", trust_tier=tier),
                 vectors=fake_embed(chunk_text(doc_id, text)),
                 model="fake", provider="test")


DOC = ("We acknowledge receipt of your letter and confirm delivery of the goods "
       "ordered last March. ") * 40                       # 200+ words: past the scan guard


def test_reclassify_tier_stamps_ingested_matter(tmp_path):
    store = CorpusStore(tmp_path / "corpus.sqlite3")
    _ingest(store, "m-tier", "d-a", DOC, tier="T0")
    _ingest(store, "m-tier", "d-b", DOC + " More words follow here.", tier="T1")
    out = reclassify_tier("m-tier", "T3", root=tmp_path)
    assert out["ok"] is True and out["docs"] == 2
    assert {d["trust_tier"] for d in store.docs("m-tier")} == {"T3"}
    assert reclassify_tier("m-tier", "T9", root=tmp_path)["ok"] is False
    assert "no ingested corpus" in reclassify_tier("m-none", "T1",
                                                   root=tmp_path)["error"]


def test_bind_tier_roundtrip(tmp_path):
    assert bind_tier("m-x", "T3", root=tmp_path)["bound"] == {"trust_tier": "T3"}
    assert bound_tier(tmp_path, "m-x") == "T3"
    assert bind_tier("m-x", "T9", root=tmp_path)["ok"] is False
    assert bound_tier(tmp_path, "m-never") is None        # unbound matter
    assert bind_tier("m-x", "clear", root=tmp_path)["bound"] is None
    assert bound_tier(tmp_path, "m-x") is None
    (tmp_path / "matter.json").write_text("{corrupt", encoding="utf-8")
    assert bound_tier(tmp_path, "m-x") is None            # corrupt binding -> unbound


def test_ingest_defaults_to_bound_tier(tmp_path, monkeypatch):
    monkeypatch.setenv("HARNESS_HOME", str(tmp_path))
    import harness.localstack as localstack
    monkeypatch.setattr(localstack, "embed_fn", fake_embed)
    import server
    assert bind_tier("m-bind", "T3", root=tmp_path)["ok"]
    src1 = tmp_path / "one.txt"
    src1.write_text(DOC, encoding="utf-8")
    out = server.dispatch("ironfleet_ingest_docs",
                          {"matter": "m-bind", "path": str(src1)})
    assert out["ingested"] == ["one.txt"]
    store = CorpusStore(tmp_path / "corpus.sqlite3")
    assert store.docs("m-bind")[0]["trust_tier"] == "T3"  # the binding, not the default
    src2 = tmp_path / "two.txt"
    src2.write_text(DOC + " Different bytes for a different document. ",
                    encoding="utf-8")
    server.dispatch("ironfleet_ingest_docs",
                    {"matter": "m-bind", "path": str(src2), "trust_tier": "T0"})
    tiers = {d["name"]: d["trust_tier"] for d in store.docs("m-bind")}
    assert tiers == {"one.txt": "T3", "two.txt": "T0"}    # explicit call tier wins


def test_sync_version_stamps_three_copies(tmp_path):
    pj = tmp_path / ".claude-plugin"
    pj.mkdir(parents=True)
    (pj / "plugin.json").write_text(
        json.dumps({"name": "x", "version": "1.2.3"}), encoding="utf-8")
    (pj / "marketplace.json").write_text(
        json.dumps({"plugins": [{"name": "x", "version": "1.2.3"}]}), encoding="utf-8")
    (tmp_path / "mcp").mkdir()
    (tmp_path / "mcp" / "server.py").write_text('VERSION = "1.2.0"\n',
                                                encoding="utf-8")
    out = sync_version("2.0.0", root=tmp_path)
    assert out["ok"] is True and len(out["changed"]) == 3
    assert json.loads((pj / "plugin.json").read_text(
        encoding="utf-8"))["version"] == "2.0.0"
    assert json.loads((pj / "marketplace.json").read_text(
        encoding="utf-8"))["plugins"][0]["version"] == "2.0.0"
    assert 'VERSION = "2.0.0"' in (tmp_path / "mcp" / "server.py").read_text(
        encoding="utf-8")
    assert sync_version("not-a-version", root=tmp_path)["ok"] is False


def test_sync_version_no_arg_repairs_drift(tmp_path):
    pj = tmp_path / ".claude-plugin"
    pj.mkdir(parents=True)
    (pj / "plugin.json").write_text(
        json.dumps({"name": "x", "version": "3.1.4"}), encoding="utf-8")
    (pj / "marketplace.json").write_text(
        json.dumps({"plugins": [{"name": "x", "version": "3.0.0"}]}), encoding="utf-8")
    (tmp_path / "mcp").mkdir()
    (tmp_path / "mcp" / "server.py").write_text('VERSION = "3.0.0"\n',
                                                encoding="utf-8")
    out = sync_version(root=tmp_path)                     # no arg: re-sync to plugin.json
    assert out["ok"] is True and out["version"] == "3.1.4"
    assert len(out["changed"]) == 2                       # the two drifted copies
