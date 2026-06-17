# Design

## Domain Model

- Review queue: `review_queue.json` with current status records.
- Review audit ledger: `review_audit.jsonl` beside the queue.
- Audit event: event id, event type, queue path, idea name, config path, source,
  previous status, next status, actor, note, and created timestamp.

## Application Flow

Idea generation writes queue records and appends one `created` event per idea.
Review status changes append `status_changed` events. Successful approved idea
batch runs append `ran` events.

The queue remains the gate source for current status. The audit ledger is the
history source.

## Interface Contract

CLI additions:

- `--review-audit --review-queue <path>` prints audit events.
- `--review-actor <actor>` records operator text on status changes and run
  marking.

## Data Model

No database migration. The ledger is artifact-backed JSONL.

## UI / Platform Impact

CLI-only workflow. No API or browser surface changes.

## Observability

Every queue lifecycle starts with `created` events. Every mutation appends an
event; existing queue summaries include `audit_path`.

## Alternatives Considered

1. Keep only latest queue state.
2. Add a SQLite review audit table immediately.
3. Wait for auth before adding any review trail.
