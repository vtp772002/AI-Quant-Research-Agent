# Validation

## Proof Strategy

The story is done when fixture provider output can generate validated configs,
external command execution is blocked by default, transcripts are written, and
the full test suite remains green.

## Test Plan

| Layer | Cases |
| --- | --- |
| Unit | Prompt payload, fixture provider, command provider guard. |
| Integration | `generate_idea_configs_with_provider` writes configs plus transcript artifacts. |
| E2E | Full pytest suite remains green. |
| Platform | CLI smoke for `--generate-ideas --llm-provider fixture`. |
| Safety | Command provider requires explicit external allowance. |

## Commands

```text
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python -m pytest tests/test_research_agents.py -q
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python -m pytest -q
python -m compileall -q src tests
git diff --check
PYTHONPATH=src python -m quant_research_agent.main --generate-ideas --config configs/base.yaml --llm-provider fixture --llm-fixture <fixture> --ideas-output-dir <tmp>/ideas
```

## Acceptance Evidence

- `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python -m pytest tests/test_research_agents.py -q` passed 8/8.
- `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python -m pytest -q` passed 30/30.
- `python -m compileall -q src tests` passed.
- `git diff --check` passed.
- `PYTHONPATH=src python -m quant_research_agent.main --generate-ideas --config configs/base.yaml --llm-provider fixture --llm-fixture <tmp>/fixture.json --ideas-output-dir <tmp>/ideas` passed and wrote config, prompt, response, and transcript artifacts.
