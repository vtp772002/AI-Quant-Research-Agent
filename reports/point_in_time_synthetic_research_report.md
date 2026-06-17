# AI Quant Research Report

## Experiment

- Name: `point_in_time_synthetic_momentum_low_volatility`
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
- Universe source: `csv:configs/universe_membership_demo.csv`
- Membership rows: 20
- Requested symbols: 20
- Observed symbols: 20
- Date rows: 1305
- Panel rows: 25576
- Point-in-time universe: yes
- Survivorship-bias-free: yes
- Corporate actions institutional-grade: no

| Symbol | Observations | Coverage | Missing Rows | Zero Volume | Bad Prices | Extreme Returns | Stale Prices |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| AAPL | 1305 | 100.00% | 0 | 0 | 0 | 0 | 0 |
| ADBE | 1305 | 100.00% | 0 | 0 | 0 | 0 | 0 |
| AMAT | 1305 | 100.00% | 0 | 0 | 0 | 0 | 0 |
| AMD | 1305 | 100.00% | 0 | 0 | 0 | 0 | 0 |
| AMZN | 1305 | 100.00% | 0 | 0 | 0 | 0 | 0 |
| AVGO | 1305 | 100.00% | 0 | 0 | 0 | 0 | 0 |
| BKNG | 1043 | 79.92% | 262 | 0 | 0 | 0 | 0 |
| COST | 1305 | 100.00% | 0 | 0 | 0 | 0 | 0 |
| CSCO | 1305 | 100.00% | 0 | 0 | 0 | 0 | 0 |
| GOOGL | 1305 | 100.00% | 0 | 0 | 0 | 0 | 0 |
| HON | 1305 | 100.00% | 0 | 0 | 0 | 0 | 0 |
| INTU | 1305 | 100.00% | 0 | 0 | 0 | 0 | 0 |
| META | 1305 | 100.00% | 0 | 0 | 0 | 0 | 0 |
| MSFT | 1305 | 100.00% | 0 | 0 | 0 | 0 | 0 |
| NFLX | 1305 | 100.00% | 0 | 0 | 0 | 0 | 0 |
| NVDA | 1305 | 100.00% | 0 | 0 | 0 | 0 | 0 |
| QCOM | 1305 | 100.00% | 0 | 0 | 0 | 0 | 0 |
| SBUX | 1305 | 100.00% | 0 | 0 | 0 | 0 | 0 |
| TSLA | 1043 | 79.92% | 262 | 0 | 0 | 0 | 0 |
| TXN | 1305 | 100.00% | 0 | 0 | 0 | 0 | 0 |

Warnings:
- Synthetic data validates mechanics but is not investment evidence.
- Corporate-action handling is not marked institutional-grade.
- BKNG coverage is 79.92%; inspect missing rows before trusting results.
- TSLA coverage is 79.92%; inspect missing rows before trusting results.

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
| momentum_20d | 25176 | 96.46% | 3.54% |
| momentum_60d | 24376 | 93.39% | 6.61% |
| volatility_20d | 25176 | 96.46% | 3.54% |
| drawdown_20d | 25196 | 96.54% | 3.46% |
| reversal_5d | 25476 | 97.61% | 2.39% |

Pairs above absolute Spearman correlation of 0.75:

| Factor A | Factor B | Spearman Corr |
| --- | --- | ---: |
| momentum_20d | drawdown_20d | 0.7897 |

## Results

| Split | IC Mean | Sharpe | Max Drawdown | Avg Turnover | Avg Cost | Total Return |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Train | 0.0175 | 0.24 | -32.27% | 1.53 | 0.18% | 10.89% |
| Test | 0.0272 | 0.00 | -25.50% | 1.43 | 0.19% | -3.17% |
| Full | 0.0204 | 0.18 | -32.27% | 1.50 | 0.18% | 7.38% |

## Execution Costs

| Component | Train | Test | Full |
| --- | ---: | ---: | ---: |
| Avg base cost | 0.08% | 0.07% | 0.07% |
| Avg spread cost | 0.03% | 0.03% | 0.03% |
| Avg impact cost | 0.06% | 0.08% | 0.06% |
| Avg borrow cost | 0.01% | 0.01% | 0.01% |
| Avg total cost | 0.18% | 0.19% | 0.18% |
| Cumulative cost | 31.47% | 14.28% | 45.75% |
| Avg trade participation | 0.38% | 0.53% | 0.43% |
| Max trade participation | 2.10% | 2.71% | 2.71% |

