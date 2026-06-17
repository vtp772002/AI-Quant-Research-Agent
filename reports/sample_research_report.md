# AI Quant Research Report

## Experiment

- Name: `momentum_low_volatility_demo`
- Universe: 20 assets from `synthetic`
- Date range: 2020-01-01 to 2024-12-31
- Holding period: 5 trading days
- Rebalance: every 5 trading days
- Long/short quantile: 20%
- Borrow fee: 75.0 bps annualized
- Shortable universe: 18 configured symbols
- Locate history: not configured

## Data Integrity

- Source: `synthetic`
- Universe source: `static`
- Membership rows: 20
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
| Train | 0.0186 | 0.16 | -34.06% | 1.57 | 0.18% | 4.05% |
| Test | 0.0253 | -0.10 | -25.95% | 1.44 | 0.19% | -5.65% |
| Full | 0.0206 | 0.09 | -34.06% | 1.53 | 0.19% | -1.83% |

## Execution Costs

| Component | Train | Test | Full |
| --- | ---: | ---: | ---: |
| Avg base cost | 0.08% | 0.07% | 0.08% |
| Avg spread cost | 0.03% | 0.03% | 0.03% |
| Avg impact cost | 0.06% | 0.08% | 0.06% |
| Avg borrow cost | 0.01% | 0.01% | 0.01% |
| Avg total cost | 0.18% | 0.19% | 0.19% |
| Cumulative cost | 32.11% | 14.12% | 46.23% |
| Avg trade participation | 0.38% | 0.51% | 0.42% |
| Max trade participation | 2.44% | 3.01% | 3.01% |

## Borrow Availability

No date-aware locate or borrow availability history was configured.

## Capacity Diagnostics

| Metric | Value |
| --- | ---: |
| Max single-name weight | 33.33% |
| Avg single-name max weight | 25.99% |
| Avg effective positions | 8.13 |
| Min effective positions | 6.86 |
| Avg gross exposure | 2.00x |
| Max gross exposure | 2.00x |
| Position weight breaches | 0 |

Capacity curve:

| Notional | Test Sharpe | Test Return | Avg Cost | Avg Impact | Avg Participation | Max Participation | Breaches | Pass |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| 1,000,000 | 0.07 | -0.77% | 0.12% | 0.01% | 0.05% | 0.30% | 0 | yes |
| 5,000,000 | -0.01 | -2.97% | 0.15% | 0.04% | 0.26% | 1.51% | 0 | no |
| 10,000,000 | -0.10 | -5.65% | 0.19% | 0.08% | 0.51% | 3.01% | 0 | no |
| 25,000,000 | -0.39 | -13.26% | 0.30% | 0.19% | 1.28% | 7.53% | 0 | no |

Estimated capacity: 1,000,000 notional under configured gates.

## Robustness Diagnostics

| Metric | Mean | 2.5% | 97.5% | Positive Probability |
| --- | ---: | ---: | ---: | ---: |
| Test Sharpe | -0.11 | -1.72 | 1.41 | 44.00% |
| Test IC | 0.0223 | -0.0258 | 0.0650 | 81.50% |

Parameter Sensitivity:

| Variant | Holding | Quantile | Cost Mult | Test IC | Test Sharpe | Test Cost | Test Return |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| h3_q15 | 3 | 15% | 1.00 | 0.0136 | -1.59 | 0.23% | -31.16% |
| h3_q20 | 3 | 20% | 1.00 | 0.0136 | -1.34 | 0.19% | -24.52% |
| h3_q30 | 3 | 30% | 1.00 | 0.0136 | -0.91 | 0.14% | -13.73% |
| h5_q15 | 5 | 15% | 1.00 | 0.0253 | -0.39 | 0.23% | -16.60% |
| h5_q20 | 5 | 20% | 1.00 | 0.0253 | -0.10 | 0.19% | -5.65% |
| h5_q30 | 5 | 30% | 1.00 | 0.0253 | 0.12 | 0.14% | 0.97% |
| h10_q15 | 10 | 15% | 1.00 | 0.0155 | 0.04 | 0.24% | -6.74% |
| h10_q20 | 10 | 20% | 1.00 | 0.0155 | 0.43 | 0.21% | 23.26% |
| h10_q30 | 10 | 30% | 1.00 | 0.0155 | 0.45 | 0.16% | 21.11% |

Cost Sensitivity:

| Variant | Holding | Quantile | Cost Mult | Test IC | Test Sharpe | Test Cost | Test Return |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| cost_0.5x | 5 | 20% | 0.50 | 0.0253 | 0.14 | 0.10% | 1.28% |
| cost_1x | 5 | 20% | 1.00 | 0.0253 | -0.10 | 0.19% | -5.65% |
| cost_2x | 5 | 20% | 2.00 | 0.0253 | -0.58 | 0.38% | -18.14% |

## Baseline Comparison

| Strategy | Test IC | Test Sharpe | Test Max Drawdown | Test Turnover | Test Cost | Test Total Return |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| agent_signal | 0.0253 | -0.10 | -25.95% | 1.44 | 0.19% | -5.65% |
| momentum_20d_only | 0.0375 | 0.18 | -28.22% | 1.66 | 0.23% | 1.93% |
| low_volatility_only | -0.0258 | -1.33 | -47.08% | 0.93 | 0.13% | -37.62% |
| reversal_5d_only | -0.0582 | -2.89 | -66.96% | 3.05 | 0.45% | -63.82% |
| random_cross_section | -0.0432 | -1.92 | -49.12% | 3.16 | 0.46% | -49.31% |

