---
name: nz-contract-review-analyzer
description: 'Analyses commercial contracts clause-by-clause against a standard NZ commercial playbook.  Flags deviations as GREEN/YELLOW/RED, generates redline suggestions, and produces a negotiation priority report. Use when: Use when reviewing a commercial contract, NDA, service agreement, or any document with legal clauses that need assessment against standard positions. Suitable for pre-signature review, vendor assessment, and risk flagging.'
license: MIT
compatibility: Claude Code, Claude Desktop, Claude Cowork. Corpus tools need local Python 3.10+ and Ollama.
metadata:
  version: 1.0.0
  source_kernel: contract_review.py
  function: analyse_contract
  parameters:
    contract_text:
      type: string
      required: true
      description: The full contract text to analyse.
    playbook:
      type: object
      required: false
      description: Custom playbook dict overriding default clause positions. Keys are clause categories.
    focus_areas:
      type: array
      required: false
      description: List of clause categories to prioritise (e.g. ['liability', 'indemnification']).
  returns:
    clauses:
      type: array
      description: List of clause analysis dicts with category, flag, summary, deviation, redline.
    overall_risk:
      type: string
      description: GREEN / YELLOW / RED overall assessment.
    red_count:
      type: integer
      description: Number of RED-flagged clauses.
    yellow_count:
      type: integer
      description: Number of YELLOW-flagged clauses.
    green_count:
      type: integer
      description: Number of GREEN-flagged clauses.
    negotiation_priorities:
      type: array
      description: Ordered list of clauses to negotiate, highest priority first.
  mode: both
  permissions: []
  trust_tier_required: 2
---


# NZ Contract Review Analyzer

Analyses commercial contracts against a standard NZ commercial playbook.
Covers 14 clause categories with GREEN/YELLOW/RED classification.
