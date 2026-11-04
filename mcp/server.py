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
from harness.corpus import CorpusStore, bound_tier, ironfleet_corpus_search  # noqa: E402
from harness.module_e.kernel_tools import statutory_demand, without_prejudice  # noqa: E402
from harness.module_e.vendored.court_calendar import court_filing_deadline  # noqa: E402
from harness.paths import resolve_store_root              # noqa: E402
from harness.vectors import VectorStore                   # noqa: E402

# VERSION must move together with the version fields in .claude-plugin/plugin.json
# and .claude-plugin/marketplace.json — three hardcoded copies, no build step syncs
# them yet (that lands with W3's operator CLI).
VERSION = "0.3.2"


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
                    "(weekends + public holidays; NZ also 25 Dec-2 Jan per "
                    "Companies Act 1993 s 2 / PPSA s 16)"}


def t_ingest_docs(a: dict) -> dict:
    from harness.ingest_generic import extract_text
    from harness.corpus import DocRecord, chunk_text
    import hashlib
    store, root = _stores()
    matter = a["matter"]
    # G3: one tier stamps every doc this call ingests. Default order: the call's
    # trust_tier, then the operator's matter binding (matter.json, W3's bind-tier),
    # then T1 open.
    tier = a.get("trust_tier") or bound_tier(root, matter) or "T1"
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
        store.ingest(matter, DocRecord(f"doc-{sha[:12]}", text, f.name,
                                       trust_tier=tier),
                     vectors=vecs, model="bge-m3", provider="ollama-embed")
        report["ingested"].append(f.name)
        report["chunks"] += len(texts)
    return report


def t_list_docs(a: dict) -> dict:
    store, root = _stores()
    m = a["matter"]
    return {"matter": m, "docs": store.docs(m), "chunks": store.count(m),
            "store_root": str(root)}


def t_verify_document(a: dict) -> dict:
    """G1: mechanical, offline, re-runnable quote fidelity check over one deliverable."""
    from harness.verify import verify_document
    store, root = _stores()
    out = verify_document(a["matter"], a["path"], store=store)
    if not out.get("ok"):
        out["remedy"] = ("fix the flagged spans or mark them [NOT IN CORPUS] and "
                         "record a ruled exception; PRIVILEGED spans instead come out "
                         "of the draft (or the source is re-tiered as open) and never "
                         "close via the ruled-exception path; stage 9 may not close "
                         "on any of them")
    return out


def t_objection(a: dict) -> dict:
    """G5: the adversary's three failure modes, mechanically, before advice is drafted."""
    from harness.objection import objection
    store, _root = _stores()
    return objection(a["matter"], a["path"], run_id=a.get("run_id"),
                     workspace=a.get("workspace"), store=store)


def t_citator(a: dict) -> dict:
    """W3: citator-lite — which ingested judgments cite this authority (or the
    authorities a draft names), flagged later/same-or-earlier."""
    from harness.citator import citator
    store, _root = _stores()
    return citator(a["matter"], authority=a.get("authority"), path=a.get("path"),
                   store=store)


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


def t_disclosure(a: dict) -> dict:
    """G4: the 2026 AI-use certification block, rendered from the run ledger."""
    return records.disclosure_block(a["run_id"], matter=a.get("matter", ""),
                                    workspace=a.get("workspace"))


def _schema(props: dict, req: list[str]) -> dict:
    return {"type": "object", "properties": props, "required": req}


MATTER = {"type": "string", "description": "matter ref, colon-free (e.g. powell-builders)"}

