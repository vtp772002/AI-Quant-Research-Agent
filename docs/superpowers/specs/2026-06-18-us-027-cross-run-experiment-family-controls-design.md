# US-027 Cross-Run Experiment-Family Controls Design

Date: 2026-06-18

## Objective

Add a reproducible cross-run experiment-family control layer so a strategy is
not described as promotion-ready merely because one selected run passed the
US-026 within-run validity gate.

US-027 turns a set of related runs into one of three family-level outcomes:

- `FAMILY_PROMOTE`: a run-level `PROMOTE` candidate also survives
  cross-run family false-discovery control.
- `FAMILY_REVIEW`: evidence is incomplete, not comparable, or operationally
  ambiguous enough to require human review.
- `FAMILY_REJECT`: the selected run fails run-level validity or fails
  family-level significance after accounting for the related run family.

The family verdict is advisory. It does not change process exit status and does
not replace human investment, risk, data, or compliance review.

## Problem

US-026 controls false discovery across the candidate family evaluated inside
one run: agent signal, baselines, stress tests, and sensitivity variants.

That does not protect against cross-run experiment shopping. A researcher or
agent can run multiple configurations, prompts, holding periods, universes, or
data snapshots and only promote the best-looking run. Without a durable family
ledger, the platform cannot distinguish a pre-registered candidate from a
selected winner after many attempts.

The remaining product gap is explicitly documented as cross-run
experiment-family controls. US-027 closes that gap for the local Level 1
research platform without introducing managed Postgres, object storage, or
external provider dependencies.

## Approaches Considered

### 1. Manifest-only family comparison

Read `results/runs/*/manifest.json`, group runs by a new family id, and compute
Benjamini-Hochberg q-values across the discovered manifests.

This is simple and avoids database changes, but it leaves the SQLite registry
behind the methodology. The registry is already the local system of record for
runs, so omitting family fields would create two competing truth surfaces.

### 2. Registry-ledger plus manifest artifact

Add optional experiment-family metadata to config, manifest, registry records,
CLI output, and family comparison artifacts. Continue using manifest bundles as
portable evidence, but mirror the family metadata into the local SQLite
registry for durable querying.

Selected because it closes the methodology gap while preserving the current
offline architecture and avoiding managed infrastructure.

### 3. Managed registry/object storage first

Move to Postgres/object storage, then implement family controls there.

Rejected for US-027 because backend deployment is a separate infrastructure
phase. The family model and promotion semantics should be proven locally before
choosing managed storage details.

## Configuration

Add optional `experiment.family` metadata:

```yaml
experiment:
  family:
    family_id: momentum-low-vol-v1
    hypothesis_id: momentum-low-risk
    candidate_id: base
    selection_policy: pre_registered
```

Rules:

- `family_id`, `hypothesis_id`, `candidate_id`, and `selection_policy` are
  optional strings.
- If omitted, the run remains valid but family comparison marks it as
  `FAMILY_REVIEW` when a family verdict would require that metadata.
- Values must be non-empty after stripping whitespace when supplied.
- `selection_policy` must be one of:
  - `pre_registered`
  - `exploratory`
  - `generated`
  - `manual_selection`
- Checked-in demo configs should provide stable family metadata so local
  smokes and generated manifests demonstrate the feature.

## Family Evidence Model

A family comparison row represents one completed run and contains:

- run id
- experiment name
- generated timestamp
- `family_id`
- `hypothesis_id`
- `candidate_id`
- `selection_policy`
- config hash
- git commit and dirty flag
- data source and dataset id
- run-level validity verdict
- agent holdout IC, holdout Sharpe, holdout return, p-value, and q-value from
  US-026
- family q-value computed across all family rows
- family verdict
- reasons
- manifest path

Family p-values use the US-026 `agent_signal` raw p-value from each run. The
Benjamini-Hochberg procedure is applied across all runs in the selected family.

The family selected candidate is determined conservatively:

1. Prefer rows with `selection_policy=pre_registered`.
2. If there is one pre-registered row, evaluate that row as the selected
   candidate.
3. If there are multiple pre-registered rows, all rows are reported and each
   receives a family verdict; the summary says the selected candidate is
   ambiguous.
4. If there are no pre-registered rows, the family can only reach
   `FAMILY_REVIEW` or `FAMILY_REJECT`, not `FAMILY_PROMOTE`.

This keeps US-027 from silently promoting an after-the-fact best run.

## Verdict Rules

Each row receives a family verdict:

- `FAMILY_PROMOTE`
  - `family_id` is present.
  - `selection_policy` is `pre_registered`.
  - run-level US-026 verdict is `PROMOTE`.
  - family q-value is at most the configured family FDR alpha.
  - manifest provenance is comparable enough for the family: no dirty code,
    and the family summary has one config hash, one data source, and one
    dataset id.
