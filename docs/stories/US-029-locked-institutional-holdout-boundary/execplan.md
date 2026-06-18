# Exec Plan

## Goal

Add a fail-closed locked holdout manifest boundary so research-validity
promotion evidence can prove which institutional holdout slice was used.

## Scope

In scope:

- Parse locked holdout config under research validity.
- Validate manifest schema, hash, date range, symbols, and row counts.
- Attach locked holdout evidence to workflow result.
- Write evidence to report, CLI JSON, reproducibility manifest, registry JSON,
  product docs, story packet, decision record, and test matrix.
- Add deterministic tests for success and fail-closed mismatch cases.

Out of scope:

- Managed data warehouse or object-lock storage.
- Multi-user authorization.
- Live vendor API or credentials.
- Trading or broker execution.
- Changing the existing chronological holdout math.

## Risk Classification

Risk flags:

- Data model: promotion evidence changes.
- Audit/security: locked holdout provenance and fail-closed behavior.
- Public contracts: config, CLI JSON, manifest, and report surfaces.
- Existing behavior: research-validity workflow.
- Weak proof: methodology gate requires new targeted tests.

Hard gates:

- Audit/security.
- Removing or weakening validation requirements is forbidden.

Lane: high-risk.

## Work Phases

1. Discovery: inspect config, snapshot, workflow, reproducibility, report, and
   validity tests.
2. Design: define local manifest contract and fail-closed evidence path.
3. Implementation: add config, validation module, workflow plumbing, report and
   manifest output.
4. Verification: targeted tests, full pytest, compileall, pip check, git diff
   check, CLI smoke.
5. Harness update: story status/evidence, decision row, matrix, detailed trace.
6. Commit and push to `origin/main`.

## Stop Conditions

Pause for human confirmation if:

- The implementation requires real vendor credentials or cloud storage.
- Existing research-validity gates would need to be weakened.
- A destructive migration or data deletion appears necessary.
- The scope expands into broker/trading behavior.
