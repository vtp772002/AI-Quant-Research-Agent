# Validation

## Proof Strategy

The story is done when all new extension modules have deterministic unit or
integration coverage, existing tests still pass, and CLI smoke commands prove
the user-facing paths work without external providers or brokers.

## Test Plan

| Layer | Cases |
| --- | --- |
| Unit | Paper extraction, registry export, vendor snapshot loading, execution simulation participation gates. |
| Integration | Batch runner executes a temporary config and writes comparison artifacts. |
| E2E | Full pytest suite remains green. |
| Platform | CLI smokes for batch, registry export, paper extraction, and execution simulation. |
| Safety | Tests and docs confirm execution simulation has no broker side effects. |

## Fixtures

- Temporary synthetic config.
- Temporary registry populated from a reproducibility manifest.
- Temporary vendor snapshot CSV.
- Inline paper/blog text.
- Inline as-of signal rows.

## Commands

```text
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python -m pytest tests/test_production_extensions.py -q
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python -m pytest -q
python -m compileall -q src tests
git diff --check
PYTHONPATH=src python -m quant_research_agent.main --paper-to-alpha <paper> --template-output <output>
PYTHONPATH=src python -m quant_research_agent.main --export-registry <dir> --registry-path results/experiments.sqlite
PYTHONPATH=src python -m quant_research_agent.main --simulate-execution --config configs/base.yaml --as-of-date 2022-12-30
```

## Acceptance Evidence

- `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python -m pytest tests/test_production_extensions.py -q` passed 6/6.
- `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python -m pytest -q` passed 22/22.
- `python -m compileall -q src tests` passed.
- `git diff --check` passed.
- `PYTHONPATH=src python -m quant_research_agent.main --paper-to-alpha <tmp>/paper.md --template-output <tmp>/template.yaml` passed and wrote a draft YAML template.
- `PYTHONPATH=src python -m quant_research_agent.main --export-registry <tmp>/export --registry-path results/experiments.sqlite` passed and wrote NDJSON, manifest, and Postgres handoff SQL for 9 current registry rows.
- `PYTHONPATH=src python -m quant_research_agent.main --simulate-execution --config configs/base.yaml --as-of-date 2022-12-30 --execution-output <tmp>/execution.json` passed and produced a broker-free blocked-order simulation with no trade placement.
- `PYTHONPATH=src python -m quant_research_agent.main --run-batch configs/base.yaml --batch-output-dir <tmp>/batch --limit 1` passed and wrote batch summary plus comparison artifacts; tracked runtime artifacts touched by the smoke were restored before commit.
