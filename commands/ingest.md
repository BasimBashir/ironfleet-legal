---
description: Ingest documents into a matter's local citation-exact corpus (RAG)
argument-hint: "<path to files or folder> [matter: <ref>]"
---

# IronFleet ingest

Ingest `$ARGUMENTS` (a file or a folder) into the matter corpus.

1. **Matter ref** — take it from the arguments (`matter: <ref>`); if absent, derive a
   colon-free one from the folder name and say so.
2. **Call** MCP `ironfleet_ingest_docs` (matter, path). PDFs require pypdf; if the
   result reports parse failures, print the exact fix: `pip install --user pypdf`.
3. **Report** — ingested files, chunk counts, and anything skipped (scanned/no-text
   sources are recorded-and-skipped, not silently embedded). Then call
   `ironfleet_list_docs` and show the matter's running totals.
4. **If the MCP server is down (DEGRADED MODE):** say so in one line — documents cannot
   enter the corpus right now, and every later draft will carry
   `[NO CORPUS STORE — attach documents directly]` until it is back. Do not pretend.

Re-ingesting an unchanged file is free (sha256 resume). To refresh a CHANGED document,
delete is coming with R-CL2 CRUD; for now, changed content re-ingests as a new doc —
name files by version (`contract-v2.pdf`) to keep the corpus clean.
