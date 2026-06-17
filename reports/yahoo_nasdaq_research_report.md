# AI Quant Research Report

## Experiment

- Name: `yahoo_nasdaq_momentum_low_volatility`
- Universe: 20 assets from `yahoo`
- Date range: 2020-01-01 to 2025-12-31
- Holding period: 5 trading days
- Rebalance: every 5 trading days
- Long/short quantile: 20%
- Borrow fee: 75.0 bps annualized
- Shortable universe: 18 configured symbols
- Locate history: not configured

## Data Integrity

- Source: `yahoo`
- Universe source: `static`
- Membership rows: 20
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
| Train | 0.0209 | 0.23 | -30.68% | 1.73 | 0.17% | 11.58% |
| Test | -0.0079 | -0.29 | -28.13% | 1.62 | 0.15% | -15.17% |
| Full | 0.0123 | 0.09 | -35.43% | 1.70 | 0.16% | -5.35% |

## Execution Costs

| Component | Train | Test | Full |
| --- | ---: | ---: | ---: |
| Avg base cost | 0.09% | 0.08% | 0.08% |
| Avg spread cost | 0.03% | 0.03% | 0.03% |
| Avg impact cost | 0.04% | 0.02% | 0.03% |
| Avg borrow cost | 0.01% | 0.01% | 0.01% |
| Avg total cost | 0.17% | 0.15% | 0.16% |
| Cumulative cost | 34.88% | 12.78% | 47.66% |
| Avg trade participation | 0.20% | 0.12% | 0.18% |
| Max trade participation | 1.51% | 0.69% | 1.51% |

## Borrow Availability

No date-aware locate or borrow availability history was configured.

## Capacity Diagnostics

| Metric | Value |
| --- | ---: |
| Max single-name weight | 50.00% |
| Avg single-name max weight | 28.87% |
| Avg effective positions | 7.71 |
| Min effective positions | 5.33 |
| Avg gross exposure | 2.00x |
| Max gross exposure | 2.00x |
| Position weight breaches | 7 |

Capacity curve:

| Notional | Test Sharpe | Test Return | Avg Cost | Avg Impact | Avg Participation | Max Participation | Breaches | Pass |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| 1,000,000 | -0.25 | -13.84% | 0.13% | 0.00% | 0.01% | 0.07% | 0 | no |
| 5,000,000 | -0.27 | -14.43% | 0.14% | 0.01% | 0.06% | 0.35% | 0 | no |
| 10,000,000 | -0.29 | -15.17% | 0.15% | 0.02% | 0.12% | 0.69% | 0 | no |
| 25,000,000 | -0.35 | -17.35% | 0.18% | 0.05% | 0.30% | 1.74% | 0 | no |

Warnings:
- Position concentration breached 35% on 7 rebalance dates.
- No configured notional passed both participation and positive-Sharpe capacity gates.

## Robustness Diagnostics

| Metric | Mean | 2.5% | 97.5% | Positive Probability |
| --- | ---: | ---: | ---: | ---: |
| Test Sharpe | -0.27 | -1.65 | 1.52 | 37.00% |
| Test IC | -0.0041 | -0.0643 | 0.0629 | 41.50% |

Parameter Sensitivity:

| Variant | Holding | Quantile | Cost Mult | Test IC | Test Sharpe | Test Cost | Test Return |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| h3_q15 | 3 | 15% | 1.00 | 0.0005 | -0.13 | 0.17% | -6.61% |
| h3_q20 | 3 | 20% | 1.00 | 0.0005 | -0.78 | 0.14% | -17.98% |
| h3_q30 | 3 | 30% | 1.00 | 0.0005 | -0.46 | 0.12% | -10.77% |
| h5_q15 | 5 | 15% | 1.00 | -0.0079 | -0.12 | 0.17% | -11.80% |
| h5_q20 | 5 | 20% | 1.00 | -0.0079 | -0.29 | 0.15% | -15.17% |
| h5_q30 | 5 | 30% | 1.00 | -0.0079 | -0.22 | 0.12% | -11.16% |
| h10_q15 | 10 | 15% | 1.00 | -0.0195 | -0.32 | 0.19% | -34.37% |
| h10_q20 | 10 | 20% | 1.00 | -0.0195 | -0.50 | 0.16% | -39.59% |
| h10_q30 | 10 | 30% | 1.00 | -0.0195 | -0.18 | 0.14% | -18.40% |

Cost Sensitivity:

| Variant | Holding | Quantile | Cost Mult | Test IC | Test Sharpe | Test Cost | Test Return |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| cost_0.5x | 5 | 20% | 0.50 | -0.0079 | -0.13 | 0.07% | -9.56% |
| cost_1x | 5 | 20% | 1.00 | -0.0079 | -0.29 | 0.15% | -15.17% |
| cost_2x | 5 | 20% | 2.00 | -0.0079 | -0.60 | 0.30% | -25.39% |

