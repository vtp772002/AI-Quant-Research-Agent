# Cross-Run Experiment Family Controls

Date: 2026-06-18

## Status

Accepted

## Context

US-026 controls false discovery inside one run, but a researcher can still run
many related configurations and select the best-looking result after the fact.
That cross-run experiment-shopping risk is a methodology gap in the local
research platform.

## Decision

Add optional experiment-family metadata to configs, manifests, and registry
rows, and add a CLI family comparison command that applies
Benjamini-Hochberg FDR correction across related runs.

Family promotion is conservative:

- only pre-registered rows can reach `FAMILY_PROMOTE`;
- run-level `REJECT` remains rejected;
- missing evidence or metadata requires review;
- mixed provenance requires review;
- q-values above alpha reject;
- the gate remains advisory and does not change process exit status.

## Alternatives Considered

1. Manifest-only family control. Rejected because registry rows would not carry
   the local system-of-record metadata.
2. Managed registry/object storage first. Deferred because storage deployment
   should follow the methodology contract.
3. Auto-select the best family row. Rejected because it would preserve
   experiment-shopping risk.

## Consequences

Positive:

- Promotion evidence now accounts for related runs, not just variants inside
  one run.
- Family comparison is deterministic, local, and portable through manifests.
- Existing registries migrate in place without losing rows.

Tradeoffs:

- The local SQLite registry is still mutable and not an immutable governance
  ledger.
- Family correctness depends on honest family metadata and selection policy.
- Managed storage, authorization, and retention remain future work.

## Follow-Up

- Promote the registry to managed Postgres/object storage after ownership,
  migration, and retention rules are specified.
- Add immutable registry governance before any external investment process
  depends on family verdicts.
