# Research Validity Promotion Gate

Date: 2026-06-18

## Status

Accepted

## Context

The platform already reports chronological validation metrics, walk-forward
windows, baselines, robustness checks, capacity diagnostics, manifests, and
registry rows. Those surfaces are enough to inspect an exploratory run, but not
enough to call a result promotion-ready: the same validation evidence can be
used during iteration, and the run evaluates multiple baselines and variants.

The missing control is a reproducible gate that distinguishes exploratory
validation from a final research-promotion decision without turning the project
into a trading or compliance system.

## Decision

Add an advisory research-validity gate with these rules:

- Reserve a configurable chronological tail holdout for promotion evidence.
- Keep `test` as a compatibility alias for validation-period metrics.
- Exclude holdout observations from validation diagnostics and capacity gates;
  validation forward-return observations whose realization date crosses the
  holdout boundary are purged.
- Build the within-run candidate family from the agent signal, configured
  baselines, enabled stress tests, parameter-sensitivity variants, and
  cost-sensitivity variants.
- Compute one-sided positive-holdout-IC p-values and apply
  Benjamini-Hochberg FDR correction across that family.
- Emit `PROMOTE`, `REVIEW`, or `REJECT` using explicit statistical, economic,
  baseline, walk-forward, and data-readiness checks.
- Treat the verdict as advisory: `REJECT` does not change the process exit code
  and does not suppress normal artifacts.

This controls false discovery rate only for the candidate family evaluated
inside one recorded run. It does not claim protection across unrecorded manual
experiments or separate historical runs.

## Alternatives Considered

1. Add a verdict over existing test metrics. Rejected because the existing
   validation/test period is already part of exploratory analysis.
2. Require a separately locked holdout dataset. Deferred because it needs
   institutional data-release and access-control procedures outside this story.
3. Hard-fail the process on `REJECT`. Rejected because invalid or weak research
   results are still useful artifacts for review and iteration.

## Consequences

Positive:

- Promotion language is now tied to explicit holdout, FDR, economic, baseline,
  stability, and data-readiness checks.
- Reports and machine-readable artifacts show why a result is promoted,
  rejected, or needs review.
- Existing automation can keep running because the gate is advisory.

Tradeoffs:

- A same-dataset chronological tail holdout is weaker than a separately locked
  dataset.
- Benjamini-Hochberg correction is scoped to one run's candidate family and
  does not solve cross-run experiment shopping.
- Current demo configs may reject despite positive validation-period evidence;
  that is expected because the gate is stricter than exploration metrics.

## Follow-Up

- Add cross-run experiment-family controls when the registry becomes the
  authoritative experiment selection ledger.
- Add separately access-controlled holdout datasets during the institutional
  data phase.
- Review prompt/provider-generated experiment families against this gate before
  treating generated ideas as promotion candidates.
