---
name: nz-memory-systems
description: Use this skill whenever @STRAT or @HUNTER needs to persist knowledge across a long-running NZ legal matter, when designing how case facts should be stored and retrieved across agent sessions, when a matter has accumulated enough history that retrieval quality is degrading, or when @WARGAMER needs to reason over the full case history without reloading all source documents. Also invoke when setting up a new matter in Iron Fleet and deciding which memory architecture to use. Adapted from muratcankoylan/Agent-Skills-for-Context-Engineering memory-systems — Iron Fleet contextualised for NZ legal matter lifecycles, Cognee GraphRAG, privilege-safe memory, and multi-agent coordination.
license: MIT
compatibility: Claude Code, Claude Desktop, Claude Cowork. Corpus tools need local Python 3.10+ and Ollama.
metadata:
  mode: GLASS
  version: 1.0.0
  source_kernel: nz_memory_systems.py
  function: run
  permissions: []
  trust_tier_required: 1
  adapted_from: muratcankoylan/Agent-Skills-for-Context-Engineering
---


# nz-memory-systems

## Purpose
Guides memory architecture design for Iron Fleet agent sessions. Adapted
from muratcankoylan/Agent-Skills-for-Context-Engineering `memory-systems`.

Iron Fleet matters run for months with multiple agents operating over
the same case data. Without a deliberate memory architecture, agents
re-fetch the same documents, lose track of prior decisions, and
contradict earlier strategy conclusions.

## Memory Architecture Options

### Option 1 — In-Context Scratchpad (short matters)
Store working state directly in the agent's context window using
structured sections. Suitable for matters < 20 documents, < 10 turns.
```
## Working Memory — [matter_ref]
### Facts: [bullet list with chunk_ids]
### Strategy: [current position]
### Open Questions: [pending items]
```

**Iron Fleet constraint:** Scratchpad must include `wp_status` for any
correspondence referenced. Never scratchpad-store WP content inline —
store the chunk_id reference only.

### Option 2 — CaseState Persistence (standard matters)
Use Iron Fleet's CaseState for cross-session persistence. Per Annex §3.6,
agents never write to CaseState directly — they return state in output
and the orchestrator writes it.
```python
# Agent returns state to persist
return {
    "result": {...},
    "state_to_persist": {
        "matter_ref": "OA-2024-001",
        "key_facts": [...],
        "strategy_position": "...",
        "privilege_log": [{"chunk_id": "...", "wp_status": "WP"}]
    }
}
# Orchestrator writes state_to_persist to CaseState
# Next invocation receives updated CaseState as input
```

### Option 3 — Cognee GraphRAG (complex matters)
Use the existing Cognee Neo4j knowledge graph for matters with:
- > 50 documents
- Multi-party disputes
- Cross-matter entity tracking (same counterparty across matters)

**Entity types for NZ legal matters:**
- `Party` — plaintiff, defendant, counsel, judge
- `Document` — affidavit, correspondence, judgment
- `Issue` — legal issue with statute/case citation
- `DeadlineEvent` — filing dates, hearing dates
- `PrivilegeRecord` — wp_status per correspondence item

**Graph relationships:**
```
Party --[FILED]--> Document
Document --[EXHIBITS]--> Document
Issue --[GOVERNED_BY]--> Statute
PrivilegeRecord --[CLASSIFIES]--> Document
DeadlineEvent --[APPLIES_TO]--> Issue
```

### Option 4 — Vector RAG (judgment retrieval)
Use PGVector for semantic search over the judgment corpus. Already
configured in Iron Fleet. Best for:
- Finding relevant NZ case law for a legal issue
- Retrieving similar statutory demand outcomes (SIM-A-20)
- Cross-matter pattern matching

## Memory Selection Guide

| Matter Type | Documents | Duration | Recommended |
|---|---|---|---|
| Single transaction | < 20 | < 1 week | Scratchpad |
| Standard litigation | 20–100 | 1–6 months | CaseState |
| Complex multi-party | 100+ | > 6 months | Cognee GraphRAG |
| Case law research | Any | Any | Vector RAG |

## Privilege-Safe Memory Rules

1. **Never store WP content in scratchpad inline** — store chunk_id only
2. **CaseState privilege_log** — every WP/WPSATC item must have an entry
3. **GraphRAG PrivilegeRecord nodes** — wp_status is a required property
4. **Vector RAG** — do not embed WP correspondence text; embed summaries
   with privilege classification preserved as metadata
5. **Memory exports** — run through `privilege_protection.scan_for_privilege()`
   before any external export

## Confidence Signals

| Signal | Weight | How scored |
|---|---|---|
| `matter_complexity_assessed` | 0.40 | 1.0 if doc/duration assessed; 0.5 if estimated |
| `privilege_safe_design` | 0.35 | 1.0 if privilege rules applied; 0.0 if overlooked |
| `casestate_pattern_correct` | 0.25 | 1.0 if Annex §3.6 pattern followed; 0.0 if direct write |

## Ambiguity Handling

If matter complexity cannot be assessed, default to CaseState —
it is the safest option that works for all matter sizes.

If privilege classification is uncertain for any stored item,
output `[PRIVILEGE-CLASSIFICATION-UNCERTAIN — MANUAL REVIEW]` and halt.

Never store WP content in Vector RAG embeddings — the embedding
model is external and WP text must not leave the local environment.

## Output Schema
```json
{
  "status": "SUCCESS | FLAGGED",
  "result": {
    "recommended_architecture": "scratchpad | casestate | graphrag | vector_rag",
    "rationale": "Why this architecture was selected",
    "privilege_safe": true,
    "casestate_pattern_correct": true,
    "entity_types": ["Party", "Document", "Issue"],
    "graph_relationships": ["Party --[FILED]--> Document"],
    "setup_steps": ["Step 1", "Step 2"]
  },
  "confidence": 0.88,
  "flags": [],
  "trust_tier": "T1"
}
```