# AI Quant Research Agent

From hypothesis to alpha signal, backtest, and research report.

This project explores how agentic workflows can assist quantitative researchers
by generating alpha hypotheses, converting them into executable factor signals,
running long-short backtests, and producing research reports with statistical
validation.

## Research Goal

Can an AI agent accelerate the alpha research workflow without hiding the
statistical evidence a quant researcher needs to judge a signal?

## System Design

- `data`: load deterministic synthetic OHLCV data, Yahoo Finance OHLCV data, or
  validated CSV snapshot data with manifest provenance.
- `factors`: compute a reusable factor library with 20+ price, momentum,
  reversal, volatility, volume, and liquidity factors.
- `agents`: create a hypothesis, translate selected factors into a ranked
  signal, compare it with baselines, evaluate the experiment, and write a
  report.
- `backtest`: run a dollar-neutral top/bottom quantile long-short portfolio.
- `api`: expose an internal FastAPI service for health checks, run execution,
  run lookup, report lookup, and as-of signal generation.
- `reports` and `results`: store generated research artifacts.

## Quick Start

```bash
python3 -m venv .venv
. .venv/bin/activate
pip install -e ".[dev]"
python -m quant_research_agent.main --config configs/base.yaml
```

The spec-compatible entrypoint also works:

```bash
python -m src.main --config configs/base.yaml
```

Run the internal research API:

```bash
python -m quant_research_agent.api
curl http://127.0.0.1:8000/health
curl "http://127.0.0.1:8000/signals/as-of?config_path=configs/base.yaml&date=2022-12-30"
```

Compare generated runs:

```bash
python -m quant_research_agent.main --compare-runs results/runs --comparison-metric sharpe --limit 10
python -m quant_research_agent.main --compare-runs results/runs --json --output results/run_comparison.json
```

Run a local production-like container:

```bash
docker compose up --build api
```

## Default Experiment

The default config tests this hypothesis:

```text
Assets with stronger recent momentum and lower realized risk should outperform
over the next 5 trading days.
```

Signal:

```text
rank(momentum_20d) + rank(momentum_60d)
- rank(volatility_20d) - rank(drawdown_20d)
```

Backtest:

```text
Long top 20%, short bottom 20%, rebalance every 5 trading days.
```

Baselines:

```text
momentum_20d_only
low_volatility_only
reversal_5d_only
random_cross_section
```

Real-data demo:

```bash
python -m quant_research_agent.main --config configs/yahoo_nasdaq_demo.yaml
```

Point-in-time universe demo:

```bash
python -m quant_research_agent.main --config configs/point_in_time_synthetic_demo.yaml
```

Golden snapshot demo:

```bash
python -m quant_research_agent.main --config configs/institutional_snapshot_demo.yaml
```

## Metrics

The research report includes:

- IC mean, standard deviation, t-stat, and hit rate.
- Sharpe ratio.
- Max drawdown.
- Average turnover.
- Total long-short return.
- Chronological train/test split.
- Baseline comparison on test-period metrics.
- Walk-forward validation across multiple chronological windows.
- Factor coverage and redundancy diagnostics for selected exposures.
- Neutralization and liquidity stress tests for the agent signal.
- Data integrity diagnostics for source quality, panel coverage, and
  institutional-readiness assumptions.
- Base, spread, and liquidity-sensitive market-impact transaction costs.
- Borrow fee, shortability constraints, and date-aware locate availability
  history for short-leg feasibility.
- Point-in-time CSV universe membership adapter for survivorship-safe research
  interfaces.
- Bootstrap confidence intervals, parameter sensitivity grids, and cost
  sensitivity diagnostics for overfit and robustness review.
- Capacity curve, concentration, and trade participation diagnostics for AUM
  feasibility review.
- CSV snapshot manifest validation for dataset provenance, SHA-256 content
  checks, row counts, symbol sets, date ranges, and institutional data flags.
- Per-run reproducibility packs with run id, config hash, code version, data
  fingerprints, artifact hashes, frozen config, and manifest JSON.
- Queryable SQLite experiment registry at `results/experiments.sqlite` by
  default, populated from reproducibility manifests.
- As-of signal generation for daily research automation without using future
  returns.
- Run comparison tooling over reproducibility manifests, with provenance
  warnings when compared runs use different configs, commits, data sources, or
  dirty worktrees.

## Validation

```bash
python -m pytest
python -m quant_research_agent.main --config configs/base.yaml --json
python -m quant_research_agent.api
```

## Limitations

- Synthetic data validates mechanics but is not investment evidence.
- Yahoo Finance is a convenient demo source, not an institutional data source;
  reports flag this explicitly in the data integrity section.
- v1 has diagnostic neutralization, liquidity stress tests, robustness checks,
  capacity diagnostics, a liquidity-sensitive transaction cost model, borrow
  constraints, a CSV locate-history adapter, run comparison, a local experiment
  registry, an internal API, and as-of signal generation, but no direct vendor API
  integration, broker-grade locate entitlement feed, auth, paper/live broker
  execution, order management, or compliance workflow.

## Production Readiness Path

This repo is now aimed at Level 1 first: an internal production research
platform. It is not a live trading system.

Implemented Level 1 foundations:

- Dockerfile and `docker-compose.yml` for the internal API.
- `.env.example` with non-secret local defaults.
- GitHub Actions test workflow.
- Queryable experiment registry.
- As-of signal API.

Deferred until separate stories:

- Postgres/object-storage backed registry and artifacts.
- Scheduler/worker orchestration beyond the provided daily-run script.
- Auth, authorization, and multi-user SaaS controls.
- Commercial data vendor ingestion.
- Paper trading, broker integration, hard risk gates, reconciliation, and kill
  switch controls.

## Next Steps

- Add direct vendor API integration behind the validated snapshot adapter.
- Add direct locate/borrow availability integration from a securities-lending
  source.
- Add broker-grade execution simulator with venue routing and order scheduling.
- Add paper-to-alpha extraction that turns quant papers/blogs into experiment
  templates.
