# US-026 Research Validity and Promotion Gate Design

Date: 2026-06-18

## Objective

Add a deterministic research-validity gate that turns each completed experiment
into one of three decisions:

- `PROMOTE`: evidence is strong enough for the next research stage.
- `REVIEW`: core holdout evidence is positive, but one or more operational or
  comparative requirements need human review.
- `REJECT`: core holdout evidence is statistically or economically inadequate.

The gate is advisory. A rejected experiment still completes normally and writes
its report, JSON payload, reproducibility manifest, registry row, and experiment
CSV rows.

## Problem

The current workflow has chronological train/test and walk-forward diagnostics,
but it does not reserve an untouched final period or correct the significance
claim for the number of strategies and variants evaluated. This makes the
system useful for exploration but too permissive for promotion decisions.

US-026 must prevent a good-looking exploratory result from being described as
promotion-ready unless it survives:

1. An untouched chronological holdout.
2. Multiple-hypothesis correction.
3. Economic, baseline, stability, and data-readiness gates.

## Approaches Considered

### 1. Add a verdict over existing test metrics

This is the smallest change, but the existing test period is already used by
walk-forward, robustness, baseline, and report interpretation. It would produce
a verdict without a genuinely independent final evaluation period.

Rejected because it improves presentation more than research validity.

### 2. Add a three-way chronological split inside every backtest

Use the existing `train_fraction` as the training boundary and reserve a
configurable tail fraction as holdout. The observations between those two
boundaries form validation. Candidate configuration and exploratory comparisons
use train/validation evidence; promotion uses holdout evidence only.

Selected because it gives a useful independent gate while preserving the
current deterministic, offline workflow and data adapters.

### 3. Require a separately versioned holdout dataset

This is the strongest institutional boundary because the holdout can be
physically unavailable during development. It also requires dataset lifecycle,
access control, and release procedures that the current Level 1 platform does
not have.

Deferred to the institutional data phase. US-026 will keep the interfaces
compatible with a later separately locked holdout dataset.

## Configuration

Add `experiment.validation.research_validity`:

```yaml
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

Rules:

- `holdout_fraction` must be between `0.05` and `0.40`.
- `train_fraction + holdout_fraction` must be at most `0.90`, preserving at
  least 10% of observations for validation.
- `fdr_alpha` must be greater than zero and at most `0.25`.
- Minimum Sharpe and IC thresholds must be finite.
- Existing configs without `research_validity` remain valid and receive an
  advisory `REVIEW` result with `enabled=false`; checked-in demonstration
  configs explicitly enable the gate.

## Chronological Data Split

Each `BacktestResult` will expose:

- `train`: observations through the existing training boundary.
- `validation`: observations after training and before the holdout boundary.
- `holdout`: the final configured fraction of observations.
- `test`: compatibility alias for `validation`.
- `full`: all observations.

The final holdout starts at the first observation in the reserved tail. No
holdout metric is used to construct factors, choose factor signs, choose
holding period, choose quantile, choose costs, or choose the primary agent
signal.

The project does not currently perform automatic model selection. The primary
candidate remains the pre-registered `agent_signal` from configuration.
Baselines, stress tests, parameter sensitivity, and cost sensitivity are
evaluated as the multiple-testing family; they do not replace the primary
candidate based on holdout performance.

## Multiple-Hypothesis Control

The hypothesis family contains:

- `agent_signal`.
- Configured baselines.
- Enabled stress-test variants.
- Parameter-sensitivity variants.
- Cost-sensitivity variants.

For each candidate, calculate a one-sided p-value for positive holdout IC from
the holdout IC t-statistic using the standard normal survival function:

```text
p = 0.5 * erfc(ic_tstat / sqrt(2))
```

Apply the Benjamini-Hochberg procedure across the complete family. Report both
raw p-values and monotonic adjusted q-values. The agent signal passes the
statistical gate only when:

```text
agent_holdout_ic > min_holdout_ic
and agent_q_value <= fdr_alpha
```

This correction controls false discovery rate for the candidate family in one
run. It does not claim protection across unrecorded manual experiments or
separate historical runs.

## Promotion Criteria

The validity evaluator emits one named check per requirement:

1. `positive_holdout_sharpe`
   - Holdout Sharpe is greater than `min_holdout_sharpe`.
2. `positive_holdout_ic`
   - Holdout IC is greater than `min_holdout_ic`.
3. `fdr_significant`
   - Agent q-value is at most `fdr_alpha`.
4. `positive_holdout_return`
   - Net holdout total return is positive when required.
5. `beats_best_baseline`
   - Agent holdout Sharpe is at least the best configured baseline holdout
     Sharpe when required.
6. `walk_forward_stable`
   - At least half of agent walk-forward windows have non-negative Sharpe when
     required.
7. `data_ready`
   - Data is point-in-time, survivorship-bias-free, and corporate-action
     adjusted when required.

Verdict rules:

- `PROMOTE`: every enabled check passes.
- `REJECT`: any core evidence check fails:
  `positive_holdout_sharpe`, `positive_holdout_ic`, `fdr_significant`, or
  `positive_holdout_return`.
- `REVIEW`: all core evidence checks pass, but one or more comparative,
  stability, or data-readiness checks fail.

Disabled optional checks are recorded as not required and do not fail the
verdict.

## Components

### `config.py`

Add immutable configuration types and parse-time validation for the research
validity settings.

### `backtest/engine.py`

Add the holdout boundary and produce train, validation, holdout, compatibility
test, and full metrics from the same realized return series.

### `agents/research_validity.py`

Own:

- Candidate-family construction.
- One-sided IC p-values.
- Benjamini-Hochberg q-values.
- Promotion checks.
- Verdict selection.
- Human-readable reasons.

This module receives completed backtest and diagnostic objects. It does not
load data, construct signals, mutate configs, or write artifacts.

### `agents/evaluator_agent.py`

Run the validity evaluator after baseline, stress, robustness, and capacity
diagnostics are complete. Add the result to `ResearchRunResult`.

### `agents/report_agent.py`

Add a `Research Validity Gate` section containing:

- Verdict and whether the gate is enabled.
- Train, validation, and holdout boundaries.
- Agent holdout metrics.
- Candidate p-value/q-value table.
- Requirement-by-requirement pass/fail table.
- Explicit reasons preventing promotion.

The report must not use language implying promotion when the verdict is
`REVIEW` or `REJECT`.

### Workflow and reproducibility surfaces

Add the complete validity payload to:

- CLI JSON.
- Reproducibility manifest.
- SQLite registry `metrics_json`.

Add summary fields to experiment CSV rows:

- `validity_verdict`
- `validity_enabled`
- `holdout_start`
- `holdout_sharpe`
- `holdout_ic_mean`
- `holdout_total_return`
- `agent_fdr_q_value`

No new API endpoint is required. Existing run and report endpoints expose the
new data through current artifacts.

## Failure Handling

- Too few observations for train/validation/holdout is a configuration/runtime
  error and fails before artifact promotion claims are written.
- A candidate without enough holdout IC observations receives p-value and
  q-value `1.0`, causing the statistical gate to fail conservatively.
- Missing baselines skip `beats_best_baseline` with a recorded
  `not_applicable` status.
- An enabled data-readiness requirement fails closed when any required
  provenance flag is false.
- The validity verdict never changes the process exit code.

## Testing Strategy

### Unit

- Parse valid and invalid research-validity configuration.
- Verify chronological split boundaries and that holdout is disjoint from
  train and validation.
- Verify one-sided p-values.
- Verify Benjamini-Hochberg ordering, monotonic q-values, and deterministic
  results.
- Verify `PROMOTE`, `REVIEW`, and `REJECT` decision paths.
- Verify insufficient holdout evidence fails conservatively.

### Isolation

- Construct two runs with identical train/validation observations but different
  holdout returns.
- Confirm the primary candidate remains `agent_signal` and all pre-holdout
  boundaries and validation metrics remain identical.
- Confirm only holdout evidence and the final verdict change.

### Integration

- Workflow result contains validity diagnostics.
- Markdown report contains the validity section and no unsupported promotion
  language.
- CLI JSON and reproducibility manifest contain the same verdict and checks.
- Experiment CSV persists validity summary fields.

### Regression

- Existing deterministic synthetic, point-in-time, snapshot, LLM, API, and
  production-extension tests remain green.
- Checked-in base, Yahoo, point-in-time, and institutional snapshot configs run
  with the gate enabled.

## Exit Criteria

US-026 is complete only when:

- The gate produces deterministic `PROMOTE`, `REVIEW`, or `REJECT` outcomes.
- Holdout observations are chronologically disjoint and excluded from
  development metrics.
- The full candidate family receives Benjamini-Hochberg q-values.
- Report, JSON, manifest, registry payload, and CSV surfaces agree.
- Tests demonstrate holdout isolation and all verdict branches.
- Full pytest, compileall, diff check, and CLI smoke commands pass.
- Harness story verification records current evidence.

## Explicit Non-Goals

- Failing CLI or API requests because a signal is rejected.
- Automatically replacing the configured agent signal with the best holdout
  performer.
- Claiming investment merit from synthetic or Yahoo data.
- A separately access-controlled holdout dataset.
- Cross-run false-discovery accounting.
- Paper trading, broker integration, or order execution.
