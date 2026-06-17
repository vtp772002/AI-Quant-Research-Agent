# Design

## Domain Model

- Review queue: existing `idea_review` JSON queue with records and status
  counts.
- Review audit event: existing append-only JSONL event stream.
- API principal: sanitized API key id and role from the existing API auth
  boundary.

## Application Flow

Read endpoints delegate directly to `review_summary` and `review_audit_events`.
Write endpoints accept a Pydantic request body, require researcher access, and
delegate status mutation or approved batch execution to existing application
services.

When the API changes review state, it passes `api:<sanitized_key_id>` as the
review actor. The review audit ledger stores that actor, not the raw API key.

## Interface Contract

Viewer or higher:

- `GET /reviews/ideas?review_queue=<path>`
- `GET /reviews/audit?review_queue=<path>`

Researcher or higher:

- `POST /reviews/ideas/status`
- `POST /reviews/approved/run`

Missing queues return 404. Invalid statuses or empty approved queues return
400. Existing API request logs continue to record auth decision context for the
same requests.

## Data Model

No migration. This story reuses file-backed `review_queue.json` and
`review_audit.jsonl`.

## UI / Platform Impact

No browser UI. The internal API can now act as the automation boundary for
review queue inspection and approved generated-idea execution.

## Observability

Request logs include sanitized API auth context. Product audit events include
sanitized API actor ids for status changes and run marking.

## Alternatives Considered

1. Keep review operations CLI-only.
2. Add unauthenticated review endpoints.
3. Split review queue operations into a separate service immediately.
