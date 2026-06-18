# Design

## Domain Model

- `ResearchValidityConfig`: parse-time validated settings under
  `experiment.validation.research_validity`.
- `BacktestResult`: exposes `train`, `validation`, `holdout`, compatibility
  `test`, and `full` metrics; `test` remains an alias for validation so older
  surfaces keep their contract.
- `CandidateEvidence`: holdout IC, IC t-stat, Sharpe, total return,
  observations, raw p-value, and Benjamini-Hochberg q-value for one evaluated
  candidate.
- `ValidityCheck`: one named requirement with required/pass/fail state,
  observed value, threshold, and reason.
- `ResearchValidityResult`: enabled flag, verdict, split boundaries, candidate
  table, check table, and reasons preventing promotion.

## Application Flow

Backtests reserve a chronological tail holdout when the gate is enabled. The
validation/test interval ends before the holdout boundary, and validation
diagnostics purge forward-return observations whose realization date crosses
into the holdout period.

The evaluator constructs the full within-run candidate family after the primary
agent signal, baselines, stress tests, robustness variants, and capacity
diagnostics are complete. The family contains:

- `agent_signal`
- configured baselines
- enabled stress-test variants
- parameter-sensitivity variants
- cost-sensitivity variants

Each candidate receives a one-sided positive-holdout-IC p-value. The evaluator
then applies Benjamini-Hochberg correction across that complete within-run
family and selects `PROMOTE`, `REVIEW`, or `REJECT` from named checks.

The report and machine-readable artifacts serialize the full evidence. They do
not change process exit status and do not imply investment approval.

## Interface Contract

Configuration:

```yaml
experiment:
  validation:
    research_validity:
      enabled: true
      holdout_fraction: 0.15
      fdr_alpha: 0.10
      min_holdout_sharpe: 0.0
      min_holdout_ic: 0.0
      require_positive_return: true
      require_baseline_outperformance: true
      require_walk_forward_stability: true
      require_data_readiness: true
```

Artifact fields:

- CLI JSON includes `research_validity`.
- Reproducibility manifests include top-level `research_validity` and
  `metrics.holdout`.
- Experiment CSV rows include `validity_verdict`, `validity_enabled`,
  `holdout_start`, `holdout_sharpe`, `holdout_ic_mean`,
  `holdout_total_return`, and `agent_fdr_q_value`.
- Markdown reports include a `Research Validity Gate` section.

Verdict contract:

- `PROMOTE`: every required check passes.
- `REJECT`: any core evidence check fails:
  `positive_holdout_sharpe`, `positive_holdout_ic`, `fdr_significant`, or
  `positive_holdout_return`.
- `REVIEW`: core evidence passes, but baseline, walk-forward, or data-readiness
  checks need review.

## Data Model

No schema migration is required. Existing JSON/CSV/Markdown artifacts carry the
new evidence. SQLite registry rows persist the validity payload inside existing
metrics JSON.

## UI / Platform Impact

CLI and internal API runs expose the new fields through existing artifact and
run-report surfaces. There is no new endpoint and no broker or external-system
interaction.

## Observability

Reports and reproducibility manifests record the split boundaries, candidate
family, p-values, q-values, checks, and verdict reasons. Harness records US-026
as a high-risk story because it changes research promotion semantics and proof
expectations.

## Alternatives Considered

1. Verdict over existing validation/test metrics. Rejected because those
   metrics were already used for exploration and interpretation.
2. Three-way chronological split inside every backtest. Selected because it
   creates a useful independent tail gate while preserving the offline workflow.
3. Separately locked holdout dataset. Deferred to a later institutional data
   phase because it needs access control and dataset-release procedures.
