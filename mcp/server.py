# mcp/server.py — the ironfleet stdio MCP server (stdlib only; zero pip deps here —
# sqlite-vec is the one optional env dep, installed by /ironfleet-legal:doctor).
# MECHANICAL-ONLY by construction (the R4 ruling for the plugin line): every tool below
# is local computation or a localhost call to the user's own Ollama/llama-server. The
# LLM is the user's own Claude; this server never talks to one.
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

_MCP_DIR = str(Path(__file__).resolve().parent)
sys.path.insert(0, _MCP_DIR)   # vendored `harness` + records
# The killable-parse watchdog (ingest_generic.extract_text) re-imports this package in a
# CHILD python; without PYTHONPATH that child only worked where `harness` was pip-installed.
os.environ["PYTHONPATH"] = _MCP_DIR + os.pathsep + os.environ.get("PYTHONPATH", "")

import records                                            # noqa: E402
from harness.corpus import CorpusStore, ironfleet_corpus_search  # noqa: E402
from harness.module_e.kernel_tools import statutory_demand, without_prejudice  # noqa: E402
from harness.module_e.vendored.court_calendar import court_filing_deadline  # noqa: E402
from harness.paths import resolve_store_root              # noqa: E402
from harness.vectors import VectorStore                   # noqa: E402

VERSION = "0.1.0"


def _stores():
    root, _source = resolve_store_root()
    return (CorpusStore(Path(root) / "corpus.sqlite3",
                        vectors=VectorStore(Path(root) / "vectors.sqlite3")), root)


# ------------------------------------------------------------------ tool handlers

def t_corpus_search(a: dict) -> dict:
    store, _ = _stores()
    return ironfleet_corpus_search(a, store=store)


def t_statutory_demand(a: dict) -> dict:
    return statutory_demand(a)


def t_without_prejudice(a: dict) -> dict:
    return without_prejudice(a)


def t_filing_deadline(a: dict) -> dict:
    from datetime import date
    d = court_filing_deadline(date.fromisoformat(a["service_date"]),
                              int(a["days"]), region=a.get("region"),
                              jurisdiction=a.get("jurisdiction", "nz"))
    return {"deadline": d.isoformat(),
            "note": "day of service excluded; only working days counted "
                    "(weekends + NZ public holidays)"}


def t_ingest_docs(a: dict) -> dict:
    from harness.ingest_generic import extract_text
    from harness.corpus import DocRecord, chunk_text
    import hashlib
    store, _ = _stores()
    matter = a["matter"]
    src = Path(a["path"])
    files = sorted(src.glob("**/*")) if src.is_dir() else [src]
    report = {"ingested": [], "skipped": [], "resumed": [], "chunks": 0}
    for f in files:
        if not f.is_file() or f.name.startswith("."):
            continue
        try:
            text = extract_text(f)
        except Exception as ex:                        # noqa: BLE001 — recorded, keep going
            report["skipped"].append(f"{f.name}: {ex}")
            continue
        if len(text.split()) < 200:
            report["skipped"].append(f"{f.name}: {len(text.split())} words (<200, scanned?)")
            continue
        sha = hashlib.sha256(text.encode("utf-8")).hexdigest()
        if store.has_doc(matter, sha):
            report["resumed"].append(f.name)
            continue
        texts = chunk_text(f"doc-{sha[:12]}", text)
        vecs = []
        from harness.localstack import embed_fn
        for i in range(0, len(texts), 64):
            vecs.extend(embed_fn(texts[i:i + 64]))
        store.ingest(matter, DocRecord(f"doc-{sha[:12]}", text, f.name),
                     vectors=vecs, model="bge-m3", provider="ollama-embed")
        report["ingested"].append(f.name)
        report["chunks"] += len(texts)
    return report


def t_list_docs(a: dict) -> dict:
    store, root = _stores()
    m = a["matter"]
    return {"matter": m, "docs": store.docs(m), "chunks": store.count(m),
            "store_root": str(root)}


