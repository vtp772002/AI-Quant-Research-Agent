# Overview

## Current Behavior

The platform can compute `FAMILY_PROMOTE`, preserve registry evidence, validate
a locked holdout, and stage managed-registry artifacts. Promotion remains an
advisory result with no separate recommendation and approval workflow.

## Target Behavior

The platform supports a local two-person family-promotion workflow:

- a researcher recommends one run from recomputed `FAMILY_PROMOTE` evidence;
- the exact comparison evidence is frozen and hashed;
- a distinct operator approves or rejects the recommendation;
- all events are appended to a hash-chained ledger;
- events are HMAC-authenticated and mutation transactions are serialized;
- verification fails closed on tampering, role violations, duplicate
  recommendations, same-actor decisions, or invalid state transitions;
- CLI and role-scoped API operations expose the same behavior.

## Affected Users

- Quant researcher recommending a validated candidate.
- Research operator approving or rejecting promotion.
- Auditor verifying evidence and actor separation.

## Affected Product Docs

- `README.md`
- `docs/product/ai-quant-research-agent.md`
- `docs/ARCHITECTURE.md`
- `docs/TEST_MATRIX.md`

## Non-Goals

- External identity providers or tenant management.
- Credentialed Postgres or object-lock mutation.
- Queue-backed scheduling.
- Paper trading, broker execution, or compliance approval.
