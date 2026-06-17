# AI Quant Research Report

## Experiment

- Name: `yahoo_nasdaq_momentum_low_volatility`
- Universe: 20 assets from `yahoo`
- Date range: 2020-01-01 to 2025-12-31
- Holding period: 5 trading days
- Rebalance: every 5 trading days
- Long/short quantile: 20%

## Data Integrity

- Source: `yahoo`
- Requested symbols: 20
- Observed symbols: 20
- Date rows: 1507
- Panel rows: 30140
- Point-in-time universe: no
- Survivorship-bias-free: no
- Corporate actions institutional-grade: no

| Symbol | Observations | Coverage | Missing Rows | Zero Volume | Bad Prices | Extreme Returns | Stale Prices |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| AAPL | 1507 | 100.00% | 0 | 0 | 0 | 0 | 0 |
| MSFT | 1507 | 100.00% | 0 | 0 | 0 | 0 | 0 |
| NVDA | 1507 | 100.00% | 0 | 0 | 0 | 0 | 0 |
| AMZN | 1507 | 100.00% | 0 | 0 | 0 | 0 | 0 |
| META | 1507 | 100.00% | 0 | 0 | 0 | 0 | 0 |
| GOOGL | 1507 | 100.00% | 0 | 0 | 0 | 0 | 0 |
| AVGO | 1507 | 100.00% | 0 | 0 | 0 | 0 | 0 |
| COST | 1507 | 100.00% | 0 | 0 | 0 | 0 | 0 |
| TSLA | 1507 | 100.00% | 0 | 0 | 0 | 0 | 0 |
| NFLX | 1507 | 100.00% | 0 | 0 | 0 | 0 | 0 |
| AMD | 1507 | 100.00% | 0 | 0 | 0 | 0 | 0 |
| ADBE | 1507 | 100.00% | 0 | 0 | 0 | 0 | 0 |
| CSCO | 1507 | 100.00% | 0 | 0 | 0 | 0 | 0 |
| QCOM | 1507 | 100.00% | 0 | 0 | 0 | 0 | 0 |
| TXN | 1507 | 100.00% | 0 | 0 | 0 | 0 | 0 |
| INTU | 1507 | 100.00% | 0 | 0 | 0 | 0 | 0 |
| AMAT | 1507 | 100.00% | 0 | 0 | 0 | 0 | 0 |
| HON | 1507 | 100.00% | 0 | 0 | 0 | 0 | 0 |
| SBUX | 1507 | 100.00% | 0 | 0 | 0 | 0 | 0 |
| BKNG | 1507 | 100.00% | 0 | 0 | 0 | 0 | 0 |

Warnings:
- Yahoo Finance is a demo source and does not provide an institutional point-in-time research dataset.
- Universe membership is not marked point-in-time; survivorship or lookahead bias may remain.
- Universe is not marked survivorship-bias-free.
- Corporate-action handling is not marked institutional-grade.

## Hypothesis

Assets with stronger recent momentum and lower realized risk should outperform over the next 5 trading days.

Expected direction: positive exposure to [momentum_20d, momentum_60d], negative exposure to [volatility_20d, drawdown_20d].

## Signal

Positive factors: momentum_20d, momentum_60d

Negative factors: volatility_20d, drawdown_20d

Signal is built from cross-sectional percentile ranks so each rebalance compares assets only against the active universe on that date.

## Factor Diagnostics

| Factor | Observations | Coverage | Missing Rate |
| --- | ---: | ---: | ---: |
| momentum_20d | 29740 | 98.67% | 1.33% |
| momentum_60d | 28940 | 96.02% | 3.98% |
| volatility_20d | 29740 | 98.67% | 1.33% |
| drawdown_20d | 29760 | 98.74% | 1.26% |
| reversal_5d | 30040 | 99.67% | 0.33% |

No selected factor pairs exceeded absolute Spearman correlation of 0.75.

## Results

| Split | IC Mean | Sharpe | Max Drawdown | Avg Turnover | Avg Cost | Total Return |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Train | 0.0209 | 0.23 | -29.99% | 1.65 | 0.15% | 11.64% |
| Test | -0.0079 | -0.55 | -29.33% | 1.58 | 0.13% | -23.13% |
| Full | 0.0123 | 0.01 | -29.99% | 1.63 | 0.14% | -14.19% |

## Execution Costs

| Component | Train | Test | Full |
| --- | ---: | ---: | ---: |
| Avg base cost | 0.08% | 0.08% | 0.08% |
| Avg spread cost | 0.03% | 0.03% | 0.03% |
| Avg impact cost | 0.03% | 0.02% | 0.03% |
| Avg total cost | 0.15% | 0.13% | 0.14% |
| Cumulative cost | 29.82% | 11.14% | 40.96% |
| Avg trade participation | 0.19% | 0.12% | 0.16% |
| Max trade participation | 1.27% | 0.69% | 1.27% |

