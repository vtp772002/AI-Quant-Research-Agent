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
| US-027 | Cross-run experiment-family controls | yes | yes | yes | yes | implemented | `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 .venv/bin/python -m pytest tests/test_experiment_family.py tests/test_workflow.py tests/test_production_research_platform.py -q`; `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 .venv/bin/python -m pytest -q`; `.venv/bin/python -m compileall -q src tests`; `.venv/bin/python -m pip check`; `python -m quant_research_agent.main --compare-family results/runs --json` |
| US-028 | Managed immutable registry governance pack | yes | yes | yes | yes | implemented | `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 .venv/bin/python -m pytest tests/test_production_extensions.py -q`; `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 .venv/bin/python -m pytest -q`; `.venv/bin/python -m compileall -q src tests`; `.venv/bin/python -m pip check`; CLI export and verify smokes for registry governance pack |
| US-029 | Locked institutional holdout dataset boundary | yes | yes | yes | yes | implemented | `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 .venv/bin/python -m pytest tests/test_locked_holdout.py tests/test_workflow.py -q`; `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 .venv/bin/python -m pytest -q`; `.venv/bin/python -m compileall -q src tests`; `.venv/bin/python -m pip check`; institutional snapshot CLI smoke with locked holdout evidence |
| US-030 | Managed registry deployment adapter | yes | yes | yes | yes | implemented | `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 .venv/bin/python -m pytest tests/test_managed_registry.py tests/test_production_extensions.py -q`; `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 .venv/bin/python -m pytest -q`; `.venv/bin/python -m compileall -q src tests`; `.venv/bin/python -m pip check`; CLI export/stage/verify managed registry smoke |
| US-031 | Provider-specific LLM evals and cost controls | yes | yes | yes | yes | implemented | `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python -m pytest tests/test_research_agents.py -q`; `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python -m pytest -q`; `python -m compileall src tests`; `.venv/bin/python -m pip check`; fixture-provider CLI smoke with request/cost controls and eval artifacts |
| US-032 | Two-person family promotion authorization | yes | yes | yes | yes | implemented | Focused promotion/platform tests passed 24/24; full pytest passed 161/161; compileall, `.venv` pip check, and `git diff --check` passed; CLI HMAC recommend/list/decide/verify smoke produced a valid 2-event ledger; API role/fingerprint/secret smoke passed |
| US-033 | Durable research job queue and lease-based worker | yes | yes | yes | yes | implemented | Queue/platform verification 29/29; full pytest 175/175; queue suite 13/13; compileall, pip check, diff check, real CLI enqueue/list/worker/show smoke, and Harness story verify passed |
| US-034 | Managed local research worker supervision | yes | yes | yes | yes | implemented | Worker queue suite 16/16; queue/platform verification 32/32; full pytest 178/178; compileall, pip check, diff check, real CLI enqueue/worker-loop smoke, daily script enqueue/worker smoke, Harness story verify, and decision verify passed |

## Evidence Rules

- Unit proof covers pure domain and application rules.
- Integration proof covers backend enforcement, data integrity, provider
  behavior, jobs, or service contracts.
- E2E proof covers user-visible browser flows.
- Platform proof covers only shell, deployment, mobile, desktop, or runtime
  behavior that cannot be proven in lower layers.
- A story can be implemented without every proof column if the story packet
  explains why.
