# Overview

## Current Behavior

The research workflow has deterministic backtests, chronological validation,
walk-forward diagnostics, robustness checks, capacity diagnostics, baselines,
reproducibility manifests, and registry rows. Before US-026, promotion readiness
was still inferred from validation-period metrics that were also used for
exploration and report interpretation.

That made the platform useful for research iteration, but it did not reserve a
final untouched period or correct the evidence claim for the number of
strategies and variants evaluated in one run.

## Target Behavior

Each completed run can emit an advisory research-validity verdict:

- `PROMOTE`: configured holdout, FDR, economic, baseline, stability, and
  data-readiness checks pass.
- `REVIEW`: core holdout evidence passes, but comparative, stability, or data
  readiness needs human review.
- `REJECT`: core statistical or economic holdout evidence fails.

The verdict is evidence, not process control. A `REJECT` result still completes
the run and writes the Markdown report, CLI JSON payload, reproducibility
manifest, experiment CSV row, and registry metrics.

## Affected Users

- Quant researcher deciding whether a signal is ready for the next research
  stage.
- Operator reviewing generated or manually configured experiment evidence.
- Future developer extending institutional data controls or cross-run
  experiment accounting.

## Affected Product Docs

- `README.md`
- `docs/product/ai-quant-research-agent.md`
- `docs/TEST_MATRIX.md`

## Non-Goals

- Investment approval or trading approval.
- Process failure when a signal receives `REJECT`.
- Cross-run false-discovery accounting across unrecorded manual experiments.
- Separately access-controlled holdout datasets.
- Broker execution, order routing, or compliance workflow.
