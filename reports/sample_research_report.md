# AI Quant Research Report

## Experiment

- Name: `momentum_low_volatility_demo`
- Universe: 20 assets from `synthetic`
- Date range: 2020-01-01 to 2024-12-31
- Holding period: 5 trading days
- Rebalance: every 5 trading days
- Long/short quantile: 20%

## Data Integrity

- Source: `synthetic`
- Requested symbols: 20
- Observed symbols: 20
- Date rows: 1305
- Panel rows: 26100
- Point-in-time universe: no
- Survivorship-bias-free: no
- Corporate actions institutional-grade: no

| Symbol | Observations | Coverage | Missing Rows | Zero Volume | Bad Prices | Extreme Returns | Stale Prices |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| AAPL | 1305 | 100.00% | 0 | 0 | 0 | 0 | 0 |
| MSFT | 1305 | 100.00% | 0 | 0 | 0 | 0 | 0 |
| NVDA | 1305 | 100.00% | 0 | 0 | 0 | 0 | 0 |
| AMZN | 1305 | 100.00% | 0 | 0 | 0 | 0 | 0 |
| META | 1305 | 100.00% | 0 | 0 | 0 | 0 | 0 |
| GOOGL | 1305 | 100.00% | 0 | 0 | 0 | 0 | 0 |
| AVGO | 1305 | 100.00% | 0 | 0 | 0 | 0 | 0 |
| COST | 1305 | 100.00% | 0 | 0 | 0 | 0 | 0 |
| TSLA | 1305 | 100.00% | 0 | 0 | 0 | 0 | 0 |
| NFLX | 1305 | 100.00% | 0 | 0 | 0 | 0 | 0 |
| AMD | 1305 | 100.00% | 0 | 0 | 0 | 0 | 0 |
| ADBE | 1305 | 100.00% | 0 | 0 | 0 | 0 | 0 |
| CSCO | 1305 | 100.00% | 0 | 0 | 0 | 0 | 0 |
| QCOM | 1305 | 100.00% | 0 | 0 | 0 | 0 | 0 |
| TXN | 1305 | 100.00% | 0 | 0 | 0 | 0 | 0 |
| INTU | 1305 | 100.00% | 0 | 0 | 0 | 0 | 0 |
| AMAT | 1305 | 100.00% | 0 | 0 | 0 | 0 | 0 |
| HON | 1305 | 100.00% | 0 | 0 | 0 | 0 | 0 |
| SBUX | 1305 | 100.00% | 0 | 0 | 0 | 0 | 0 |
| BKNG | 1305 | 100.00% | 0 | 0 | 0 | 0 | 0 |

Warnings:
- Synthetic data validates mechanics but is not investment evidence.
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
| momentum_20d | 25700 | 98.47% | 1.53% |
| momentum_60d | 24900 | 95.40% | 4.60% |
| volatility_20d | 25700 | 98.47% | 1.53% |
| drawdown_20d | 25720 | 98.54% | 1.46% |
| reversal_5d | 26000 | 99.62% | 0.38% |

Pairs above absolute Spearman correlation of 0.75:

| Factor A | Factor B | Spearman Corr |
| --- | --- | ---: |
| momentum_20d | drawdown_20d | 0.7881 |

## Results

| Split | IC Mean | Sharpe | Max Drawdown | Avg Turnover | Avg Cost | Total Return |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Train | 0.0186 | 0.33 | -32.08% | 1.55 | 0.16% | 17.81% |
| Test | 0.0253 | -0.10 | -23.75% | 1.44 | 0.17% | -5.25% |
| Full | 0.0206 | 0.21 | -32.08% | 1.52 | 0.17% | 11.62% |

## Execution Costs

| Component | Train | Test | Full |
| --- | ---: | ---: | ---: |
| Avg base cost | 0.08% | 0.07% | 0.08% |
| Avg spread cost | 0.03% | 0.03% | 0.03% |
| Avg impact cost | 0.06% | 0.07% | 0.06% |
| Avg total cost | 0.16% | 0.17% | 0.17% |
| Cumulative cost | 28.64% | 12.75% | 41.39% |
| Avg trade participation | 0.36% | 0.49% | 0.40% |
| Max trade participation | 2.06% | 2.71% | 2.71% |

