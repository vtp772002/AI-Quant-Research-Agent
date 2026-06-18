# Locked Institutional Holdout Dataset Boundary

Date: 2026-06-18

## Status

Accepted

## Context

Research validity now evaluates holdout performance and controls cross-run
family shopping. Registry governance packs make exported evidence verifiable.
The remaining methodology gap is that the holdout slice itself is still derived
from ordinary configured market data at runtime. Promotion evidence should be
able to prove that a separately reviewed institutional holdout boundary was
used and that it was not silently changed.

## Decision

Add an optional locked holdout manifest boundary under research validity.
When enabled, the workflow validates the realized holdout slice against a local
manifest and fails closed on mismatch.

The first implementation is deterministic and local:

- no managed data warehouse;
- no live vendor API;
- no credentials;
- no access-control service.

Locked holdout evidence is written into CLI JSON, the reproducibility manifest,
registry JSON metrics, and the Markdown report.

## Alternatives Considered

1. New holdout data loader. Deferred because validating the realized holdout
   slice is the narrowest methodologically useful boundary.
2. Warning-only manifest validation. Rejected because configured locked holdout
   evidence must fail closed.
3. Managed storage first. Deferred to US-030 because storage deployment needs
   ownership, credentials, and retention rules.

## Consequences

Positive:

- Promotion evidence can prove the holdout boundary used for the run.
- Hash/date/symbol/row-count drift fails closed when the lock is configured.
- The boundary remains deterministic and local for CI.

Tradeoffs:

- Local manifests do not enforce access control by themselves.
- A locked holdout manifest must be maintained when the reviewed dataset changes.
- Managed storage and object-lock enforcement remain future work.

## Follow-Up

- Promote locked holdout artifacts into the managed Postgres/object-lock adapter
  in US-030.
- Add authorization around holdout review if the project becomes multi-user.
