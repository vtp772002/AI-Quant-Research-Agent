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
2. Diagnose data source quality, panel coverage, and institutional-readiness
   assumptions.
3. Propose or load an alpha hypothesis.
4. Compute a reusable factor library.
5. Convert selected factors into a cross-sectional signal.
6. Diagnose selected factor coverage and pairwise redundancy.
7. Run a long-short backtest with chronological train/test split.
8. Compare the agent signal against configured baseline strategies.
9. Validate signal stability over configured walk-forward windows.
10. Stress-test the agent signal with configured neutralization and liquidity
   constraints.
11. Apply base, spread, and liquidity-sensitive market-impact transaction
   costs.
12. Calculate IC, Sharpe ratio, max drawdown, turnover, costs, and total
   return.
13. Write a Markdown research report and append experiment metrics.

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

Data integrity diagnostics report requested versus observed symbols, row and
date counts, per-symbol coverage, duplicate index rows, non-positive prices or
volume, stale adjusted closes, extreme adjusted returns, and explicit warnings
when data is not marked point-in-time, survivorship-bias-free, or
institutional-grade for corporate actions.

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

Stress tests are optional backtest variants that reuse the same market data,
rebalance cadence, transaction cost assumption, and validation windows as the
agent signal. Sector neutralization subtracts each configured sector's
cross-sectional mean signal on each rebalance date. Liquidity filtering removes
assets below the configured cross-sectional `dollar_volume_20d` rank before
portfolio construction.

Transaction costs include a base turnover cost, spread cost, and
liquidity-sensitive market impact cost. Market impact is estimated from trade
size as a fraction of rolling 20-day average dollar volume using the configured
portfolio notional and impact coefficient. Reports include average base,
spread, impact, total cost, and trade participation diagnostics.

## Limitations

- Synthetic data validates mechanics, not investment merit.
- Yahoo Finance data is useful for demos but not institutional-grade research
  data.
- Data integrity diagnostics identify readiness gaps but do not create
  survivorship-safe data by themselves.
- Walk-forward validation tests temporal stability but does not remove the need
  for better data controls and independent hypothesis review.
- v1 includes a liquidity-sensitive transaction cost model, but it is still a
  research approximation and does not replace broker execution data, venue
  routing analysis, borrow constraints, survivorship controls, or a full
  production execution simulator.