## Baseline Comparison

| Strategy | Test IC | Test Sharpe | Test Max Drawdown | Test Turnover | Test Cost | Test Total Return |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| agent_signal | 0.0253 | -0.10 | -23.75% | 1.44 | 0.17% | -5.25% |
| momentum_20d_only | 0.0375 | 0.20 | -26.65% | 1.64 | 0.21% | 2.88% |
| low_volatility_only | -0.0258 | -1.37 | -47.58% | 0.93 | 0.11% | -38.14% |
| reversal_5d_only | -0.0582 | -2.65 | -64.07% | 3.03 | 0.42% | -60.04% |
| random_cross_section | -0.0432 | -1.92 | -48.20% | 3.12 | 0.42% | -48.38% |

## Stress Tests

| Stress Test | Test IC | Test Sharpe | Test Max Drawdown | Test Turnover | Test Cost | Test Total Return |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| sector_neutral_signal | 0.0202 | 0.14 | -22.26% | 1.38 | 0.18% | 1.08% |
| liquidity_top_80pct | 0.0247 | 0.36 | -17.06% | 1.37 | 0.15% | 7.08% |
| sector_neutral_liquidity_top_80pct | 0.0426 | 1.10 | -19.01% | 1.21 | 0.13% | 36.99% |

## Walk-Forward Validation

| Window | Train Through | Test Range | Obs | IC Mean | Sharpe | Avg Cost | Hit Rate | Total Return |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| wf_01 | 2022-02-09 | 2022-02-16 to 2023-01-18 | 49 | 0.0152 | -0.43 | 0.17% | 53.06% | -12.04% |
| wf_02 | 2023-01-18 | 2023-01-25 to 2023-12-27 | 49 | 0.0298 | 0.67 | 0.17% | 46.94% | 13.05% |
| wf_03 | 2023-12-27 | 2024-01-03 to 2024-12-18 | 51 | 0.0421 | 0.77 | 0.17% | 52.94% | 14.21% |

| Strategy | Windows | Mean Test IC | Mean Sharpe | Mean Cost | Positive IC Windows | Median Total Return |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| agent_signal | 3 | 0.0290 | 0.33 | 0.17% | 100.00% | 13.05% |
| momentum_20d_only | 3 | 0.0205 | -0.15 | 0.19% | 100.00% | -13.13% |
| low_volatility_only | 3 | -0.0059 | -0.63 | 0.12% | 33.33% | -15.96% |
| reversal_5d_only | 3 | -0.0412 | -2.59 | 0.41% | 0.00% | -37.49% |
| random_cross_section | 3 | -0.0041 | -0.97 | 0.41% | 33.33% | -28.08% |
| sector_neutral_signal | 3 | 0.0173 | -0.00 | 0.17% | 66.67% | 8.84% |
| liquidity_top_80pct | 3 | 0.0286 | 0.67 | 0.14% | 100.00% | 16.34% |
| sector_neutral_liquidity_top_80pct | 3 | 0.0273 | 0.49 | 0.13% | 66.67% | 17.63% |

## Interpretation

The signal shows positive out-of-sample rank correlation but weak portfolio conversion. Investigate turnover, concentration, and whether the long/short cutoffs are too aggressive.

The strongest out-of-sample Sharpe is from `momentum_20d_only`, not the agent signal. Treat this as a useful rejection/iteration signal: inspect which factor exposure is carrying the result before adding model complexity.

The signal keeps positive test IC and Sharpe under these stress tests: sector_neutral_signal, liquidity_top_80pct, sector_neutral_liquidity_top_80pct. Compare their drawdowns and turnover before treating this as robust.

Factor diagnostics flagged potentially redundant exposures. The strongest pair is `momentum_20d` and `drawdown_20d` with Spearman correlation 0.7881; simplify or orthogonalize before adding more factors.

Walk-forward validation supports further research: most agent-signal windows have positive IC and the average window Sharpe is positive.

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
