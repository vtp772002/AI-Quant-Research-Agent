# Overview

## Current Behavior

US-020 writes `review_queue.json` and enforces approval before generated idea
configs can run. The queue captures current state and notes, but it does not
preserve a durable event history for creation, approval, rejection, archival, or
run marking.

## Target Behavior

Each generated idea review queue writes an append-only `review_audit.jsonl`
ledger. The ledger records creation, status changes, and run marking with actor,
note, previous status, next status, timestamps, and artifact paths. The CLI can
print audit events for review.

## Affected Users

- Quant researcher reviewing generated hypotheses.
- Operator running approved generated idea batches.
- Future developer promoting review state into managed storage.

## Affected Product Docs

- `README.md`
- `docs/product/ai-quant-research-agent.md`
- `docs/ARCHITECTURE.md`

## Non-Goals

- Authenticated identity.
- Tamper-proof audit storage.
- Managed database-backed review audit tables.
- Multi-user approval policy.