- `FAMILY_REJECT`
  - run-level verdict is `REJECT`; or
  - family q-value is greater than the configured family FDR alpha.
- `FAMILY_REVIEW`
  - family metadata is missing.
  - selection policy is not `pre_registered`.
  - run-level verdict is `REVIEW`.
  - provenance differs across family rows.
  - multiple pre-registered candidates exist.
  - p-value evidence is missing.

The comparison summary also emits warnings for mixed configs, commits, dirty
worktrees, data sources, dataset ids, missing family metadata, and ambiguous
pre-registration.

Default family FDR alpha is `0.10`.

## Components

### `config.py`

Add immutable experiment-family configuration types and parse-time validation.
The parser should keep existing configs valid by defaulting family fields to
`None`.

### `reproducibility.py`

Add `experiment_family` metadata to every manifest:

```json
{
  "experiment_family": {
    "family_id": "momentum-low-vol-v1",
    "hypothesis_id": "momentum-low-risk",
    "candidate_id": "base",
    "selection_policy": "pre_registered"
  }
}
```

### `experiment_registry.py`

Add non-destructive SQLite migration logic for family columns on
`experiment_runs`:

- `experiment_family_id TEXT`
- `hypothesis_id TEXT`
- `candidate_id TEXT`
- `selection_policy TEXT`

Existing registries must migrate in place without losing rows.

### `experiment_family.py`

New pure application module that owns:

- manifest discovery
- optional registry row conversion
- run-family row construction
- agent-signal validity evidence extraction
- Benjamini-Hochberg q-values across runs
- row verdict selection
- family summary and warnings
- Markdown and JSON rendering

This module should not run backtests, mutate configs, call external services,
or write reports except through explicit output paths from the CLI.

### `main.py`

Add CLI flags:

- `--compare-family <path>`
- `--family-id <id>`
- `--family-fdr-alpha <float>`

The path can be a run-bundle directory such as `results/runs` or a single
manifest file. Output behavior should match `--compare-runs`: Markdown by
default, JSON when `--json` is set, and optional file write through `--output`.

### Reports and wording

Generated run reports keep the US-026 `Research Validity Gate` section as
run-level evidence. The interpretation text must not imply final promotion
readiness unless family-level control has also been run. US-027's primary
report artifact is the family comparison Markdown/JSON output.

### Docs and Harness

Create a high-risk story packet:

- `docs/stories/US-027-cross-run-experiment-family-controls/overview.md`
- `docs/stories/US-027-cross-run-experiment-family-controls/design.md`
- `docs/stories/US-027-cross-run-experiment-family-controls/execplan.md`
- `docs/stories/US-027-cross-run-experiment-family-controls/validation.md`

Create decision record:

- `docs/decisions/0020-cross-run-experiment-family-controls.md`

Update:

- `README.md`
- `docs/product/ai-quant-research-agent.md`
- `docs/TEST_MATRIX.md`

## Failure Handling

- Missing manifests cause a clear `FileNotFoundError`.
- Unsupported family FDR alpha fails fast; valid range is greater than zero and
  at most `0.25`.
- Missing `agent_signal` validity evidence yields p-value `1.0` and
  `FAMILY_REVIEW`.
- A family with no `family_id` is still renderable, but cannot promote.
- Existing SQLite registries without family columns are migrated in place.
- The family comparison command never runs external providers and never places
  trades.

## Testing Strategy

### Unit

- Parse valid and invalid experiment-family config.
- Validate selection-policy values.
- Extract agent-signal p-values from manifests.
- Apply Benjamini-Hochberg q-values across a family.
- Verify `FAMILY_PROMOTE`, `FAMILY_REVIEW`, and `FAMILY_REJECT` branches.
- Verify provenance warnings for mixed configs, data sources, dataset ids,
  dirty code, and missing metadata.

### Integration

- Write reproducibility manifests containing `experiment_family`.
- Record and read SQLite registry rows with migrated family columns.
- Compare a directory of synthetic manifests and render Markdown/JSON.
- Run CLI `--compare-family` against a temporary run bundle.

### Full verification

- Focused family tests.
- Existing validity/workflow tests.
- Full pytest suite.
- `compileall`.
- `pip check`.
- `git diff --check`.
- Harness story verification.

## Acceptance Criteria

- Checked-in demo configs include stable experiment-family metadata.
- Every new manifest includes `experiment_family`.
- Registry rows persist family fields after non-destructive migration.
- CLI family comparison outputs row-level family q-values and verdicts.
- `FAMILY_PROMOTE` is impossible without pre-registration, run-level
  `PROMOTE`, comparable provenance, and family q-value within alpha.
- README/product docs no longer list cross-run experiment-family controls as a
  missing v1 feature; any remaining limitation is managed/immutable registry
  governance.
- Harness records US-027 as implemented with unit, integration, E2E, and
  platform proof.
