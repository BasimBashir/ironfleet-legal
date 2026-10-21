# src/harness/ingest_generic.py
"""R1: the GENERAL ingestion core — any new source set is manifest ROWS, never code.

Added 2026-10-14 on the user's direction ("make it future-ingestion-proof"): the two
task-specific ingesters (judgment PDFs, statute provisions) collapsed into one path
driven by content detection and manifest rows.

Row shape (a sources-spec YAML `sources:` list, or dicts in code):
  path: file-or-directory        (pdf | txt | md)
  kind: auto | statute | prose   (auto detects from content; default auto)
  act:  <name>                   (statute rows; defaults to the filename)
  licence: <string>              (REQUIRED for statute rows — fail-closed)
  source_url: <url>              (REQUIRED for statute rows)
  retrieved: <date/notes>        (REQUIRED for statute rows)

Statute detection: a text carrying a section-heading skeleton (>=5 bare-number headings
in its first 4000 lines) is a statute and is parsed at PROVISION level (one DocRecord
per section — the COLIEE/RefWalk shape, the measured fix for the 39% STATUTE-ABSENT
needle class). Everything else goes through the structure-aware judgment splitter.
"""
from __future__ import annotations

import hashlib
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

from harness.corpus import CorpusStore, DocRecord, chunk_text

_STATUTE_SECTION = re.compile(r"^(?P<num>\d{1,3}[A-Z]{0,2})\s*(?P<title>[A-Z][^|\n]{0,120})?\s*$")


def parse_provisions(act_name: str, text: str) -> list[DocRecord]:
    """Statute structure -> one DocRecord per section. Handles bare-number headings
    ("297") and number+title ("16 Meaning of..."). The DocRecord text opens in the
    needle surface form ('Act Year, s 297 ...') so a pin hits its own section."""
    sections: list[tuple[str, list[str]]] = []
    cur_num, cur_body = "", []
    for ln in text.splitlines():
        m = _STATUTE_SECTION.match(ln)
        if m:
            if cur_num:
                sections.append((cur_num, cur_body))
            cur_num = f"{m['num']} {(m['title'] or '').strip()}".strip()
            cur_body = []
        elif cur_num:
            cur_body.append(ln)
        else:
            cur_body.append(ln)
    if cur_num:
        sections.append((cur_num, cur_body))
    out: list[DocRecord] = []
    for num, body in sections:
        body_text = "\n".join(body).strip()
        if len(body_text.split()) < 8:                 # "(Repealed)" stubs, page furniture
            continue
        full = f"{act_name}, s {num}\n\n{body_text}"
        sha = hashlib.sha256(full.encode("utf-8")).hexdigest()[:12]
        out.append(DocRecord(doc_id=f"statute-{sha}", text=full,
                             source_name=f"{act_name}, s {num}"))
    return out


_PCO_FURNITURE = re.compile(r"Version as at|Reprint as at|^\s*\d{4} No \d+", re.MULTILINE)


def detect_kind(text: str) -> str:
    """'statute' iff the text has a section-heading skeleton AND PCO-export furniture
    ('Version as at' / '1993 No 105') that judgments never carry. The furniture clause
    exists because extracted judgment PDFs spray standalone page-number lines that
    match a section-heading regex (measured live: 25 judgments refused as licence-less
    'statutes' before this clause)."""
    if not _PCO_FURNITURE.search(text[:8000]):
        return "prose"
    hits = sum(1 for ln in text.splitlines()[:4000] if _STATUTE_SECTION.match(ln))
    return "statute" if hits >= 5 else "prose"


def licence_check(row: dict) -> str | None:
    """Fail-closed: a refusal reason, or None. Required fields for statute rows."""
    for field in ("licence", "source_url", "retrieved"):
        if not row.get(field):
            return f"manifest row missing {field!r}"
    p = row.get("path") or row.get("file")
    if p and not Path(p).exists():
        return f"source file {p!r} not found"
    return None


def _files_for(rows: list[dict]) -> list[tuple[Path, dict]]:
    out: list[tuple[Path, dict]] = []
    for r in rows:
        p = Path(r["path"])
        if p.is_dir():
            for pat in ("**/*.pdf", "**/*.txt", "**/*.md"):
                for f in sorted(p.glob(pat)):
                    out.append((f, r))
        else:
            out.append((p, r))
    return out


PARSE_TIMEOUT_S = 180              # a source that hangs parse is recorded-and-skipped

_PARSE_CMD = ("import sys; from harness.ingest_generic import _parse_chain; "
              "_parse_chain(sys.argv[1], sys.argv[2])")


