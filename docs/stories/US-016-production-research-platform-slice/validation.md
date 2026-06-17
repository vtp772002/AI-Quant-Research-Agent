# Validation

## Proof Strategy

The story is done when existing CLI behavior still passes and the new production
research interfaces are covered by deterministic tests plus smoke commands.

## Test Plan

| Layer | Cases |
| --- | --- |
| Unit | SQLite registry create/upsert/read, as-of signal generation without future dates. |
| Integration | FastAPI health, metrics, as-of signal, and missing-run response contract. |
| E2E | Existing CLI E2E remains green. |
| Platform | Dockerfile and compose config exist; CI runs tests and CLI smoke. |
| Performance | No benchmark claim in this slice. |
| Logs/Audit | API request middleware emits structured operational logs. |

## Fixtures

- Deterministic synthetic OHLCV data.
- Temporary YAML configs and temporary SQLite registry paths.

## Commands

```text
python -m pytest
python -m quant_research_agent.main --config configs/base.yaml --json
python -m quant_research_agent.api
```

## Acceptance Evidence

- `python -m compileall -q src tests` passed.
- `git diff --check` passed.
- `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python -m pytest` passed 11/11.
- `PYTHONPATH=src python -m quant_research_agent.main --config configs/base.yaml --json` passed and wrote a SQLite registry row at `results/experiments.sqlite`.
- API route smoke confirmed `/health`, `/metrics`, `/experiments/run`, `/experiments`, `/experiments/{run_id}`, `/reports/{run_id}`, `/signals/latest`, and `/signals/as-of`.
- `docker build -t aiqra-production-slice:test .` passed.
- `docker compose config` and `docker-compose config` could not run on this machine because the Compose plugin/legacy binary is unavailable.
