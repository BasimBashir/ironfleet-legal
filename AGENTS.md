# IronFleet Legal — how to drive this kit in any harness

You have the IronFleet Legal kit: a NZ paralegal with a local, citation-exact corpus.

- **Tools** — the `ironfleet` MCP server (25 `ironfleet_*` tools). Mechanical only:
  corpus search, quote verifier, deadline and statutory-demand kernels, run ledger,
  case dossier, moot gate. Quote ONLY text `ironfleet_corpus_search` returns.
- **Commands** — 11 workflows (`process-case`, `ingest`, `doctor`, `sync-law`,
  `explain`, `debrief`, `case-status`, `next-actions`, `moot`, `hearing-pack`,
  `mock-hearing`). Your harness shows them as slash commands, prompt templates, or
  the MCP prompts of the `ironfleet` server. If none of those is visible, call
  `ironfleet_command` (name, arguments = the user's ask) and follow what it returns.
- **Stage agents** — 19 briefs (ingestor, hunter, strategist, adversary, evaluator,
  clerk, citation, auditor, case-manager, …). Dispatch them with your harness's
  subagents; `ironfleet_agent_brief` returns any brief verbatim. No subagents at
  all: run the stage yourself from the brief and log an `exception` event saying so.
- **Skills** — 27 Agent Skills under `skills/` (doctor first, on any new machine).
- **Never mark a document `status: final` without its `moot-gate: PASSED <run_id>`
  line.** Where the harness runs the plugin's pre-write hook this is enforced; where
  it does not, you enforce it.
- Setup per harness: docs/FRESH-OS-SETUP.md. Not legal advice — a qualified NZ lawyer
  reviews everything before filing.
