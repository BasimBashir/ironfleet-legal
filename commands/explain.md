---
description: Walk the user through a finished run in plain English — the answer, passage by passage, every passage self-verified by the G1 corpus check
argument-hint: "<matter-ref> [workspace path, default matters/<matter-ref>]"
---

# /explain — the plain-English walkthrough

**This renders a run, it never analyses.** No new facts, no new legal reasoning, no
second opinion: the walkthrough is the run's own deliverables read aloud, with every
passage mechanically re-checked by `ironfleet_verify_document` (G1) before you show
it. If the run does not exist, stop — do not reconstruct an answer.

**Input:** $ARGUMENTS — the matter ref. Workspace defaults to `matters/<matter-ref>/`
under the current directory; pass a path to override.

## Run (mechanical — reads the run + corpus, writes nothing)

1. **Locate the run.** Open the workspace: `closing-summary.md` must exist (the run
   closed). If it does not, STOP and say so: "/explain renders a finished run — run
   /process-case first for <matter-ref>." Read `closing-summary.md` (the five-line
   answer), `advice-letter.md` and `citation-check.md` (stage 8's pasted envelopes).
2. **Re-verify (G1, fresh).** Call `ironfleet_verify_document` (matter, path) on
   `advice-letter.md` and `win-assessment.md` NOW — never trust the envelopes pasted
   in citation-check.md; re-runnability is the point. If a fresh envelope disagrees
   with a pasted one (the deliverable was edited after the run), say so in one loud
   line before anything else.
3. **Walk through the answer.** In plain English, in this order:
   - The direct answer, from closing-summary.md.
   - Each material point of the advice: WHY — the passage quoted verbatim from
     advice-letter.md, its `[E.n.S.n]` ref rendered as a clickable link to that
     line (`[E2.S1](advice-letter.md:14)`), the corpus source it verified against
     (the envelope's `found_in`), and its verdict badge (VERIFIED). The statute and
     the passage, named: "here is why the 2019 invoice was excluded."
   - **Freshness.** If the envelope carries `freshness` (W2), state it once: "these
     authorities are current as of <date>" — the sentence a court wants to see.
4. **Unverified passages render loudly, never smoothed over.** A passage whose
   verdict is NOT_IN_CORPUS, MISMATCH or PRIVILEGED appears in the walkthrough with
   that verdict and — if one was logged — the run's ruled-exception note naming ref,
   quote and ruling. A PRIVILEGED verdict is never softened (G3 house rule).
5. **MCP unavailable (DEGRADED):** if the server will not answer, say so once and
   render the walkthrough with `[UNVERIFIED — corpus check unavailable]` in place of
   verdicts. Never silently drop the corpus contract — degrade loudly.

**Reply inline — write no file.** The run's document set stays canonical; the
walkthrough lives in the conversation, linking the deliverables it renders.