## Borrow Availability

No date-aware locate or borrow availability history was configured.

## Capacity Diagnostics

| Metric | Value |
| --- | ---: |
| Max single-name weight | 33.33% |
| Avg single-name max weight | 25.99% |
| Avg effective positions | 8.08 |
| Min effective positions | 6.86 |
| Avg gross exposure | 2.00x |
| Max gross exposure | 2.00x |
| Position weight breaches | 0 |

Capacity curve:

| Notional | Test Sharpe | Test Return | Avg Cost | Avg Impact | Avg Participation | Max Participation | Breaches | Pass |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| 1,000,000 | 0.17 | 2.02% | 0.12% | 0.01% | 0.05% | 0.27% | 0 | yes |
| 5,000,000 | 0.09 | -0.32% | 0.15% | 0.04% | 0.26% | 1.36% | 0 | yes |
| 10,000,000 | 0.00 | -3.17% | 0.19% | 0.08% | 0.53% | 2.71% | 0 | yes |
| 25,000,000 | -0.28 | -11.24% | 0.31% | 0.20% | 1.31% | 6.78% | 0 | no |

Estimated capacity: 10,000,000 notional under configured gates.

## Robustness Diagnostics

| Metric | Mean | 2.5% | 97.5% | Positive Probability |
| --- | ---: | ---: | ---: | ---: |
| Test Sharpe | -0.04 | -1.53 | 1.46 | 51.00% |
| Test IC | 0.0242 | -0.0255 | 0.0678 | 82.50% |

Parameter Sensitivity:

| Variant | Holding | Quantile | Cost Mult | Test IC | Test Sharpe | Test Cost | Test Return |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| h3_q15 | 3 | 15% | 1.00 | 0.0143 | -0.95 | 0.24% | -22.06% |
| h3_q20 | 3 | 20% | 1.00 | 0.0143 | -1.11 | 0.19% | -21.28% |
| h3_q30 | 3 | 30% | 1.00 | 0.0143 | -1.60 | 0.14% | -22.05% |
| h5_q15 | 5 | 15% | 1.00 | 0.0272 | 0.28 | 0.24% | 6.10% |
| h5_q20 | 5 | 20% | 1.00 | 0.0272 | 0.00 | 0.19% | -3.17% |
| h5_q30 | 5 | 30% | 1.00 | 0.0272 | -0.41 | 0.15% | -11.53% |
| h10_q15 | 10 | 15% | 1.00 | 0.0151 | 0.31 | 0.26% | 14.81% |
| h10_q20 | 10 | 20% | 1.00 | 0.0151 | 0.36 | 0.21% | 18.54% |
| h10_q30 | 10 | 30% | 1.00 | 0.0151 | 0.01 | 0.16% | -4.33% |

Cost Sensitivity:

| Variant | Holding | Quantile | Cost Mult | Test IC | Test Sharpe | Test Cost | Test Return |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| cost_0.5x | 5 | 20% | 0.50 | 0.0272 | 0.23 | 0.10% | 4.01% |
| cost_1x | 5 | 20% | 1.00 | 0.0272 | 0.00 | 0.19% | -3.17% |
| cost_2x | 5 | 20% | 2.00 | 0.0272 | -0.46 | 0.39% | -16.09% |

## Baseline Comparison

| Strategy | Test IC | Test Sharpe | Test Max Drawdown | Test Turnover | Test Cost | Test Total Return |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| agent_signal | 0.0272 | 0.00 | -25.50% | 1.43 | 0.19% | -3.17% |
| momentum_20d_only | 0.0419 | -0.00 | -32.18% | 1.67 | 0.23% | -4.51% |
| low_volatility_only | -0.0249 | -1.58 | -51.49% | 0.97 | 0.14% | -42.01% |
| reversal_5d_only | -0.0646 | -2.72 | -63.67% | 3.01 | 0.44% | -61.47% |
| random_cross_section | -0.0052 | -0.75 | -36.10% | 3.24 | 0.47% | -29.34% |

