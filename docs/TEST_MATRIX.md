# Test Matrix

This file maps product behavior to proof.

No product behavior has been defined or implemented yet. Do not mark a row
implemented until tests or validation evidence exist.

## Status Values

| Status | Meaning |
| --- | --- |
| planned | Accepted as intended behavior, not implemented |
| in_progress | Actively being built |
| implemented | Implemented and proof exists |
| changed | Contract changed after earlier implementation |
| retired | No longer part of the product contract |

## Matrix

| Story | Contract | Unit | Integration | E2E | Platform | Status | Evidence |
| --- | --- | --- | --- | --- | --- | --- | --- |
| US-001 | Core AI quant research workflow | yes | yes | no | yes | implemented | `.venv/bin/python -m pytest`; `.venv/bin/python -m quant_research_agent.main --config configs/base.yaml --json` |
| US-002 | Real-data config and baseline comparison | yes | yes | no | yes | implemented | `.venv/bin/python -m pytest`; CLI smoke for `configs/base.yaml` and `configs/yahoo_nasdaq_demo.yaml` |
| US-026 | Research validity and promotion gate | yes | yes | yes | yes | implemented | `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 .venv/bin/python -m pytest tests/test_research_validity.py tests/test_workflow.py -q`; `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 .venv/bin/python -m pytest -q`; `.venv/bin/python -m compileall -q src tests`; `.venv/bin/python -m pip check`; CLI smokes for base, point-in-time synthetic, institutional snapshot, and Yahoo demo configs |

## Evidence Rules

- Unit proof covers pure domain and application rules.
- Integration proof covers backend enforcement, data integrity, provider
  behavior, jobs, or service contracts.
- E2E proof covers user-visible browser flows.
- Platform proof covers only shell, deployment, mobile, desktop, or runtime
  behavior that cannot be proven in lower layers.
- A story can be implemented without every proof column if the story packet
  explains why.
