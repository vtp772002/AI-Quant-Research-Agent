# Validation

## Proof Strategy

The story is done when the agentic research loop is deterministic, validates
generated ideas, writes runnable configs, critiques manifests, emits paper v2
payloads, and preserves the full existing test suite.

## Test Plan

| Layer | Cases |
| --- | --- |
| Unit | Idea validation, deterministic idea generation, research memory, critic, paper-to-alpha v2. |
| Integration | Config generation from ideas and mine-alpha output artifacts. |
| E2E | Full pytest suite remains green. |
| Platform | CLI smokes for idea generation, critique, paper v2, and mine-alpha. |
| Safety | Unknown factors and unsafe payloads are rejected before config generation. |

## Fixtures

- Temporary base config.
- Temporary registry populated from reproducibility manifests.
- Temporary manifest JSON.
- Inline paper/blog text.

## Commands

```text
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python -m pytest tests/test_research_agents.py -q
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python -m pytest -q
python -m compileall -q src tests
git diff --check
PYTHONPATH=src python -m quant_research_agent.main --generate-ideas --config configs/base.yaml --n 2 --ideas-output-dir <tmp>/ideas
PYTHONPATH=src python -m quant_research_agent.main --critique-run results/runs/<run_id>/manifest.json
PYTHONPATH=src python -m quant_research_agent.main --paper-to-alpha-v2 <tmp>/paper.md --template-output <tmp>/paper_alpha_v2.json
PYTHONPATH=src python -m quant_research_agent.main --mine-alpha --config configs/base.yaml --n 2 --mine-output-dir <tmp>/mine
```

## Acceptance Evidence

- `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python -m pytest tests/test_research_agents.py -q` passed 6/6.
- `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python -m pytest -q` passed 28/28.
- `python -m compileall -q src tests` passed.
- `git diff --check` passed.
- `PYTHONPATH=src python -m quant_research_agent.main --generate-ideas --config configs/base.yaml --n 2 --ideas-output-dir <tmp>/ideas` passed and wrote `ideas.json` plus two config variants.
- `PYTHONPATH=src python -m quant_research_agent.main --critique-run results/runs/<run_id>/manifest.json` passed and returned a reject/accept verdict plus follow-up idea.
- `PYTHONPATH=src python -m quant_research_agent.main --paper-to-alpha-v2 <tmp>/paper.md --template-output <tmp>/paper_alpha_v2.json` passed and returned validation, unsupported concepts, and bias warnings.
- `PYTHONPATH=src python -m quant_research_agent.main --mine-alpha --config configs/base.yaml --n 2 --mine-output-dir <tmp>/mine` passed and wrote idea configs without running batch.
