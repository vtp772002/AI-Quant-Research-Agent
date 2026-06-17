# Overview

## Current Behavior

The internal FastAPI service exposes health, metrics, run execution, experiment
lookup, report lookup, and signal routes. Before this story, those routes were
callable without authentication.

## Target Behavior

`/health` remains public for deployment checks. All other API routes require an
`X-API-Key` configured through `AIQRA_API_KEYS`. Viewer keys can read metrics,
runs, reports, and signals. Researcher keys can also run experiments. Operator
keys inherit researcher permissions for future operational routes.

## Affected Users

- Internal research automation calling the API.
- Quant researcher querying reports and signals.
- Operator running experiments through the API.

## Affected Product Docs

- `README.md`
- `docs/product/ai-quant-research-agent.md`
- `docs/ARCHITECTURE.md`
- `.env.example`

## Non-Goals

- User accounts, sessions, JWTs, or OAuth.
- Tenant-scoped authorization.
- Key rotation or managed secret storage.
- Authenticated actor request audit logs.
