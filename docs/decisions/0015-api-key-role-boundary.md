# API Key Role Boundary

Date: 2026-06-17

## Status

Accepted

## Context

The internal FastAPI service exposes research automation routes for metrics,
run lookup, report lookup, as-of signals, and experiment execution. Before
adding live providers, managed persistence, or broker-adjacent workflows, the
service needs a clear access boundary.

The current repo does not have users, sessions, tenants, or a managed identity
provider. Adding those now would expand the story beyond a local Level 1
research platform.

## Decision

Protect every non-health API route with `X-API-Key`:

- API keys are configured through `AIQRA_API_KEYS` as comma-separated
  `key:role` entries.
- Roles are `viewer`, `researcher`, and `operator`.
- Role hierarchy is `viewer < researcher < operator`.
- Metrics, experiment lookup, report lookup, and signal routes require
  `viewer`.
- Experiment execution requires `researcher`.
- `/health` remains public for deployment probes.
- If no API keys are configured, protected routes fail closed.

## Alternatives Considered

1. Keep the internal API unauthenticated. Rejected because future provider,
   registry, and execution-adjacent work should not build on a public research
   surface.
2. Add JWT sessions and user management now. Rejected because the repo has no
   multi-user product model yet.
3. Protect only mutating routes. Rejected because reports, run metadata, and
   signals can still expose sensitive research information.

## Consequences

Positive:

- The API has a simple fail-closed boundary.
- Local and CI validation can exercise role behavior without external services.
- Future auth can replace the API-key parser behind the same role contract.

Tradeoffs:

- API keys are static shared secrets, not user identities.
- There is no key rotation, revocation table, or per-request audit actor yet.

## Follow-Up

- Add authenticated actor ids to request logs.
- Promote keys to a managed secret store or identity provider before multi-user
  SaaS deployment.
