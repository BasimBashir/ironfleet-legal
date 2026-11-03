---
description: Ingest operator-supplied law files (statutes, judgments) into the corpus with a freshness report — never fetches, the operator is the source
argument-hint: "<folder of downloaded law files> [matter: law|law-judgments]"
---

# /sync-law — operator-supplied law corpus

**The source is the OPERATOR, never a robot.** legislation.govt.nz bot-gates
automation, and NZLII's usage policy bars AI/embedding use outright (rulings
2026-10-30; operator-supplied path confirmed 2026-11-03): this command NEVER
fetches. The user downloads the statute text or judgment copies themselves, in
their own browser, into a folder — then runs this command on that folder.
**NZLII is never a source, even manually downloaded**: creating embeddings of its
content breaches its usage policy no matter who downloaded the files.

**Input:** $ARGUMENTS — the folder of downloaded files. Matter defaults to `law`
(statutes); pass `matter: law-judgments` for judgment copies — that is the matter
`ironfleet_citator` reads (W3).

## Run (mechanical — reuse the existing ingest path, no second pipeline)

1. **Baseline.** `ironfleet_list_docs` (matter) — note each doc's `doc_id`,
   `source_name`, and `ts`.
2. **Ingest.** `ironfleet_ingest_docs` (matter, paths = the folder's files).
   Re-ingesting a `doc_id` replaces its rows and refreshes `ts`; the corpus keeps
   each text's `sha256`, so identical re-downloads cost nothing but a timestamp.
3. **Report** per file: NEW (not in the baseline) or REFRESHED (was already
   present). State the counts in one line each.
4. **Freshness.** `ironfleet_list_docs` again and state the newest `ts` as the
   matter's currency date — "the `law` matter is current as of <ts>". From now
   on, every `ironfleet_verify_document` envelope on this matter carries
   `freshness` (the newest ingest time among the chunks that decided a VERIFIED
   verdict), so a deliverable can cite "this authority is current as of <date>"
   — the sentence a court wants to see.
5. **Tier.** Public law text: run `python mcp/harness/cli.py bind-tier law T3`
   (or leave the T1 default) so every future ingest of this matter defaults
   open, and `ironfleet_citator`/`ironfleet_verify_document` treat it as
   quotable.

**Licence note (honest):** legislation.govt.nz's copyright page was never
machine-readable from this box (bot-gated). The user reads the copyright terms
when they download and confirms reuse-for-embedding is permitted (expected CC BY
4.0 for NZ legislation — an ASSUMPTION until the page is actually read). Record
what the page says, in the matter's fact-questions, on first download.
