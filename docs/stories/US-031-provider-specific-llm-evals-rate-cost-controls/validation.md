# Validation

## Proof Strategy

Use deterministic tests and fixture-provider CLI smoke to prove the control and
eval contract without network credentials.

## Test Plan

| Layer | Cases |
| --- | --- |
| Unit | Token/cost controls reject over-budget requests and write rejection artifacts. |
| Integration | Fixture provider writes prompt, response, transcript, controls, eval, ideas, configs, and review queue. |
| E2E | CLI fixture smoke passes with request and cost limits. |
| Platform | Full pytest, compileall, pip check, git diff check, and Harness story verify. |
| Performance | Not applicable; one provider request per CLI operation. |
| Logs/Audit | Provider transcript records controls and eval paths without secrets. |

## Fixtures

- Test fixture idea payloads in `tests/test_research_agents.py`.
- CLI smoke fixture generated under `/tmp` during validation.

## Commands

```text
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python -m pytest tests/test_research_agents.py -q
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python -m pytest -q
python -m compileall src tests
.venv/bin/python -m pip check
git diff --check
PYTHONPATH=src python -m quant_research_agent.main --generate-ideas --config configs/base.yaml --llm-provider fixture --llm-fixture <tmp>/fixture.json --ideas-output-dir <tmp>/ideas --n 1 --llm-max-requests 1 --llm-max-estimated-cost-usd 1.0 --llm-input-cost-per-1k 0.001 --llm-output-cost-per-1k 0.001
scripts/bin/harness-cli story verify US-031
```

## Acceptance Evidence

- `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python -m pytest tests/test_research_agents.py -q`
  passed: 16 passed.
- `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python -m pytest -q` passed: 150 passed.
- `python -m compileall src tests` passed.
- `.venv/bin/python -m pip check` passed: no broken requirements found.
- `git diff --check` passed.
- Global `python -m pip check` was also attempted and failed on unrelated
  machine-level package conflicts outside this project environment; `.venv`
  remains the project proof interpreter.
- Fixture-provider CLI smoke with request/cost controls passed and returned
  `controls_path`, `eval_path`, prompt, response, transcript, config, ideas,
  and review queue paths.
- CLI smoke controls artifact status was `passed` with estimated cost
  `0.016207`; eval artifact status was `passed` with checks:
  `requested_idea_count`, `schema_fields_present`, `allowed_factor_boundary`,
  `unique_names`, `warnings_present`, and `confidence_range`.
