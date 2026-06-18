# Exec Plan

## Goal

Add cross-run experiment-family controls over related manifests and registry
rows.

## Scope

In scope:

- Config metadata for experiment families.
- Manifest and registry persistence.
- Non-destructive registry migration.
- Family-level Benjamini-Hochberg correction across runs.
- CLI Markdown/JSON family comparison.
- Demo config metadata.
- Product docs, decision record, and Harness proof.

Out of scope:

- Managed registry deployment.
- Immutable audit governance.
- Multi-user family authorization.
- Any trading or broker integration.

## Risk Classification

Risk flags:

- Existing behavior: changes promotion semantics by adding a family layer.
- Public contracts: adds config, manifest, registry, and CLI fields.
- Weak proof: methodology requires targeted tests.
- Multi-domain: touches config, manifests, registry, CLI, docs, and reports.

Lane: high-risk.

## Work Phases

1. Add family config parsing.
2. Persist family metadata to manifests and registry.
3. Evaluate cross-run family evidence.
4. Expose CLI and demo metadata.
5. Update product and Harness docs.
6. Verify, merge, and push.

## Stop Conditions

Pause for human confirmation if:

- The family gate would hard-fail normal runs.
- The implementation needs managed storage or external services.
- The design starts auto-selecting best runs after search.
- Validation requirements need to be weakened.