TOOLS = [
    ("ironfleet_corpus_search",
     "Search this matter's citation-exact corpus (hybrid lexical+vector+citation join, "
     "optional local rerank) and return VERBATIM passages. The only sanctioned source of "
     "quoted text: drafts emit [E.n.S.n]-style references and quote only what this returns. "
     "Privileged-tier docs (T0/T2) stay readable in passages but never enter the quotable "
     "authorities list — do not quote text whose trust_tier is not open. "
     "Fail-closed: no matter bound -> empty envelope.", _schema({
         "matter": MATTER, "query": {"type": "string"},
         "k": {"type": "integer", "description": "passages to return (default 5)"},
         "rerank": {"type": "boolean", "description": "local cross-encoder rerank (default true)"},
         "min_tier": {"type": "string", "description": "openness floor for the quotable "
                     "authorities list (default T1)"}},
         ["matter", "query"]), t_corpus_search),
    ("ironfleet_statutory_demand",
     "Validate a statutory demand and compute its compliance deadline from the "
     "jurisdiction pack (NZ: 15 working days, s 289(2)(d); au/uk: 21 calendar days).", _schema({
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
         "matter": MATTER, "path": {"type": "string", "description": "file or directory"},
         "trust_tier": {"type": "string", "description": "stamp every ingested doc: "
                        "T0 privileged / T1 open (default) / T2 internal / T3 public"}},
         ["matter", "path"]), t_ingest_docs),
    ("ironfleet_list_docs",
     "List a matter's ingested documents (name, words, chunks, when) and the chunk count.", _schema({
         "matter": MATTER}, ["matter"]), t_list_docs),
    ("ironfleet_verify_document",
     "Ground-truth citation checker (the 0.2.0 headline): mechanically checks a "
     "deliverable against this matter's corpus — every double-quoted span and every "
     "[E.n.S.n] reference must be a byte substring of an ingested chunk of an open "
     "enough trust tier. Verdict per ref/quote: VERIFIED | PRIVILEGED | MISMATCH | "
     "NOT_IN_CORPUS. PRIVILEGED = the span lives only in privileged-tier (T0/T2) "
     "chunks: remove it from the draft. Offline, no LLM, re-runnable by anyone "
     "holding the corpus. Run it before closing a run; ok=false means it is not "
     "safe to deliver.", _schema({
         "matter": MATTER, "path": {"type": "string",
                                    "description": "deliverable file (absolute, or "
                                                   "relative to the store root)"}},
         ["matter", "path"]), t_verify_document),
    ("ironfleet_objection",
     "G5, the adversary's three failure modes as a mechanical pre-mortem over one "
     "draft: (a) a cited authority not in corpus, (b) a quoted span not in corpus, "
     "(c) a date/period not matching the kernel's computation for this run (reads the "
     "tool_result events stage 6 logs). When the run logged an evidence table "
     "(log_event event `evidence`, payload {table: {ref: sentence}}), every [E.n.S.n] "
     "ref is pinned to its sentence: a ref quoting something else is a MISMATCH. Run "
     "it on the attack brief before advice is drafted, and on the deadline-bearing "
     "deliverables at verify. ok=false means objections stand.", _schema({
         "matter": MATTER, "path": {"type": "string",
                                    "description": "draft file (absolute, or relative "
                                                   "to the store root)"},
         "run_id": {"type": "string", "description": "the run whose kernel "
                    "computations and evidence table to check against"},
         "workspace": {"type": "string", "description": "matter workspace dir "
                       "(runs/ lands there)"}},
         ["matter", "path"]), t_objection),
    ("ironfleet_citator",
     "W3 citator-lite: for one authority — or every authority a draft names (path "
     "mode) — list the later judgments in this matter's ingested corpus that cite "
     "it (the cites join; each citing judgment flagged by its own neutral-citation "
     "year). Mechanically closes the 'no longer good law' half of the Stanford "
     "finding: the tool surfaces citing judgments, whether one overruled or "
     "distinguished the authority is a human reading call. Run it at verify on any "
     "deliverable that cites case law, against the law-judgments matter.", _schema({
         "matter": MATTER,
         "authority": {"type": "string", "description": "one authority: 'X v Y "
                       "[year] court no' or 'Act year, s N' (name forms must match "
                       "the corpus exactly — abbreviations never bridge)"},
         "path": {"type": "string", "description": "draft file — check every "
                  "authority it names (absolute, or relative to the store root)"}},
         ["matter"]), t_citator),
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
    ("ironfleet_disclosure",
     "G4: render the 2026 AI-use certification block for a run, mechanically from "
     "run.json + trace.jsonl: stages (only those with a stage_end event), tools "
     "evidenced by tool_result events, verify_document verdicts, corpus refs, the "
     "certification sentence and a signature line. Embed the returned `block` in "
     "every court filing deliverable.", _schema({
         "run_id": {"type": "string"}, "matter": MATTER,
         "workspace": {"type": "string", "description": "matter workspace dir "
                       "(runs/ lands there)"}},
         ["run_id"]), t_disclosure),
]

HANDLERS = {name: fn for name, _d, _s, fn in TOOLS}
TOOL_DEFS = [{"name": n, "description": d, "inputSchema": s} for n, d, s, _f in TOOLS]


def dispatch(name: str, args: dict) -> dict:
    fn = HANDLERS.get(name)
    if fn is None:
        raise RuntimeError(f"unknown tool: {name}")
    return fn(args or {})


