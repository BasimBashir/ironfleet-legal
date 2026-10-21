---
name: nz-data-structure-protocol
description: Use this skill whenever SIM-A-18 needs to design or extend the knowledge graph memory layer, when @STRAT or @HUNTER need to persist entity relationships across long-running matters, when designing graph schemas for entity_graph_schema.json, or when adding new node or edge types to the Cognee Neo4j knowledge graph. Also invoke when designing data structures for vulnerability mapping, cross-matter entity tracking, or any graph-based long-term memory that must survive across agent sessions. Adapted from k-kolomeitsev/data-structure-protocol — Iron Fleet contextualised for NZ legal entity graphs, SIM-A-18 knowledge-graph- vulnerability-mapper, and Cognee Neo4j integration.
license: Apache-2.0
compatibility: Claude Code, Claude Desktop, Claude Cowork. Corpus tools need local Python 3.10+ and Ollama.
metadata:
  mode: GLASS
  version: 1.0.0
  source_kernel: nz_data_structure_protocol.py
  function: run
  permissions: []
  trust_tier_required: 1
  adapted_from: k-kolomeitsev/data-structure-protocol
---


# nz-data-structure-protocol

## Purpose
Graph-based data structure design for Iron Fleet long-term memory. Adapted
from k-kolomeitsev/data-structure-protocol.

Target: SIM-A-18 `knowledge-graph-vulnerability-mapper` and the graph memory
layer over `entity_graph_schema.json` in Iron Fleet's Cognee Neo4j instance.

## Iron Fleet Entity Graph Schema

### Core Node Types
```json
{
  "Party": {
    "properties": ["name", "role", "jurisdiction", "counsel", "trust_tier"],
    "indexes": ["name", "role"]
  },
  "Document": {
    "properties": ["chunk_id", "title", "doc_type", "wp_status",
                   "created_date", "sha256", "trust_tier"],
    "indexes": ["chunk_id", "wp_status"]
  },
  "LegalIssue": {
    "properties": ["description", "statute_ref", "case_citation",
                   "issue_type", "resolution_status"],
    "indexes": ["issue_type", "statute_ref"]
  },
  "Matter": {
    "properties": ["matter_ref", "court", "filing_date", "status",
                   "jurisdiction"],
    "indexes": ["matter_ref"]
  },
  "Vulnerability": {
    "properties": ["vuln_type", "severity", "entity_ref", "detected_date",
                   "remediation_status"],
    "indexes": ["vuln_type", "severity"]
  },
  "DeadlineEvent": {
    "properties": ["event_type", "due_date", "rule_ref", "status"],
    "indexes": ["due_date", "status"]
  }
}
```

### Core Edge Types
```json
{
  "PARTY_IN_MATTER": {"from": "Party", "to": "Matter"},
  "FILED": {"from": "Party", "to": "Document"},
  "EXHIBITS": {"from": "Document", "to": "Document"},
  "RAISES": {"from": "Document", "to": "LegalIssue"},
  "GOVERNED_BY": {"from": "LegalIssue", "to": "Statute"},
  "HAS_DEADLINE": {"from": "Matter", "to": "DeadlineEvent"},
  "VULNERABILITY_IN": {"from": "Vulnerability", "to": "Document"},
  "CROSS_MATTER_ENTITY": {"from": "Party", "to": "Party",
                           "properties": ["relationship_type", "matters"]}
}
```

## SIM-A-18 Vulnerability Mapper Integration

SIM-A-18 `knowledge-graph-vulnerability-mapper` sits on top of this schema.
Vulnerability nodes capture:
- `vuln_type`: e.g. "conflicting_affidavit", "missing_exhibit",
  "unsigned_document", "privilege_mismatch"
- `severity`: HIGH / MEDIUM / LOW
- `entity_ref`: chunk_id of the document with the vulnerability
- `remediation_status`: OPEN / IN_PROGRESS / RESOLVED

Cypher query pattern for SIM-A-18:
```cypher
MATCH (v:Vulnerability {severity: "HIGH"})
-[:VULNERABILITY_IN]->(d:Document)
-[:FILED]->(p:Party)
RETURN v, d, p
ORDER BY v.detected_date DESC
```

## Graph Design Principles

1. **Privilege-safe nodes** — Document nodes always carry `wp_status`.
   Never expose WP node content in graph exports.
2. **Chunk ID integrity** — Every Document node must have a `chunk_id`
   matching the Iron Fleet corpus. No orphaned nodes.
3. **Trust tier on nodes** — Every node carrying case data must have
   `trust_tier` property. Enables T0-filtered queries.
4. **Idempotent merges** — Use `MERGE` not `CREATE` to avoid duplicates
   on re-ingestion.
5. **Audit trail** — Every edge creation must record `created_at` and
   `created_by_agent` properties.

## Cypher Patterns for Iron Fleet
```cypher
-- Create a Party node (idempotent)
MERGE (p:Party {name: $name})
SET p.role = $role,
    p.trust_tier = $trust_tier,
    p.updated_at = datetime()

-- Create a Document node with privilege
MERGE (d:Document {chunk_id: $chunk_id})
SET d.wp_status = $wp_status,
    d.trust_tier = $trust_tier,
    d.sha256 = $sha256

-- Link Party to Document
MATCH (p:Party {name: $party_name})
MATCH (d:Document {chunk_id: $chunk_id})
MERGE (p)-[:FILED {created_at: datetime(), created_by_agent: $agent}]->(d)
```

## Confidence Signals

| Signal | Weight | How scored |
|---|---|---|
| `schema_valid` | 0.40 | 1.0 if all required node types present; proportional |
| `privilege_fields_present` | 0.35 | 1.0 if wp_status on Document nodes; 0.0 if missing |
| `chunk_id_integrity` | 0.25 | 1.0 if all docs have chunk_id; proportional |

## Ambiguity Handling

If a node definition is missing `wp_status` on Document type, output
`[PRIVILEGE-FIELD-MISSING — SCHEMA-INVALID]` and halt.

If chunk_id is missing from Document node, output
`[CHUNK-ID-MISSING — ORPHANED-NODE-RISK]`.

If an edge references a node type not in the schema, output
`[UNKNOWN-NODE-TYPE — SCHEMA-EXTENSION-REQUIRED]`.

## Output Schema
```json
{
  "status": "SUCCESS | FLAGGED | ERROR",
  "result": {
    "schema_valid": true,
    "node_types": ["Party", "Document", "LegalIssue"],
    "edge_types": ["FILED", "RAISES"],
    "privilege_fields_present": true,
    "chunk_id_integrity": true,
    "missing_fields": [],
    "cypher_merge_patterns": ["MERGE (p:Party {name: $name})..."],
    "sim_a18_compatibility": true
  },
  "confidence": 0.92,
  "flags": [],
  "trust_tier": "T1"
}
```