## Stress Tests

| Stress Test | Test IC | Test Sharpe | Test Max Drawdown | Test Turnover | Test Cost | Test Total Return |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| sector_neutral_signal | 0.0285 | 0.30 | -18.92% | 1.42 | 0.19% | 6.34% |
| liquidity_top_80pct | 0.0265 | 0.07 | -19.41% | 1.37 | 0.16% | -0.67% |
| sector_neutral_liquidity_top_80pct | 0.0344 | 0.52 | -18.20% | 1.36 | 0.17% | 13.91% |

## Walk-Forward Validation

| Window | Train Through | Test Range | Obs | IC Mean | Sharpe | Avg Cost | Hit Rate | Total Return |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| wf_01 | 2022-02-09 | 2022-02-16 to 2023-01-18 | 49 | 0.0152 | -0.36 | 0.19% | 53.06% | -10.68% |
| wf_02 | 2023-01-18 | 2023-01-25 to 2023-12-27 | 49 | 0.0285 | 0.66 | 0.19% | 46.94% | 13.23% |
| wf_03 | 2023-12-27 | 2024-01-03 to 2024-12-18 | 51 | 0.0461 | 0.76 | 0.19% | 60.78% | 15.39% |

| Strategy | Windows | Mean Test IC | Mean Sharpe | Mean Cost | Positive IC Windows | Median Total Return |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| agent_signal | 3 | 0.0299 | 0.36 | 0.19% | 100.00% | 13.23% |
| momentum_20d_only | 3 | 0.0226 | -0.21 | 0.22% | 100.00% | -13.89% |
| low_volatility_only | 3 | -0.0054 | -0.82 | 0.14% | 33.33% | -21.89% |
| reversal_5d_only | 3 | -0.0443 | -2.57 | 0.43% | 0.00% | -41.17% |
| random_cross_section | 3 | 0.0079 | -0.29 | 0.45% | 66.67% | -9.47% |
| sector_neutral_signal | 3 | 0.0299 | 0.39 | 0.19% | 66.67% | 12.86% |
| liquidity_top_80pct | 3 | 0.0295 | 0.49 | 0.16% | 100.00% | 7.10% |
| sector_neutral_liquidity_top_80pct | 3 | 0.0271 | 0.57 | 0.16% | 66.67% | 14.82% |

## Interpretation

The signal is a candidate for deeper research: out-of-sample IC and Sharpe are positive. The next question is whether the effect survives real data, costs, and neutralization.

The agent signal has the strongest out-of-sample Sharpe among configured strategies. Its test IC is 0.0272, so the next validation target is stability across real data and walk-forward windows.

The signal keeps positive test IC and Sharpe under these stress tests: sector_neutral_signal, liquidity_top_80pct, sector_neutral_liquidity_top_80pct. Compare their drawdowns and turnover before treating this as robust.

Factor diagnostics flagged potentially redundant exposures. The strongest pair is `momentum_20d` and `drawdown_20d` with Spearman correlation 0.7897; simplify or orthogonalize before adding more factors.

Robustness diagnostics flag caution: bootstrap Sharpe confidence is weak; high-cost sensitivity erases positive Sharpe.

Capacity diagnostics estimate that the signal passes configured gates up to 10,000,000 notional. Treat this as a research approximation because the model uses average dollar volume, not live order book depth.

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

- Run ID: `point-in-time-synthetic-momentum-low-volatility-20260617T045621Z-ad5ebc3c4c-bebe91a8`
- Generated at: `2026-06-17T04:56:21Z`
- Config SHA-256: `ad5ebc3c4cbb9b2014d690c1283909da6a498c29e11f27b0f2331ce7965d583c`
- Git commit: `69b38c7dc11d716c7d2e4a6e608fd6d01d058996`
- Git branch: `main`
- Git dirty: yes
- Manifest: `results/runs/point-in-time-synthetic-momentum-low-volatility-20260617T045621Z-ad5ebc3c4c-bebe91a8/manifest.json`
- Frozen config: `results/runs/point-in-time-synthetic-momentum-low-volatility-20260617T045621Z-ad5ebc3c4c-bebe91a8/config.yaml`