## Baseline Comparison

| Strategy | Test IC | Test Sharpe | Test Max Drawdown | Test Turnover | Test Cost | Test Total Return |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| agent_signal | -0.0079 | -0.55 | -29.33% | 1.58 | 0.13% | -23.13% |
| momentum_20d_only | -0.0437 | -0.70 | -38.71% | 1.65 | 0.14% | -32.72% |
| low_volatility_only | -0.0288 | -1.38 | -59.41% | 0.91 | 0.08% | -55.40% |
| reversal_5d_only | 0.0613 | 0.45 | -28.90% | 3.26 | 0.28% | 16.01% |
| random_cross_section | -0.0001 | -0.85 | -34.56% | 3.25 | 0.28% | -26.34% |

## Stress Tests

| Stress Test | Test IC | Test Sharpe | Test Max Drawdown | Test Turnover | Test Cost | Test Total Return |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| sector_neutral_signal | -0.0089 | -0.41 | -27.33% | 1.47 | 0.12% | -17.29% |
| liquidity_top_80pct | 0.0048 | -0.43 | -29.67% | 1.42 | 0.11% | -20.57% |
| sector_neutral_liquidity_top_80pct | 0.0009 | -0.23 | -22.61% | 1.46 | 0.12% | -12.17% |

## Walk-Forward Validation

| Window | Train Through | Test Range | Obs | IC Mean | Sharpe | Avg Cost | Hit Rate | Total Return |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| wf_01 | 2022-07-05 | 2022-07-12 to 2023-08-29 | 58 | 0.0041 | 1.05 | 0.15% | 50.00% | 30.61% |
| wf_02 | 2023-08-29 | 2023-09-06 to 2024-10-23 | 58 | 0.0045 | -0.52 | 0.15% | 46.55% | -15.51% |
| wf_03 | 2024-10-23 | 2024-10-30 to 2025-12-19 | 58 | -0.0009 | -0.31 | 0.13% | 48.28% | -11.23% |

| Strategy | Windows | Mean Test IC | Mean Sharpe | Mean Cost | Positive IC Windows | Median Total Return |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| agent_signal | 3 | 0.0026 | 0.07 | 0.14% | 66.67% | -11.23% |
| momentum_20d_only | 3 | -0.0183 | -0.08 | 0.14% | 33.33% | 12.32% |
| low_volatility_only | 3 | -0.0387 | -1.60 | 0.08% | 0.00% | -46.64% |
| reversal_5d_only | 3 | 0.0206 | -0.55 | 0.28% | 66.67% | -8.21% |
| random_cross_section | 3 | 0.0032 | -1.15 | 0.29% | 66.67% | -20.88% |
| sector_neutral_signal | 3 | 0.0023 | -0.02 | 0.13% | 33.33% | -6.77% |
| liquidity_top_80pct | 3 | 0.0086 | 0.09 | 0.12% | 66.67% | -2.05% |
| sector_neutral_liquidity_top_80pct | 3 | 0.0009 | -0.05 | 0.12% | 66.67% | -1.06% |

## Interpretation

The signal is not supported out-of-sample in this run. Treat it as rejected until a more robust variant improves IC stability without increasing overfit risk.

The strongest out-of-sample Sharpe is from `reversal_5d_only`, not the agent signal. Treat this as a useful rejection/iteration signal: inspect which factor exposure is carrying the result before adding model complexity.

The stress-test variants did not preserve both positive IC and positive Sharpe. The base agent test IC is -0.0079 and Sharpe is -0.55; investigate sector or liquidity dependence.

Factor diagnostics did not flag high pairwise redundancy among selected exposures.

Walk-forward validation is not yet stable enough for promotion: inspect the weak windows before adding factor complexity.

The train/test split is chronological. Test-period results are the primary evidence because they are less exposed to factor selection bias.

## Limitations

- Synthetic data is useful for deterministic validation but is not investment evidence.
- Stress tests are diagnostics; the primary portfolio remains a simple long-short ranking portfolio.
- Transaction costs are modeled with base, spread, and participation-based impact assumptions, not broker execution data.
- No borrow constraints, corporate actions, or survivorship controls are included yet.

## Next Experiments

- Run the same signal on Yahoo Finance data for a real equity universe.
- Replace redundant factors or orthogonalize correlated exposures before combining signals.
- Add borrow costs and shortability constraints.
- Compare this factor against pure momentum, pure low volatility, and reversal baselines.