def t_begin_run(a: dict) -> dict:
    return records.begin_run(a["matter"], a.get("prompt", ""),
                             workspace=a.get("workspace"), stages=a.get("stages"))


def t_log_event(a: dict) -> dict:
    return records.log(a["run_id"], a.get("event", "note"), a.get("payload"),
                       matter=a.get("matter", ""), workspace=a.get("workspace"))


def t_finish_run(a: dict) -> dict:
    return records.finish_run(a["run_id"], a.get("status", "complete"),
                              a.get("deliverables"), a.get("summary", ""),
                              matter=a.get("matter", ""), workspace=a.get("workspace"))


def t_provenance(a: dict) -> dict:
    return records.provenance_header(a["run_id"], a["stage"], a["agent"],
                                     model=a.get("model", "claude"),
                                     sources=a.get("sources"), corpus_refs=a.get("corpus_refs"),
                                     matter=a.get("matter", ""), workspace=a.get("workspace"))


def _schema(props: dict, req: list[str]) -> dict:
    return {"type": "object", "properties": props, "required": req}


MATTER = {"type": "string", "description": "matter ref, colon-free (e.g. powell-builders)"}

TOOLS = [
    ("ironfleet_corpus_search",
     "Search this matter's citation-exact corpus (hybrid lexical+vector+citation join, "
     "optional local rerank) and return VERBATIM passages. The only sanctioned source of "
     "quoted text: drafts emit [E.n.S.n]-style references and quote only what this returns. "
     "Fail-closed: no matter bound -> empty envelope.", _schema({
         "matter": MATTER, "query": {"type": "string"},
         "k": {"type": "integer", "description": "passages to return (default 5)"},
         "rerank": {"type": "boolean", "description": "local cross-encoder rerank (default true)"}},
         ["matter", "query"]), t_corpus_search),
    ("ironfleet_statutory_demand",
     "Validate a statutory demand under s 289 Companies Act 1993 (NZ) and compute the "
     "s 241(4)(a) compliance deadline (>=15 working days; NZD 1,000 minimum).", _schema({
         "amount": {"type": ["number", "string"]}, "debtor_company": {"type": "string"},
         "creditor": {"type": "string"}, "debt_details": {"type": "string"},
         "service_date": {"type": "string", "description": "YYYY-MM-DD"},
         "compliance_period": {"type": "integer"}, "region": {"type": "string"},
         "jurisdiction": {"type": "string", "default": "nz"}}, ["amount", "debtor_company", "creditor", "debt_details"]),
     t_statutory_demand),
    ("ironfleet_without_prejudice",
     "Classify correspondence as WP / WPSATC / OPEN (Evidence Act 2006 s57) with "
     "injection detection. Run BEFORE quoting or forwarding settlement correspondence.", _schema({
         "content": {"type": "string"}, "subject_line": {"type": "string"},
         "trust_tier": {"type": "string", "description": "T0-T3 (default T1)"},
         "operator_override": {"type": "boolean"}}, ["content"]), t_without_prejudice),
    ("ironfleet_filing_deadline",
     "Compute a court/statutory deadline: working days from service, NZ weekends and "
     "public holidays excluded (NZ/AU/UK holiday data 2024-2030).", _schema({
         "service_date": {"type": "string", "description": "YYYY-MM-DD"},
         "days": {"type": "integer", "description": "working days in the statutory period"},
         "region": {"type": "string"}, "jurisdiction": {"type": "string", "default": "nz"}},
         ["service_date", "days"]), t_filing_deadline),
    ("ironfleet_ingest_docs",
     "Ingest documents into the matter corpus: parse -> structure-aware split -> local "
     "bge-m3 embeddings (Ollama, localhost) -> per-matter store. sha256 idempotent; "
     "scanned/no-text sources are recorded-and-skipped. PDFs need `pip install --user pypdf`.", _schema({
         "matter": MATTER, "path": {"type": "string", "description": "file or directory"}},
         ["matter", "path"]), t_ingest_docs),
    ("ironfleet_list_docs",
     "List a matter's ingested documents (name, words, chunks, when) and the chunk count.", _schema({
         "matter": MATTER}, ["matter"]), t_list_docs),
    ("ironfleet_begin_run",
     "Start a run record: creates runs/<date>-<id>/ with run.json + trace.jsonl. "
     "Call FIRST in every /process-case run; keep the returned run_id for log_event/finish_run.", _schema({
         "matter": MATTER, "prompt": {"type": "string"},
         "workspace": {"type": "string", "description": "matter workspace dir (runs/ lands there)"},
         "stages": {"type": "array", "items": {"type": "string"}}}, ["matter", "prompt"]),
     t_begin_run),
    ("ironfleet_log_event",
     "Append one event to the run's trace.jsonl: stage start/end, files written (path + "
     "sha256), guard blocks, assumptions, errors.", _schema({
         "run_id": {"type": "string"}, "event": {"type": "string"},
         "payload": {"type": "object"}, "matter": {"type": "string"},
         "workspace": {"type": "string"}}, ["run_id"]), t_log_event),
    ("ironfleet_finish_run",
     "Close a run: set status, list deliverables, write RECORD.md (the human report).", _schema({
         "run_id": {"type": "string"}, "status": {"type": "string"},
         "deliverables": {"type": "array", "items": {"type": "string"}},
         "summary": {"type": "string"}, "matter": {"type": "string"},
         "workspace": {"type": "string"}}, ["run_id"]), t_finish_run),
    ("ironfleet_provenance",
     "Return the provenance front-matter block (run id, stage, agent, date, source "
     "sha256s, corpus refs) to paste at the top of EVERY deliverable.", _schema({
         "run_id": {"type": "string"}, "stage": {"type": "string"}, "agent": {"type": "string"},
         "model": {"type": "string"}, "sources": {"type": "array", "items": {"type": "string"}},
         "corpus_refs": {"type": "array", "items": {"type": "string"}},
         "matter": {"type": "string"}, "workspace": {"type": "string"}},
         ["run_id", "stage", "agent"]), t_provenance),
]

