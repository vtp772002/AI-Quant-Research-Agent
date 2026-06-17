# Review Audit Ledger For Generated Ideas

Date: 2026-06-17

## Status

Accepted

## Context

US-020 added a portable `review_queue.json` gate so generated idea configs
cannot run without human approval. That queue stores current state, but current
state alone does not explain how an idea moved from `draft` to `approved`,
`rejected`, `archived`, or `ran`.

For the next governance slice, the system needs a durable local trail without
introducing auth, multi-user approval policy, or a managed database migration.

## Decision

Add an append-only `review_audit.jsonl` ledger beside each review queue:

- Queue creation records one `created` event per generated idea.
- Status changes record `status_changed` events with previous status, next
  status, actor, note, queue path, idea name, config path, source, and timestamp.
- Completed approved runs record `ran` events.
- CLI operators can set `--review-actor` and inspect events with
  `--review-audit`.

## Alternatives Considered

1. Store only the latest queue state. Rejected because it loses review history.
2. Add a managed SQLite audit table now. Deferred because review queues are
   artifact-first and multi-user retention is not yet in scope.
3. Require auth before audit. Rejected for this slice because local operator
   attribution is useful before role-scoped authorization exists.

## Consequences

Positive:

- Review state changes become explainable and replayable from artifacts.
- CLI smoke tests can prove the full create, approve, run audit chain.
- Future managed registry or auth work has a concrete event schema to promote.

Tradeoffs:

- Actor is operator-supplied text, not authenticated identity.
- JSONL is append-only by convention, not tamper-proof storage.

## Follow-Up

- Promote review audit events into a managed registry table when auth,
  retention, or role-scoped approval is implemented.
