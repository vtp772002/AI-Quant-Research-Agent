# Overview

## Current Behavior

US-026 emits a run-level Research Validity Gate verdict using an untouched
chronological holdout and Benjamini-Hochberg FDR correction across candidates
inside one run.

Before US-027, the platform still could not account for experiment shopping
across multiple related runs. A researcher could run several configs and select
the best-looking run after the fact without a family-level correction.

## Target Behavior

The CLI can compare an experiment family across run manifests and emit
family-level verdicts:

- `FAMILY_PROMOTE`: a pre-registered run-level `PROMOTE` candidate survives
  family-level FDR correction with comparable provenance.
- `FAMILY_REVIEW`: evidence is incomplete, not pre-registered, not comparable,
  or operationally ambiguous.
- `FAMILY_REJECT`: run-level validity rejects the candidate or family q-value
  fails the configured alpha.

Every run manifest and registry row can carry `experiment_family` metadata:
family id, hypothesis id, candidate id, and selection policy.

## Affected Users

- Quant researcher deciding whether a selected signal survived the full family
  of related experiments.
- Operator reviewing generated, exploratory, or manually selected candidates.
- Future developer promoting the local registry into managed storage.

## Affected Product Docs

- `README.md`
- `docs/product/ai-quant-research-agent.md`
- `docs/TEST_MATRIX.md`

## Non-Goals

- Managed Postgres or object-storage registry deployment.
- Immutable registry governance or multi-user authorization.
- Automatic selection of a best run after search.
- Trading, investment approval, or compliance approval.
