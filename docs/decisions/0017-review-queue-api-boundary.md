# Review Queue API Boundary

Date: 2026-06-17

## Status

Accepted

## Context

Generated research ideas already flow through a local review queue and
append-only review audit ledger. The CLI can review ideas, change status, and
run approved configs, but internal automation cannot access that boundary
through the FastAPI service added for production research workflows.

The API already has role-scoped access, sanitized API key actor ids, and
structured request auth logs. Review queue operations should reuse those
boundaries instead of inventing separate API credentials or bypassing review
state.

## Decision

Expose review queue operations through the internal FastAPI service:

- `GET /reviews/ideas` returns queue summary and records.
- `GET /reviews/audit` returns append-only review audit events.
- `POST /reviews/ideas/status` updates one idea status and records the API
  actor in the review audit ledger.
- `POST /reviews/approved/run` runs approved configs through the existing batch
  orchestrator and marks completed configs as `ran`.

Viewer keys can read review summaries and audit events. Researcher and operator
keys can mutate review status and run approved configs. API-originated review
events use sanitized actors such as `api:rese...cret`; raw keys are not written
to queue, audit, or request logs.

## Alternatives Considered

1. Keep review operations CLI-only. Rejected because internal automation would
   need shell access to participate in the governed research loop.
2. Add unauthenticated review endpoints. Rejected because review state controls
   whether generated configs can execute.
3. Add a separate review service. Deferred because the existing FastAPI role
   boundary is sufficient for the current internal research platform.

## Consequences

Positive:

- Internal automation can inspect review queues without shelling out.
- Review mutations retain the append-only audit ledger.
- Role requirements match the existing API key hierarchy.

Tradeoffs:

- Queue paths are still filesystem paths supplied by trusted internal callers.
- API key roles are coarse; they do not model individual users or multi-party
  approvals.
- Review audit remains file-backed rather than a managed compliance store.

## Follow-Up

- Add managed review storage and stronger user identity if review workflows
  become multi-user or compliance-critical.