# --------------------------------------------------------------- resources (L2)

_RUN_FILES = (("run.json", "application/json"), ("trace.jsonl", "text/plain"),
              ("RECORD.md", "text/markdown"))


def list_resources() -> list[dict]:
    """L2: what a non-Claude MCP client can browse — every ingested corpus doc
    (every matter) and every run's ledger files (found through the runs/.index
    pointers begin_run writes). Mechanical enumeration, no arguments, read-only."""
    store, root = _stores()
    out: list[dict] = []
    for m in store.matters():
        for d in store.docs(m):
            out.append({"uri": f"ironfleet://corpus/{m}/{d['doc_id']}",
                        "name": f"{m}/{d['name']}",
                        "description": f"corpus doc — {d['words']} words, "
                                       f"{d['chunks']} chunks, tier {d['trust_tier']}",
                        "mimeType": "application/json"})
    idx = Path(root) / "runs" / ".index"
    if idx.is_dir():
        for p in sorted(idx.glob("*.json")):
            try:
                d = Path(json.loads(p.read_text(encoding="utf-8"))["run_dir"])
            except Exception:                      # noqa: BLE001 — skip dead pointers
                continue
            if not (d / "run.json").exists():
                continue
            for fname, mime in _RUN_FILES:
                if (d / fname).exists():
                    out.append({"uri": f"ironfleet://runs/{p.stem}/{fname}",
                                "name": f"{p.stem}/{fname}",
                                "description": "run ledger file", "mimeType": mime})
    return out


def read_resource(uri: str) -> list[dict]:
    """L2: one resource body. corpus/<matter>/<doc_id> -> the doc's row + full text;
    runs/<run_id>/<file> -> the ledger file (name allowlist, read-only)."""
    if uri.startswith("ironfleet://corpus/"):
        matter, _, doc_id = uri[len("ironfleet://corpus/"):].partition("/")
        if not matter or not doc_id:
            raise RuntimeError(f"malformed corpus uri: {uri}")
        store, _root = _stores()
        doc = store.doc_text(matter, doc_id)
        if doc is None:
            raise RuntimeError(f"no doc {doc_id} in matter {matter}")
        return [{"uri": uri, "mimeType": "application/json",
                 "text": json.dumps(doc, ensure_ascii=False)}]
    if uri.startswith("ironfleet://runs/"):
        rid, _, fname = uri[len("ironfleet://runs/"):].partition("/")
        mime = {f: m for f, m in _RUN_FILES}.get(fname)
        if mime is None:                       # also bars path separators: not a key
            raise RuntimeError(f"not a run ledger file: {fname!r}")
        d = records.run_dir_by_id(rid)
        return [{"uri": uri, "mimeType": mime,
                 "text": (d / fname).read_text(encoding="utf-8")}]
    raise RuntimeError(f"unknown resource scheme: {uri}")


def main() -> None:
    # The protocol is UTF-8 JSON; a Windows host that leaves console codepages alone
    # (cp1252) would crash the write of any passage holding a non-cp1252 character.
    # Some hosts hand non-reconfigurable stream wrappers — guard, never crash on line 1.
    if hasattr(sys.stdin, "reconfigure"):
        sys.stdin.reconfigure(encoding="utf-8", errors="replace")
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
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
        err = None
        if method == "initialize":
            result = {"protocolVersion": msg.get("params", {}).get(
                          "protocolVersion", "2025-06-18"),
                      "capabilities": {"tools": {}, "resources": {}},
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
        elif method == "resources/list":               # L2: browse corpus + run ledger
            result = {"resources": list_resources()}
        elif method == "resources/read":
            p = msg.get("params", {})
            try:
                result = {"contents": read_resource(p.get("uri", ""))}
            except Exception as ex:                    # noqa: BLE001 — JSON-RPC error, MCP spec
                result, err = None, {"code": -32002,
                                     "message": f"Resource not found: {ex}"}
        elif rid is None:
            continue                                   # notification: nothing to answer
        else:
            result = None
        if rid is not None:
            resp = {"jsonrpc": "2.0", "id": rid}
            if err is not None:
                resp["error"] = err
            elif method in ("initialize", "ping", "tools/list", "tools/call",
                            "resources/list", "resources/read"):
                resp["result"] = result
            else:
                resp["error"] = {"code": -32601, "message": f"unknown method {method}"}
            sys.stdout.write(json.dumps(resp, ensure_ascii=False) + "\n")
        sys.stdout.flush()


if __name__ == "__main__":
    main()
