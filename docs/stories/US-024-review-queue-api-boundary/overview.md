# Overview

## Current Behavior

Generated ideas write `review_queue.json` and `review_audit.jsonl`. CLI commands
can inspect the queue, update status, print audit events, and run approved
configs, but the internal API does not expose those review operations.

## Target Behavior

The internal FastAPI service exposes review queue summary, audit, status-update,
and run-approved operations behind the existing API key role boundary. Viewer
keys can read queue state and audit events. Researcher and operator keys can
update review status and run approved configs. API mutations write sanitized API
actor ids into the review audit ledger.

## Affected Users

- Quant researcher automating idea review.
- Operator integrating the internal API into scheduled research workflows.
- Future developer promoting local review queues into managed storage.

## Affected Product Docs

- `README.md`
- `docs/product/ai-quant-research-agent.md`
- `docs/ARCHITECTURE.md`

## Non-Goals

- Public API exposure.
- User accounts, tenants, sessions, or JWTs.
- Multi-party approval workflow.
- Managed review database or tamper-proof audit storage.
- Broker or live-trading integration.
