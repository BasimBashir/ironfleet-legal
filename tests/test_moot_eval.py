# tests/test_moot_eval.py — the Track B5 seeded-flaw eval: run the moot gate's
# deterministic pre-pass over the 30 flawed docs + 4 clean controls in
# tests/moot-eval/, score with moot.score(), and hold the line: >= 0.90 seeded
# critical detection, 0 false positives on the controls. Offline — fake
# embeddings, the harbour-freight dummy corpus, no Ollama, no Claude, no network.
import json
import os
import sys
from pathlib import Path

import pytest

PLUGIN = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PLUGIN / "mcp"))

MEVAL = PLUGIN / "tests" / "moot-eval"
CORPUS = PLUGIN / "dummy-case-harbour-freight" / "docs"
MATTER = "harbour-freight"

import server   # noqa: E402
import moot     # noqa: E402
import harness.localstack as localstack   # noqa: E402


@pytest.fixture(scope="session")
def eval_env(tmp_path_factory):
    """The store (dummy corpus ingested), one run with both kernel computations
    logged (the wrong_deadline docs are judged against these), and the evidence
    register (A/B/C) — everything the gate sees, logged mechanically."""
    root = tmp_path_factory.mktemp("moot-eval-store")
    old_home = os.environ.get("HARNESS_HOME")
    os.environ["HARNESS_HOME"] = str(root)
    old_embed = localstack.embed_fn
    localstack.embed_fn = lambda texts: [
        [float((ord(t[i % len(t) or 1]) + i) % 17) for i in range(1024)]
        for t in texts]
    try:
        ingested = 0
        for f in sorted(CORPUS.iterdir()):
            if f.is_file():
                r = server.dispatch("ironfleet_ingest_docs",
                                    {"matter": MATTER, "path": str(f)})
                ingested += r["chunks"]
        assert ingested > 0, "dummy corpus did not chunk"
        run = server.dispatch("ironfleet_begin_run",
                              {"matter": MATTER, "prompt": "moot eval",
                               "workspace": str(root)})
        for payload in (
                # the filing-deadline kernel's computation: 15 days from 3 April 2026
                {"tool": "ironfleet_filing_deadline", "deadline": "2026-04-24",
                 "days": 15, "service_date": "2026-04-03"},
                # the SD kernel's: $1,000 minimum satisfied, 15 working days to comply
                {"tool": "ironfleet_statutory_demand", "compliance_deadline":
                 "2026-04-24", "compliance_period_days": 15},
        ):
            server.dispatch("ironfleet_log_event",
                            {"run_id": run["run_id"], "event": "tool_result",
                             "payload": payload, "matter": MATTER,
                             "workspace": str(root)})
        import dossier
        for label in ("Exhibit A", "Exhibit B", "Exhibit C"):
            dossier.append(MATTER, "evidence",
                           {"op": "add", "label": label, "file": f"{label}.pdf"},
                           workspace=str(root))
        yield {"root": str(root), "run_id": run["run_id"]}
    finally:
        localstack.embed_fn = old_embed
        if old_home is None:
            os.environ.pop("HARNESS_HOME", None)
        else:
            os.environ["HARNESS_HOME"] = old_home


def test_seeded_flaws_meet_the_bar(eval_env):
    """30 seeded critical flaws (6 per class x 5 classes) + 4 clean controls:
    detection >= 0.90 overall, 0 controls blocked. The table prints on failure."""
    manifest = json.loads((MEVAL / "manifest.json").read_text(encoding="utf-8"))
    results = {}
    for doc in manifest["docs"]:
        p = MEVAL / doc["file"]
        assert p.exists(), f"eval doc missing: {doc['file']}"
        results[doc["file"]] = moot.moot_check(
            MATTER, str(p), run_id=eval_env["run_id"], workspace=eval_env["root"])
    s = moot.score(manifest, results)
    lines = [f"{c:17s} {pc['detected']:>2}/{pc['docs']:<2}"
             for c, pc in s["per_class"].items()]
    table = (f"overall {s['overall']['detected']}/{s['overall']['docs']} "
             f"= {s['overall']['rate']:.2f} (bar {s['bar']}); "
             f"controls FP {s['controls']['false_positives']}/{s['controls']['docs']}; "
             + "  ".join(lines))
    assert s["meets_bar"], table
    assert s["controls"]["false_positives"] == 0, table