## Baseline Comparison

| Strategy | Test IC | Test Sharpe | Test Max Drawdown | Test Turnover | Test Cost | Test Total Return |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| agent_signal | -0.0079 | -0.29 | -28.13% | 1.62 | 0.15% | -15.17% |
| momentum_20d_only | -0.0437 | -0.76 | -38.94% | 1.72 | 0.16% | -34.60% |
| low_volatility_only | -0.0288 | -1.32 | -58.96% | 1.02 | 0.10% | -54.37% |
| reversal_5d_only | 0.0613 | 0.42 | -23.45% | 3.31 | 0.30% | 14.17% |
| random_cross_section | -0.0001 | -1.34 | -40.71% | 3.27 | 0.30% | -38.08% |

## Stress Tests

| Stress Test | Test IC | Test Sharpe | Test Max Drawdown | Test Turnover | Test Cost | Test Total Return |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| sector_neutral_signal | -0.0089 | -0.25 | -24.44% | 1.51 | 0.14% | -12.32% |
| liquidity_top_80pct | 0.0048 | -0.15 | -30.15% | 1.47 | 0.13% | -11.02% |
| sector_neutral_liquidity_top_80pct | 0.0009 | 0.06 | -22.63% | 1.51 | 0.14% | -2.17% |

## Walk-Forward Validation

| Window | Train Through | Test Range | Obs | IC Mean | Sharpe | Avg Cost | Hit Rate | Total Return |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| wf_01 | 2022-07-05 | 2022-07-12 to 2023-08-29 | 58 | 0.0041 | 0.96 | 0.17% | 50.00% | 26.97% |
| wf_02 | 2023-08-29 | 2023-09-06 to 2024-10-23 | 58 | 0.0045 | -0.63 | 0.17% | 46.55% | -18.66% |
| wf_03 | 2024-10-23 | 2024-10-30 to 2025-12-19 | 58 | -0.0009 | -0.25 | 0.15% | 48.28% | -10.47% |

| Strategy | Windows | Mean Test IC | Mean Sharpe | Mean Cost | Positive IC Windows | Median Total Return |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| agent_signal | 3 | 0.0026 | 0.03 | 0.16% | 66.67% | -10.47% |
| momentum_20d_only | 3 | -0.0183 | -0.33 | 0.17% | 33.33% | -0.61% |
| low_volatility_only | 3 | -0.0387 | -1.89 | 0.11% | 0.00% | -44.70% |
| reversal_5d_only | 3 | 0.0206 | -0.46 | 0.31% | 66.67% | -8.45% |
| random_cross_section | 3 | 0.0032 | -1.60 | 0.31% | 66.67% | -22.27% |
| sector_neutral_signal | 3 | 0.0023 | -0.22 | 0.15% | 33.33% | -9.10% |
| liquidity_top_80pct | 3 | 0.0086 | -0.01 | 0.15% | 66.67% | -2.75% |
| sector_neutral_liquidity_top_80pct | 3 | 0.0009 | -0.23 | 0.14% | 66.67% | 1.08% |

## Interpretation

The signal is not supported out-of-sample in this run. Treat it as rejected until a more robust variant improves IC stability without increasing overfit risk.

The strongest out-of-sample Sharpe is from `reversal_5d_only`, not the agent signal. Treat this as a useful rejection/iteration signal: inspect which factor exposure is carrying the result before adding model complexity.

The signal keeps positive test IC and Sharpe under these stress tests: sector_neutral_liquidity_top_80pct. Compare their drawdowns and turnover before treating this as robust.

Factor diagnostics did not flag high pairwise redundancy among selected exposures.

Robustness diagnostics flag caution: bootstrap Sharpe confidence is weak; bootstrap IC confidence is weak; parameter sensitivity is fragile; high-cost sensitivity erases positive Sharpe.

Capacity diagnostics do not identify a configured notional that passes both participation and positive-Sharpe gates.

Walk-forward validation is not yet stable enough for promotion: inspect the weak windows before adding factor complexity.

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

- Run ID: `yahoo-nasdaq-momentum-low-volatility-20260617T045621Z-da84cab038-f660f305`
- Generated at: `2026-06-17T04:56:21Z`
- Config SHA-256: `da84cab03886d0cc9e6e1c163f8df62172a6d742b7f581f27927aceb470bb2ac`
- Git commit: `69b38c7dc11d716c7d2e4a6e608fd6d01d058996`
- Git branch: `main`
- Git dirty: yes
- Manifest: `results/runs/yahoo-nasdaq-momentum-low-volatility-20260617T045621Z-da84cab038-f660f305/manifest.json`
- Frozen config: `results/runs/yahoo-nasdaq-momentum-low-volatility-20260617T045621Z-da84cab038-f660f305/config.yaml`
