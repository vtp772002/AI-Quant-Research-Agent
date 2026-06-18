# Validation

## Proof Strategy

US-028 is complete when registry export writes governance artifacts, the
verifier accepts an untouched pack, deterministic tests prove tamper detection,
and CLI smoke proves export plus verification works without a managed storage
service.

## Test Plan

| Layer | Cases |
| --- | --- |
| Unit | Hash-chain rows match canonical registry records; invalid owner/retention fails closed. |
| Integration | Registry export writes NDJSON, SQL, governance manifest, hash chain, retention metadata, family evidence, and verifier status. |
| E2E | CLI `--export-registry` writes governance paths and CLI `--verify-registry-governance` exits successfully for the generated pack. |
| Platform | Local filesystem artifact generation on the Python runtime. |
| Performance | Export remains bounded by `limit`; no performance benchmark needed for this artifact-first slice. |
| Logs/Audit | Harness story, decision, matrix, and trace records capture the governance decision and proof. |

## Fixtures

- Temporary SQLite registry populated by deterministic manifest fixtures.
- Tampered NDJSON and hash-chain files for verifier failure cases.

## Commands

```text
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 .venv/bin/python -m pytest tests/test_production_extensions.py -q
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 .venv/bin/python -m pytest -q
.venv/bin/python -m compileall -q src tests
.venv/bin/python -m pip check
.venv/bin/python -m quant_research_agent.main --export-registry /tmp/aiqra-registry-governance-smoke --registry-path results/experiments.sqlite --registry-owner research-ops --registry-retention-days 730
.venv/bin/python -m quant_research_agent.main --verify-registry-governance /tmp/aiqra-registry-governance-smoke
```

## Acceptance Evidence

- `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 .venv/bin/python -m pytest tests/test_production_extensions.py -q` passed: 11 tests.
- `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 .venv/bin/python -m pytest -q` passed: 132 tests.
- `.venv/bin/python -m compileall -q src tests` passed.
- `.venv/bin/python -m pip check` passed: no broken requirements.
- `.venv/bin/python -m quant_research_agent.main --export-registry /tmp/aiqra-registry-governance-smoke --registry-path results/experiments.sqlite --registry-owner research-ops --registry-retention-days 730` passed and exported 54 rows with governance manifest and hash-chain paths.
- `.venv/bin/python -m quant_research_agent.main --verify-registry-governance /tmp/aiqra-registry-governance-smoke` passed with `valid: true` and no errors.
