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

- `data`: load deterministic synthetic OHLCV data or Yahoo Finance OHLCV data.
- `factors`: compute a reusable factor library with 20+ price, momentum,
  reversal, volatility, volume, and liquidity factors.
- `agents`: create a hypothesis, translate selected factors into a ranked
  signal, compare it with baselines, evaluate the experiment, and write a
  report.
- `backtest`: run a dollar-neutral top/bottom quantile long-short portfolio.
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
- Borrow fee and shortability constraints for short-leg feasibility.
- Point-in-time CSV universe membership adapter for survivorship-safe research
  interfaces.
- Bootstrap confidence intervals, parameter sensitivity grids, and cost
  sensitivity diagnostics for overfit and robustness review.

## Validation

```bash
python -m pytest
python -m quant_research_agent.main --config configs/base.yaml --json
```

## Limitations

- Synthetic data validates mechanics but is not investment evidence.
- Yahoo Finance is a convenient demo source, not an institutional data source;
  reports flag this explicitly in the data integrity section.
- v1 has diagnostic neutralization, liquidity stress tests, robustness checks,
  and a liquidity-sensitive transaction cost model plus borrow constraints, but
  no vendor API integration, locate record ingestion, or broker-grade execution
  simulator.

## Next Steps

- Add direct vendor data integration behind the point-in-time universe adapter.
- Add locate/borrow availability history from a securities-lending source.
- Add paper-to-alpha extraction that turns quant papers/blogs into experiment
  templates.
