# Attribution & licences

## New Zealand legislation corpus

New Zealand statutes referenced by this plugin (Companies Act 1993, PPSA 1999, Limitation
Act 2010, CCLA 2017, Privacy Act 2020, High Court Rules 2016, Evidence Act 2006, and
others) are Crown copyright, available under
[CC BY 4.0](https://creativecommons.org/licenses/by/4.0/) from
[legislation.govt.nz](https://www.legislation.govt.nz). **This plugin ships no corpus
content** — users ingest official text themselves; ingested statute rows carry licence +
source URL + retrieval date (the ingester refuses rows without them).

## Adapted skills

Skills credited "Adapted from" an upstream source carry that source's licence, verified
against each repository on 2026-10-21:

| Skill | Upstream | Upstream licence |
|---|---|---|
| summariser | anthropics/knowledge-work-plugins | Apache-2.0 |
| affidavit-formatter | anthropics/knowledge-work-plugins | Apache-2.0 |
| nz-property-based-testing | trailofbits/skills | CC-BY-SA-4.0 |
| nz-differential-review | trailofbits/skills | CC-BY-SA-4.0 |
| nz-memory-systems | muratcankoylan/Agent-Skills-for-Context-Engineering | MIT |
| nz-context-compression | muratcankoylan/Agent-Skills-for-Context-Engineering | MIT |
| nz-data-structure-protocol | k-kolomeitsev/data-structure-protocol | Apache-2.0 |
| nz-nutrient-processor | PSPDFKit-labs/nutrient-agent-skill | MIT-0 |
| nz-varlock | wrsmith108/varlock-claude-skill | MIT |
| nz-kreuzberg-ingestor | kreuzberg-dev/kreuzberg | MIT |

**Not distributed:** an `nz-contract-reviewer` skill adapted from
lawvable/awesome-legal-skills (CC-BY-NC-ND-4.0, no-derivatives) exists in the source
programme but is **excluded from this distribution** — its licence does not permit
redistribution of adaptations. It may return as a from-scratch rewrite.

CC-BY-SA-4.0 skills (nz-property-based-testing, nz-differential-review) are licensed
CC-BY-SA-4.0 as adapted; share-alike applies to those files.

## Vendored kernel code

`mcp/harness/` vendors modules from the IronFleet harness programme (corpus store,
vector index, statutory-demand kernel, without-prejudice detector, NZ/AU/UK court
calendar with holiday data) — IronFleet's own code, MIT. The holiday JSONs cover
NZ/AU/UK 2024–2030; upstream public-holiday sources are recorded in each file.
