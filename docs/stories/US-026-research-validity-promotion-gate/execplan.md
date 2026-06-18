# Exec Plan

## Goal

Implement an advisory research-validity promotion gate for completed
experiments using an untouched chronological holdout, within-run
Benjamini-Hochberg FDR correction, and explicit economic/data-readiness checks.

## Scope

In scope:

- Parse and validate `experiment.validation.research_validity`.
- Extend backtests to produce train, validation, holdout, compatibility `test`,
  and full metrics.
- Keep validation diagnostics and capacity gates from leaking holdout evidence.
- Build candidate evidence, p-values, Benjamini-Hochberg q-values, checks, and
  verdict selection.
- Persist evidence in reports, CLI JSON, reproducibility manifests, registry
  metrics, and experiment CSV rows.
- Enable the gate in checked-in research demo configs.
- Document the methodology and durable Harness records.

Out of scope:

- Hard-failing runs on `REJECT`.
- Cross-run false-discovery accounting.
- Separately locked holdout datasets.
- Live trading approval, order routing, or compliance workflow.

## Risk Classification

Risk flags:

- Existing behavior: changes validation/test split semantics by adding a
  validation/holdout distinction while retaining `test` compatibility.
- Public contracts: adds report, JSON, manifest, CSV, and registry fields.
- Weak proof: promotion semantics need explicit tests and artifact checks.
- Multi-domain: touches config, backtest, evaluator, reports, manifests, docs,
  and Harness records.

Hard gates:

- Removing or weakening validation requirements would require human approval.

Lane: high-risk.

## Work Phases

1. Add strict configuration parsing and tests.
2. Add leakage-safe chronological holdout metrics.
3. Implement candidate evidence, p-values, Benjamini-Hochberg q-values, checks,
   and verdict selection.
4. Expose the validity result through reports, workflow JSON, manifests, CSV,
   registry metrics, and demo configs.
5. Regenerate deterministic sample reports.
6. Add Harness story/decision documentation.
7. Run full verification and record Harness closeout evidence.

## Stop Conditions

Pause for human confirmation if:

- The verdict would start failing process exit status.
- The gate needs to select or optimize candidates based on holdout performance.
- Cross-run FDR control becomes required inside US-026.
- Verification requires weakening any existing validation gate.
