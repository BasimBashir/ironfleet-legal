---
name: nz-context-compression
description: Use this skill whenever an Iron Fleet agent session approaches context limits, when @HUNTER is processing large judgment sets, when @STRAT is reasoning over a full case history, or when @SUMMARISER needs to compress a large document bundle before summarising. Invoke when context utilisation exceeds 70%, when tool outputs are verbose and consuming excessive tokens, or when a long-running matter session shows signs of context degradation. Adapted from muratcankoylan/Agent-Skills-for-Context-Engineering context-compression — Iron Fleet contextualised for NZ legal matter lifecycles, privilege-safe compression, and multi-agent orchestration.
license: MIT
compatibility: Claude Code, Claude Desktop, Claude Cowork. Corpus tools need local Python 3.10+ and Ollama.
metadata:
  mode: GLASS
  version: 1.0.0
  source_kernel: nz_context_compression.py
  function: run
  permissions: []
  trust_tier_required: 1
  adapted_from: muratcankoylan/Agent-Skills-for-Context-Engineering
---


# nz-context-compression

## Purpose
Guides context compression for Iron Fleet agent sessions. Adapted from
muratcankoylan/Agent-Skills-for-Context-Engineering `context-compression`.

Iron Fleet matters run for months. @STRAT, @HUNTER, and @WARGAMER
accumulate large context windows across judgment sets, correspondence
bundles, and strategy sessions. Without compression, agents exhibit
the "lost-in-the-middle" phenomenon — critical case facts buried in
long context receive less attention than recent inputs.

**Iron Fleet-specific compression rules:**
1. **Privilege-safe compression** — never compress WP or WPSATC
   correspondence into summaries that lose the privilege classification.
   The `wp_status` field must be preserved in any compressed representation.
2. **Genesis Hash integrity** — chunk IDs and parent references must be
   preserved in compressed output. Never merge chunks with different
   trust tiers into a single compressed chunk.
3. **Citation preservation** — @CITATION depends on exact page positions.
   Compress prose summaries but never compress the `page_map` output
   from BN-05 — it is already structured and compact.
4. **Optimize tokens-per-task** — the correct metric is not
   tokens-per-request but tokens-per-task. Aggressive compression that
   loses case facts causes re-fetching which costs more overall.

## When to Trigger Compression

Trigger when any of the following:
- Context utilisation > 70%
- Tool output > 10,000 tokens in a single response
- Agent has processed > 20 documents in a session
- @STRAT session exceeds 50 turns
- Same case facts are being re-fetched (sign of lost context)

## Compression Strategies

### Strategy 1 — Anchored Iterative Summarisation (preferred)
Maintain a structured persistent summary with explicit sections:
```
## Case Summary — [matter_ref] — [date]
### Session Intent
[What this agent session is trying to accomplish]
### Key Facts Established
[Material facts with chunk_id references — never lose these]
### WP/Privilege Status
[wp_status of key correspondence — NEVER compress away]
### Legal Issues Identified
[Issues with statute/case citations preserved]
### Decisions Made
[Agent decisions with rationale]
### Next Steps
[Pending actions]
### Artifact Trail
[Files modified, chunks created, tools called — list with IDs]
```

When compression triggers, summarise only the newly-truncated span
and merge with the existing summary. Structure forces preservation.

### Strategy 2 — Observation Masking
Replace verbose tool outputs with compact references once processed:
```python
# Instead of keeping full pdfplumber extraction in context:
# BEFORE (2000 tokens): {"pages": [{"text": "...full text...", ...}]}
# AFTER (20 tokens): {"ref": "chunk_ff793ee05c07", "pages": 45, "status": "extracted"}
```

Apply when: tool output has been processed and its conclusions captured
in the summary. Never mask outputs that haven't been summarised yet.

### Strategy 3 — Context Partitioning
Split work across sub-agents when single window insufficient:
```
@HUNTER → retrieves relevant chunks → passes structured refs to @STRAT
@STRAT  → reasons over refs only → does not load full chunk text
@WARGAMER → receives @STRAT conclusions → does not re-read source docs
```

Reserve for tasks where context > 60% of window limit. Coordination
overhead is real — partitioning has a cost.

## Compression Anti-Patterns (Iron Fleet specific)

| Anti-Pattern | Risk | Correct Approach |
|---|---|---|
| Compress `wp_status` away | Privilege violation — irreversible | Always preserve in structured summary |
| Merge chunks across trust tiers | Genesis Hash corruption | Keep trust tier metadata separate |
| Compress `page_map` from BN-05 | Breaks @CITATION positioning | Never compress — already compact |
| Full regeneration summary | Loses details across iterations | Use anchored iterative summarisation |
| Compress before processing | Loses information before it's used | Process first, then mask |
| Summary without artifact trail | Can't audit what agent did | Always include artifact trail section |

## Confidence Signals

| Signal | Weight | How scored |
|---|---|---|
| `compression_needed` | 0.50 | 1.0 if context > 70%; 0.5 if 50-70%; 0.0 if < 50% |
| `privilege_safe` | 0.30 | 1.0 if wp_status preserved; 0.0 if at risk |
| `artifact_trail_intact` | 0.20 | 1.0 if chunk_ids preserved; 0.0 if lost |

## Ambiguity Handling

If context utilisation cannot be estimated, assume compression is needed
and apply anchored iterative summarisation conservatively.

If wp_status of any correspondence is uncertain after compression,
output `[WP-STATUS-LOST-IN-COMPRESSION — MANUAL REVIEW]` and halt.

Never compress if compression would drop the artifact trail below
the point where @AUDITOR can reconstruct the agent's actions.

## Output Schema
```json
{
  "status": "SUCCESS | FLAGGED",
  "result": {
    "strategy": "anchored_iterative | observation_masking | partitioning",
    "context_utilisation_pct": 75,
    "tokens_before": 45000,
    "tokens_after_estimate": 8000,
    "compression_ratio": 0.82,
    "privilege_safe": true,
    "artifact_trail_preserved": true,
    "compressed_summary": "Structured summary text",
    "masked_refs": ["chunk_ff793ee05c07", "chunk_abc123"]
  },
  "confidence": 0.88,
  "flags": [],
  "trust_tier": "T1"
}
```