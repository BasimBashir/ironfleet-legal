---
name: nz-recursive-decomposition
description: Use this skill whenever @HUNTER needs to process more than 20 documents, when @STRAT is reasoning over a full NZ case history that exceeds context limits, when @AUDITOR needs to cross-validate outputs across large discovery sets, or when @SUMMARISER needs to produce two-level summaries of large document bundles. Invoke automatically when estimated token count exceeds 40k or when document count exceeds 20. Uses filter → narrow → deep-analyse cycles to avoid context overflow. Adapted from recursive-decomposition skill — Iron Fleet contextualised for NZ High Court judgment sets, SIM-A-20 corpus processing, and GLASS-tier pre-filtering before IRON-tier reasoning.
license: MIT
compatibility: Claude Code, Claude Desktop, Claude Cowork. Corpus tools need local Python 3.10+ and Ollama.
metadata:
  mode: GLASS
  version: 1.0.0
  source_kernel: nz_recursive_decomposition.py
  function: run
  permissions: []
  trust_tier_required: 0
---


# nz-recursive-decomposition

## Purpose
Long-context agent reasoning for Iron Fleet. Teaches @HUNTER, @STRAT,
@AUDITOR, and @SUMMARISER to handle 100+ files and 50k+ token inputs
through filter → narrow → deep-analyse cycles.

**Cost optimisation:** GLASS-tier pre-filtering before IRON-tier Opus
reasoning. Do not load all 50 judgments into Opus — filter first, then
deep-analyse only the relevant 3-5.

## When to Invoke Automatically

- Document count > 20
- Estimated tokens > 40,000
- @HUNTER processing full SIM-A-20 judgment corpus
- @STRAT reasoning over multi-matter case history
- @AUDITOR cross-validating 100+ discovery documents
- @SUMMARISER producing two-level summaries of large bundles

## Decomposition Cycle
```
FILTER → NARROW → DEEP-ANALYSE
```

### Phase 1 — FILTER (GLASS tier)
Broad pass over all documents. Eliminate irrelevant documents quickly.
```python
# Filter criteria for NZ legal corpus
filter_criteria = {
    "jurisdiction": "NZ",
    "court": ["NZHC", "NZCA", "NZSC"],
    "date_range": matter_date_range,
    "issue_keywords": legal_issues,
}
# Output: reduced set (target: 20% of input)
```

### Phase 2 — NARROW (GLASS tier)
Deeper scan of filtered set. Score relevance. Rank by relevance score.
```python
# Narrow criteria
narrow_criteria = {
    "citation_match": case_citations,
    "statute_refs": ["Companies Act 1993", "Insolvency Act 2006"],
    "party_match": matter_parties,
    "issue_proximity": 0.70,  # minimum relevance score
}
# Output: top 5-10 documents with relevance scores
```

### Phase 3 — DEEP-ANALYSE (IRON tier)
Full IRON-tier reasoning on narrowed set only.
Load complete document text. Apply full legal reasoning.
```python
# Only 5-10 documents reach this phase
# Full Opus 4.6 reasoning applied
# Citations, legal issues, strategy implications extracted
```

## Iron Fleet Agent Mapping

| Agent | Decomposition Application |
|---|---|
| @HUNTER | Filter by jurisdiction + date → narrow by issue → deep-retrieve relevant chunks |
| @STRAT | Filter case history → narrow to directly relevant precedents → deep-analyse strategy implications |
| @AUDITOR | Filter discovery set → narrow to clause/entity references → deep-validate inconsistencies |
| @SUMMARISER | Filter bundle → narrow to key documents → two-level summary (practitioner + client) |

## Cost Model

| Phase | Tier | Approx tokens per doc | When to stop |
|---|---|---|---|
| Filter | GLASS | ~200 | Keep < 20% of corpus |
| Narrow | GLASS | ~1,000 | Keep top 5-10 docs |
| Deep-analyse | IRON | ~10,000 | All narrowed docs |

For a 50-judgment corpus:
- Filter: 50 × 200 = 10,000 tokens (GLASS)
- Narrow: 10 × 1,000 = 10,000 tokens (GLASS)
- Deep: 5 × 10,000 = 50,000 tokens (IRON)
- **Total: ~70,000 tokens vs 500,000 tokens for full-context load**

## Confidence Signals

| Signal | Weight | How scored |
|---|---|---|
| `filter_reduction` | 0.40 | 1.0 if filtered to < 30% of input; 0.5 if < 60% |
| `narrow_quality` | 0.35 | 1.0 if relevance scores > 0.70; 0.5 if lower |
| `deep_coverage` | 0.25 | 1.0 if all narrowed docs analysed; proportional if partial |

## Ambiguity Handling

If document count < 5, skip decomposition — load all documents directly.
Output `[DECOMPOSITION-NOT-NEEDED — LOAD-DIRECT]` as a note.

If filter phase retains > 60% of corpus, narrow criteria are too broad.
Output `[FILTER-INEFFECTIVE — REVIEW-CRITERIA]`.

If deep-analyse phase exceeds 10 documents, narrow phase was insufficient.
Output `[NARROW-INEFFECTIVE — RE-NARROW]`.

Never send more than 10 documents to IRON-tier deep-analyse.

## Output Schema
```json
{
  "status": "SUCCESS | FLAGGED",
  "result": {
    "input_document_count": 50,
    "filter_retained": 10,
    "narrow_retained": 5,
    "deep_analysed": 5,
    "filter_reduction_pct": 80,
    "estimated_token_savings": 430000,
    "decomposition_plan": [
      {
        "phase": "filter",
        "criteria": {"jurisdiction": "NZ", "court": ["NZHC"]},
        "estimated_tokens": 10000
      }
    ],
    "recommended_deep_docs": ["chunk_abc", "chunk_def"]
  },
  "confidence": 0.88,
  "flags": [],
  "trust_tier": "T1"
}
```