## Stress Tests

| Stress Test | Test IC | Test Sharpe | Test Max Drawdown | Test Turnover | Test Cost | Test Total Return |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| sector_neutral_signal | 0.0202 | 0.12 | -27.45% | 1.42 | 0.20% | 0.32% |
| liquidity_top_80pct | 0.0247 | 0.49 | -19.70% | 1.39 | 0.17% | 11.35% |
| sector_neutral_liquidity_top_80pct | 0.0426 | 1.01 | -23.30% | 1.23 | 0.15% | 35.40% |

## Walk-Forward Validation

| Window | Train Through | Test Range | Obs | IC Mean | Sharpe | Avg Cost | Hit Rate | Total Return |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| wf_01 | 2022-02-09 | 2022-02-16 to 2023-01-18 | 49 | 0.0152 | -0.51 | 0.19% | 53.06% | -13.70% |
| wf_02 | 2023-01-18 | 2023-01-25 to 2023-12-27 | 49 | 0.0298 | 0.60 | 0.19% | 46.94% | 11.92% |
| wf_03 | 2023-12-27 | 2024-01-03 to 2024-12-18 | 51 | 0.0421 | 0.91 | 0.18% | 52.94% | 17.59% |

| Strategy | Windows | Mean Test IC | Mean Sharpe | Mean Cost | Positive IC Windows | Median Total Return |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| agent_signal | 3 | 0.0290 | 0.33 | 0.19% | 100.00% | 11.92% |
| momentum_20d_only | 3 | 0.0205 | 0.02 | 0.21% | 100.00% | -4.18% |
| low_volatility_only | 3 | -0.0059 | -0.76 | 0.14% | 33.33% | -15.79% |
| reversal_5d_only | 3 | -0.0412 | -2.77 | 0.44% | 0.00% | -39.31% |
| random_cross_section | 3 | -0.0041 | -1.07 | 0.46% | 33.33% | -34.45% |
| sector_neutral_signal | 3 | 0.0173 | 0.05 | 0.19% | 66.67% | 7.07% |
| liquidity_top_80pct | 3 | 0.0286 | 0.80 | 0.16% | 100.00% | 17.00% |
| sector_neutral_liquidity_top_80pct | 3 | 0.0273 | 0.54 | 0.15% | 66.67% | 19.60% |

## Interpretation

The signal shows positive out-of-sample rank correlation but weak portfolio conversion. Investigate turnover, concentration, and whether the long/short cutoffs are too aggressive.

The strongest out-of-sample Sharpe is from `momentum_20d_only`, not the agent signal. Treat this as a useful rejection/iteration signal: inspect which factor exposure is carrying the result before adding model complexity.

The signal keeps positive test IC and Sharpe under these stress tests: sector_neutral_signal, liquidity_top_80pct, sector_neutral_liquidity_top_80pct. Compare their drawdowns and turnover before treating this as robust.

Factor diagnostics flagged potentially redundant exposures. The strongest pair is `momentum_20d` and `drawdown_20d` with Spearman correlation 0.7881; simplify or orthogonalize before adding more factors.

Robustness diagnostics flag caution: bootstrap Sharpe confidence is weak; parameter sensitivity is fragile; high-cost sensitivity erases positive Sharpe.

Capacity diagnostics estimate that the signal passes configured gates up to 1,000,000 notional. Treat this as a research approximation because the model uses average dollar volume, not live order book depth.

Walk-forward validation supports further research: most agent-signal windows have positive IC and the average window Sharpe is positive.

The train/test split is chronological. Test-period results are the primary evidence because they are less exposed to factor selection bias.

## Limitations

- Synthetic data is useful for deterministic validation but is not investment evidence.
- Stress tests are diagnostics; the primary portfolio remains a simple long-short ranking portfolio.
- Transaction costs and borrow costs are research approximations, not broker execution or securities-lending records.
- Snapshot manifests validate reproducibility and provenance, but they are not a substitute for direct vendor entitlements or independent data audits.

## Next Experiments

- Run the same signal on Yahoo Finance data for a real equity universe.
- Replace redundant factors or orthogonalize correlated exposures before combining signals.
- Add direct vendor data integration that writes validated snapshot manifests.
- Compare this factor against pure momentum, pure low volatility, and reversal baselines.

## Run Reproducibility

- Run ID: `momentum-low-volatility-demo-20260617T045621Z-8d50e36b08-a1360cc7`
- Generated at: `2026-06-17T04:56:21Z`
- Config SHA-256: `8d50e36b08d03a13635e9588afdb9d11f2119cceb04d5533d880cf442431309d`
- Git commit: `69b38c7dc11d716c7d2e4a6e608fd6d01d058996`
- Git branch: `main`
- Git dirty: yes
- Manifest: `results/runs/momentum-low-volatility-demo-20260617T045621Z-8d50e36b08-a1360cc7/manifest.json`
- Frozen config: `results/runs/momentum-low-volatility-demo-20260617T045621Z-8d50e36b08-a1360cc7/config.yaml`
