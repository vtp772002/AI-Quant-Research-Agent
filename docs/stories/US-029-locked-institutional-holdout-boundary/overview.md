# Overview

## Current Behavior

US-026 reserves a chronological holdout tail and uses holdout-period evidence
for the Research Validity Gate. US-027 adds cross-run experiment-family
controls, and US-028 adds immutable registry governance packs.

The holdout is still derived from the same configured data range at runtime. It
is not separately declared, hashed, or provenance-checked as an institutional
holdout boundary. A mutated dataset, changed date range, or incomplete holdout
coverage could silently weaken promotion evidence.

## Target Behavior

Research validity can require a locked institutional holdout manifest. When
enabled, the workflow validates the realized holdout against the manifest before
promotion evidence is written:

- manifest schema version is recognized;
- manifest content hash matches;
- expected holdout start/end match the realized backtest holdout window;
- expected symbols match the realized holdout symbols;
- expected minimum row count and row count match when configured;
- locked holdout evidence is written to CLI JSON, reproducibility manifest,
  registry metrics, and report text.

The boundary is fail-closed. A configured locked holdout mismatch raises an
error before the run can produce promotion artifacts.

## Affected Users

- Quant researcher relying on holdout evidence for promotion decisions.
- Research operator reviewing whether a candidate used locked institutional
  holdout data.
- Future developer adding managed data-store or access-control enforcement.

## Affected Product Docs

- `README.md`
- `docs/product/ai-quant-research-agent.md`
- `docs/TEST_MATRIX.md`

## Non-Goals

- Provisioning a managed data warehouse.
- Enforcing multi-user data access controls.
- Creating a separate broker, execution, or compliance workflow.
- Fetching live vendor data.
- Replacing the existing chronological holdout split.
