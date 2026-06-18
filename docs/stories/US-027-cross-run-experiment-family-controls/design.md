# Design

## Domain Model

- `ExperimentFamilyConfig`: optional config metadata with `family_id`,
  `hypothesis_id`, `candidate_id`, and `selection_policy`.
- `ExperimentFamilyRow`: one run manifest converted into family-level evidence.
- `ExperimentFamilyComparison`: filtered family rows, summary, warnings,
  family FDR alpha, and row-level verdicts.

Allowed selection policies are `pre_registered`, `exploratory`, `generated`,
and `manual_selection`.

## Application Flow

Each normal workflow run writes `experiment_family` into its reproducibility
manifest and mirrors those fields into the local SQLite registry.

The `--compare-family` CLI reads a run-bundle directory or single manifest,
optionally filters by `--family-id`, extracts the US-026 `agent_signal`
p-value, applies Benjamini-Hochberg correction across the selected family, and
renders Markdown or JSON evidence.

Family promotion is conservative:

- only `pre_registered` rows can promote;
- a run-level `REJECT` becomes `FAMILY_REJECT`;
- missing p-value evidence becomes `FAMILY_REVIEW`;
- mixed config/data/dataset provenance becomes `FAMILY_REVIEW`;
- family q-value above alpha becomes `FAMILY_REJECT`;
- multiple pre-registered candidates become `FAMILY_REVIEW`.

## Interface Contract

Config:

```yaml
experiment:
  family:
    family_id: synthetic-momentum-low-volatility-v1
    hypothesis_id: momentum-low-risk
    candidate_id: base
    selection_policy: pre_registered
```

CLI:

```bash
python -m quant_research_agent.main --compare-family results/runs --family-id synthetic-momentum-low-volatility-v1
python -m quant_research_agent.main --compare-family results/runs --json --output results/family_comparison.json
```

## Data Model

The SQLite registry migrates existing local databases in place with nullable
columns:

- `experiment_family_id`
- `hypothesis_id`
- `candidate_id`
- `selection_policy`

No managed database or retention policy is added.

## UI / Platform Impact

No browser/API endpoint changes. The CLI exposes the family comparison and the
existing run/manifest/report surfaces carry family metadata.

## Observability

Family comparison artifacts include row verdicts, p-values, family q-values,
summary counts, provenance warnings, and reasons.

## Alternatives Considered

1. Manifest-only comparison. Rejected because the registry would lag the
   methodology.
2. Registry-ledger plus manifest artifact. Selected for local reproducibility.
3. Managed registry/object storage first. Deferred as an infrastructure phase.
