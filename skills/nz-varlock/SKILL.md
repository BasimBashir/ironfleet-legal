---
name: nz-varlock
description: Use this skill whenever any Iron Fleet agent, script, or developer session needs to handle API keys, credentials, or secrets. Invoke when setting up a new development environment, when adding a new API key to Iron Fleet, when validating that secrets are properly masked, or when any code touches NUTRIENT_DWS_API_KEY, OPENROUTER_API_KEY, COGNEE credentials, or any other sensitive configuration. Also invoke immediately if a secret has been exposed in a session, terminal output, or git commit. Adapted from wrsmith108/varlock-claude-skill — Iron Fleet contextualised for NZ legal platform secret management, Nutrient key rotation protocol, and references/env_vars.md enforcement.
license: MIT
compatibility: Claude Code, Claude Desktop, Claude Cowork. Corpus tools need local Python 3.10+ and Ollama.
metadata:
  mode: GLASS
  version: 1.0.0
  source_kernel: nz_varlock.py
  function: run
  permissions: []
  trust_tier_required: 0
  adapted_from: wrsmith108/varlock-claude-skill
---


# nz-varlock

## Purpose
Secure secret management for Iron Fleet development sessions. Adapted from
wrsmith108/varlock-claude-skill.

Iron Fleet already has `references/env_vars.md` documenting required secrets.
This skill enforces that document — ensuring secrets are never exposed in
agent sessions, terminal output, logs, or git commits.

## CRITICAL — Nutrient Key Exposure Protocol

The Nutrient DWS API key was exposed in a session (Test run 20260320_182500).
**Rotate immediately:**

1. Go to `dashboard.nutrient.io`
2. Revoke the exposed key
3. Generate a new key
4. Update via varlock — NOT by editing .env directly in Claude session
5. Run `varlock load` to confirm new key is masked correctly
6. Notify Basim — any code touching Nutrient API requires security sign-off

## Iron Fleet Secrets Registry

| Secret | varlock key | Sensitivity | Used by |
|---|---|---|---|
| `NUTRIENT_DWS_API_KEY` | `NUTRIENT_DWS_API_KEY` | CRITICAL | nz-nutrient-processor |
| `OPENROUTER_API_KEY` | `OPENROUTER_API_KEY` | CRITICAL | Agent LLM routing |
| `COGNEE_API_KEY` | `COGNEE_API_KEY` | HIGH | Memory/GraphRAG |
| `GITLAB_TOKEN` | `GITLAB_TOKEN` | HIGH | CI/CD, Basim PR gate |
| `NEO4J_PASSWORD` | `NEO4J_PASSWORD` | HIGH | Knowledge graph |
| `PGVECTOR_PASSWORD` | `PGVECTOR_PASSWORD` | HIGH | Vector RAG |

## Safe vs Unsafe Patterns

### NEVER DO (exposes secrets to agent context)
```powershell
# UNSAFE
cat .env
echo $NUTRIENT_DWS_API_KEY
Get-Content .env
$env:NUTRIENT_DWS_API_KEY
git diff .env
```

### ALWAYS DO (validates without exposing)
```powershell
# SAFE
varlock load                          # validates, shows masked values
varlock load --quiet                  # silent validation
varlock run -- python scripts/test.py # inject secrets into subprocess
cat .env.schema                       # schema only, no values
```

## .env.schema for Iron Fleet
```
# Iron Fleet secrets schema
# DO NOT commit .env — only commit .env.schema

# @type=string @sensitive
NUTRIENT_DWS_API_KEY=

# @type=string @sensitive
OPENROUTER_API_KEY=

# @type=string @sensitive
COGNEE_API_KEY=

# @type=string @sensitive
GITLAB_TOKEN=

# @type=string @sensitive
NEO4J_PASSWORD=

# @type=string @sensitive
PGVECTOR_PASSWORD=
```

## Git Safety Rules
```
# .gitignore must include:
.env
.env.local
.env.*.local
*.key
*.pem
secrets/
```

Run before every commit:
```powershell
varlock load --quiet && git commit -m "..."
```

## Secret Exposure Response Protocol

If a secret is exposed:
1. **Immediately** — rotate the key at the provider dashboard
2. **Within 5 minutes** — notify Basim
3. **Before next session** — update varlock-managed .env
4. **Audit** — check git log for any committed secrets
5. **Prevent** — add pre-commit hook: `varlock load --quiet`

## Confidence Signals

| Signal | Weight | How scored |
|---|---|---|
| `varlock_available` | 0.40 | 1.0 if varlock CLI found; 0.5 if simulated |
| `schema_present` | 0.35 | 1.0 if .env.schema exists; 0.0 if missing |
| `no_plaintext_secrets` | 0.25 | 1.0 if no .env in git; 0.0 if .env tracked |

## Ambiguity Handling

If varlock is not installed, output `[VARLOCK-NOT-INSTALLED]` with
installation instructions. Do not proceed with raw .env access.

If .env.schema is missing, output `[ENV-SCHEMA-MISSING — CREATE-SCHEMA]`.

If .env is tracked in git, output `[SECRET-IN-GIT — IMMEDIATE-ACTION]`
and provide remediation steps.

## Output Schema
```json
{
  "status": "SUCCESS | FLAGGED | ERROR",
  "result": {
    "varlock_available": true,
    "schema_present": true,
    "secrets_validated": true,
    "env_in_git": false,
    "exposed_keys": [],
    "masked_summary": {
      "NUTRIENT_DWS_API_KEY": "▒▒▒▒▒ (set)",
      "OPENROUTER_API_KEY": "▒▒▒▒▒ (set)"
    },
    "recommended_actions": []
  },
  "confidence": 0.95,
  "flags": [],
  "trust_tier": "T1"
}
```