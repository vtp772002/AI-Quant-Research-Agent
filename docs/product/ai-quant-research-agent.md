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
5. Diagnose selected factor coverage and pairwise redundancy.
6. Run a long-short backtest with chronological train/test split.
7. Compare the agent signal against configured baseline strategies.
8. Validate signal stability over configured walk-forward windows.
9. Calculate IC, Sharpe ratio, max drawdown, turnover, and total return.
10. Write a Markdown research report and append experiment metrics.

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

When configured, walk-forward validation divides the backtest results into
multiple chronological test windows after an initial expanding training period.
The report summarizes agent-signal stability by window and compares aggregate
walk-forward stability across configured strategies.

Factor diagnostics evaluate the selected agent and baseline factor exposures
before interpreting results. The report shows factor coverage, missing rates,
and high absolute Spearman-correlation pairs so redundant exposures can be
simplified before adding more signal complexity.

## Limitations

- Synthetic data validates mechanics, not investment merit.
- Yahoo Finance data is useful for demos but not institutional-grade research
  data.
- Walk-forward validation tests temporal stability but does not remove the need
  for better data controls and independent hypothesis review.
- v1 does not include sector neutralization, borrow constraints, liquidity
  caps, survivorship controls, or a full transaction cost model.
