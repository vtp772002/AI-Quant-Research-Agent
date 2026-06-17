# AI Quant Research Agent

## Research Goal

This project explores whether agentic LLM-style workflows can accelerate the
quantitative research loop from hypothesis generation to executable signal,
backtest, metric evaluation, and research reporting.

## Product Surface

The first product surface is a Python CLI:

```bash
python -m quant_research_agent.main --config configs/base.yaml
```

The compatibility entrypoint below is also supported because the original spec
suggested it:

```bash
python -m src.main --config configs/base.yaml
```

## Core Workflow

1. Load OHLCV market data for a configured universe.
2. Propose or load an alpha hypothesis.
3. Compute a reusable factor library.
4. Convert selected factors into a cross-sectional signal.
5. Run a long-short backtest with chronological train/test split.
6. Compare the agent signal against configured baseline strategies.
7. Calculate IC, Sharpe ratio, max drawdown, turnover, and total return.
8. Write a Markdown research report and append experiment metrics.

## Data Contract

Market data is represented as a `pandas.DataFrame` indexed by
`date, symbol` with these columns:

- `open`
- `high`
- `low`
- `close`
- `adj_close`
- `volume`

v1 supports deterministic synthetic data for validation and Yahoo Finance data
for real-market experiments.

The Yahoo demo configuration is `configs/yahoo_nasdaq_demo.yaml`. It is intended
for exploratory real-data runs and may fail when the external data provider is
unavailable.

## Methodology

Signals are cross-sectional: each factor is ranked across the active universe
on the rebalance date. The portfolio is dollar-neutral, long the top quantile
and short the bottom quantile, rebalanced at a configured interval.

Baseline strategies use the same data, train/test split, rebalance interval,
portfolio construction, and transaction cost assumptions as the agent signal.
This keeps comparison focused on signal quality rather than backtest settings.

## Limitations

- Synthetic data validates mechanics, not investment merit.
- Yahoo Finance data is useful for demos but not institutional-grade research
  data.
- v1 does not include sector neutralization, borrow constraints, liquidity
  caps, survivorship controls, or a full transaction cost model.