HANDLERS = {name: fn for name, _d, _s, fn in TOOLS}
TOOL_DEFS = [{"name": n, "description": d, "inputSchema": s} for n, d, s, _f in TOOLS]


def dispatch(name: str, args: dict) -> dict:
    fn = HANDLERS.get(name)
    if fn is None:
        raise RuntimeError(f"unknown tool: {name}")
    return fn(args or {})


def main() -> None:
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            msg = json.loads(line)
        except json.JSONDecodeError:
            continue                                   # not JSON: ignore, keep serving
        if not isinstance(msg, dict) or "method" not in msg:
            continue
        rid = msg.get("id")
        method = msg["method"]
        if method == "initialize":
            result = {"protocolVersion": msg.get("params", {}).get(
                          "protocolVersion", "2025-06-18"),
                      "capabilities": {"tools": {}},
                      "serverInfo": {"name": "ironfleet", "version": VERSION}}
        elif method == "ping":
            result = {}
        elif method == "tools/list":
            result = {"tools": TOOL_DEFS}
        elif method == "tools/call":
            p = msg.get("params", {})
            try:
                out = dispatch(p.get("name", ""), p.get("arguments") or {})
                result = {"content": [{"type": "text",
                                       "text": json.dumps(out, ensure_ascii=False)}]}
            except Exception as ex:                    # noqa: BLE001 — loud to the model
                result = {"content": [{"type": "text", "text": f"{type(ex).__name__}: {ex}"}],
                          "isError": True}
        elif rid is None:
            continue                                   # notification: nothing to answer
        else:
            result = None
        if rid is not None:
            resp = {"jsonrpc": "2.0", "id": rid}
            if method in ("initialize", "ping", "tools/list", "tools/call"):
                resp["result"] = result
            else:
                resp["error"] = {"code": -32601, "message": f"unknown method {method}"}
            sys.stdout.write(json.dumps(resp, ensure_ascii=False) + "\n")
        sys.stdout.flush()


if __name__ == "__main__":
    main()