def _parse_chain(source_str: str, out_str: str) -> None:
    """The FULL parser chain: MarkItDown (format reach), then pypdf for PDFs, then raw
    text. Writes the text file; a total chain failure raises (never a silent empty doc)."""
    text = ""
    try:
        from markitdown import MarkItDown
        text = MarkItDown().convert(source_str).text_content or ""
    except Exception:                                  # noqa: BLE001 — fall through the chain
        text = ""
    if not text.strip():
        p = Path(source_str)
        if p.suffix.lower() == ".pdf":
            from pypdf import PdfReader
            reader = PdfReader(str(p))
            text = "\n\n".join((page.extract_text() or "") for page in reader.pages)
        else:
            text = p.read_text(encoding="utf-8")
    Path(out_str).write_text(text, encoding="utf-8")


def extract_text(source: Path, timeout: int = PARSE_TIMEOUT_S) -> str:
    """Format reach via a parser CHAIN, not per-format code (user direction 2026-10-14:
    "use existing advanced RAG modules... they don't need custom upload scripts"). The
    chain runs in a KILLABLE SUBPROCESS (file transport, no pipes): parsers have no
    internal timeouts and a pathological file can burn a core forever (observed live
    2026-10-14 — pypdf, then MarkItDown, each pinned a core 10+ minutes on judgment
    PDFs; multiprocessing-spawn workers additionally hang on this box). On timeout the
    caller records-and-skips the source (the D7 contract), never silently embedding an
    empty doc."""
    import subprocess
    import tempfile
    with tempfile.TemporaryDirectory(prefix="r1parse_") as td:
        out = Path(td) / "text.txt"
        try:
            proc = subprocess.run([sys.executable, "-c", _PARSE_CMD,
                                   str(source), str(out)],
                                  capture_output=True, text=True, timeout=timeout,
                                  cwd=str(Path(__file__).resolve().parents[2]))
        except subprocess.TimeoutExpired:
            raise TimeoutError(
                f"parse exceeded {timeout}s (killed): {source.name}") from None
        if proc.returncode != 0 or not out.exists():
            raise RuntimeError(f"parse failed: {source.name}: {proc.stderr[-300:]}")
        return out.read_text(encoding="utf-8")


def ingest_any(matter_ref: str, rows: list[dict], store: CorpusStore, embed_fn,
               model: str = "bge-m3:567m", provider: str = "ollama-embed",
               min_words: int = 200) -> dict:
    """Ingest any mix of sources per the rows. Resume (sha256), recorded-skip
    (scanned/parse-error), statute licence gate, 1:1 vector alignment, throughput in
    the report. THE front door: a new corpus set is data, not code."""
    report: dict = {"ingested": [], "skipped": [], "skipped_by_resume": [],
                    "refused": [], "chunks": 0, "provisions": 0, "prose_docs": 0}
    files = _files_for(rows)
    t0 = time.perf_counter()
    for src, row in files:
        try:
            text = extract_text(src)
        except Exception as ex:                        # noqa: BLE001 — recorded, keep going
            report["skipped"].append(f"{src.name}: parse error {ex}")
            continue
        if len(text.split()) < min_words:
            report["skipped"].append(
                f"{src.name}: {len(text.split())} words (<{min_words}, scanned?)")
            continue
        kind = row.get("kind", "auto")
        if kind == "auto":
            kind = detect_kind(text)
        sha = hashlib.sha256(text.encode("utf-8")).hexdigest()
        if store.has_doc(matter_ref, sha):
            report["skipped_by_resume"].append(src.name)
            continue
        if kind == "statute":
            reason = licence_check(row)
            if reason:
                report["refused"].append(f"{src.name}: {reason}")
                continue
            docs = parse_provisions(row.get("act") or src.stem, text)
            report["provisions"] += len(docs)
        else:
            docs = [DocRecord(doc_id=f"doc-{sha[:12]}", text=text, source_name=src.name)]
            report["prose_docs"] += 1
        for doc in docs:
            # resume at DOC granularity, not file granularity: one statute file fans
            # out to per-provision docs whose shas are what the store holds — the old
            # file-sha check never matched for statutes, so every re-run silently
            # re-embedded all provisions (the measured source of the 2.6x duplicate
            # embeddings; the "resume proven live" observation was 6 prose docs where
            # file sha == doc sha)
            if store.has_doc(matter_ref,
                             hashlib.sha256(doc.text.encode("utf-8")).hexdigest()):
                report["resumed_docs"] = report.get("resumed_docs", 0) + 1
                continue
            texts = chunk_text(doc.doc_id, doc.text)
            vectors: list[list[float]] = []
            for i in range(0, len(texts), 64):
                vectors.extend(embed_fn(texts[i:i + 64]))
            store.ingest(matter_ref, doc, vectors=vectors, model=model, provider=provider)
            report["chunks"] += len(texts)
        report["ingested"].append(src.name)
    report["wall_s"] = round(time.perf_counter() - t0, 1)
    report["chunks_per_s"] = round(report["chunks"] / max(report["wall_s"], 1e-9), 1)
    return report


def load_spec(path: Path) -> list[dict]:
    """Read a sources-spec YAML ({sources: [...]}; empty/absent list -> [])."""
    import yaml
    doc = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    return doc.get("sources", []) if isinstance(doc, dict) else []
