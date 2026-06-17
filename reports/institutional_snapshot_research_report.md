# AI Quant Research Report

## Experiment

- Name: `institutional_snapshot_momentum_low_volatility`
- Universe: 8 assets from `csv_snapshot`
- Date range: 2020-01-01 to 2022-12-31
- Holding period: 5 trading days
- Rebalance: every 5 trading days
- Long/short quantile: 25%
- Borrow fee: 75.0 bps annualized
- Shortable universe: 6 configured symbols
- Locate history: `configs/../data/golden/borrow_availability_demo.csv`

## Data Integrity

- Source: `csv_snapshot`
- Universe source: `csv:configs/institutional_snapshot_membership_demo.csv`
- Membership rows: 8
- Requested symbols: 8
- Observed symbols: 8
- Date rows: 783
- Panel rows: 6264
- Point-in-time universe: yes
- Survivorship-bias-free: yes
- Corporate actions institutional-grade: yes
- Snapshot dataset: `institutional-golden-demo-v1`
- Snapshot vendor: `InternalGolden`
- Snapshot as-of: `2023-01-03`
- Snapshot manifest: `configs/../data/golden/institutional_ohlcv_snapshot.yaml`
- Snapshot hash valid: yes
- Snapshot row count valid: yes
- Snapshot symbol set valid: yes
- Snapshot date range valid: yes

| Symbol | Observations | Coverage | Missing Rows | Zero Volume | Bad Prices | Extreme Returns | Stale Prices |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| AAA | 783 | 100.00% | 0 | 0 | 0 | 0 | 0 |
| BBB | 783 | 100.00% | 0 | 0 | 0 | 0 | 0 |
| CCC | 783 | 100.00% | 0 | 0 | 0 | 0 | 0 |
| DDD | 783 | 100.00% | 0 | 0 | 0 | 0 | 0 |
| EEE | 783 | 100.00% | 0 | 0 | 0 | 0 | 0 |
| FFF | 783 | 100.00% | 0 | 0 | 0 | 0 | 0 |
| GGG | 783 | 100.00% | 0 | 0 | 0 | 0 | 0 |
| HHH | 783 | 100.00% | 0 | 0 | 0 | 0 | 0 |

No data integrity warnings were detected.

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
| momentum_20d | 6104 | 97.45% | 2.55% |
| momentum_60d | 5784 | 92.34% | 7.66% |
| volatility_20d | 6104 | 97.45% | 2.55% |
| drawdown_20d | 6112 | 97.57% | 2.43% |

Pairs above absolute Spearman correlation of 0.75:

| Factor A | Factor B | Spearman Corr |
| --- | --- | ---: |
| momentum_20d | drawdown_20d | 0.8114 |

## Results

| Split | IC Mean | Sharpe | Max Drawdown | Avg Turnover | Avg Cost | Total Return |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Train | 0.0070 | -0.27 | -35.71% | 1.59 | 0.24% | -23.24% |
| Test | 0.0358 | 0.76 | -19.13% | 1.97 | 0.31% | 15.93% |
| Full | 0.0156 | 0.02 | -35.71% | 1.70 | 0.26% | -11.01% |

## Execution Costs

| Component | Train | Test | Full |
| --- | ---: | ---: | ---: |
| Avg base cost | 0.08% | 0.10% | 0.08% |
| Avg spread cost | 0.03% | 0.04% | 0.03% |
| Avg impact cost | 0.09% | 0.13% | 0.10% |
| Avg borrow cost | 0.04% | 0.04% | 0.04% |
| Avg total cost | 0.24% | 0.31% | 0.26% |
| Cumulative cost | 23.12% | 12.51% | 35.63% |
| Avg trade participation | 0.48% | 0.58% | 0.51% |
| Max trade participation | 3.01% | 2.41% | 3.01% |

## Borrow Availability

| Field | Value |
| --- | ---: |
| Rows | 6264 |
| Symbols | 8 |
| Date range | 2020-01-01 to 2022-12-30 |
| Coverage | 100.00% |
| Unavailable rows | 1698 |
| Hard-to-borrow rows | 783 |
| Avg borrow fee | 241.2 bps |
| Max borrow fee | 950.0 bps |

Warnings:
- Borrow availability marks 1698 date-symbol rows as not shortable.
- Borrow availability flags 783 hard-to-borrow rows at or above 500 bps.

## Capacity Diagnostics

| Metric | Value |
| --- | ---: |
| Max single-name weight | 100.00% |
| Avg single-name max weight | 68.75% |
| Avg effective positions | 3.79 |
| Min effective positions | 2.67 |
| Avg gross exposure | 2.00x |
| Max gross exposure | 2.00x |
| Position weight breaches | 133 |

Capacity curve:

| Notional | Test Sharpe | Test Return | Avg Cost | Avg Impact | Avg Participation | Max Participation | Breaches | Pass |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| 1,000,000 | 0.95 | 21.54% | 0.19% | 0.01% | 0.06% | 0.24% | 0 | yes |
| 5,000,000 | 0.87 | 19.02% | 0.25% | 0.07% | 0.29% | 1.20% | 0 | yes |
| 10,000,000 | 0.76 | 15.93% | 0.31% | 0.13% | 0.58% | 2.41% | 0 | yes |
| 25,000,000 | 0.43 | 7.12% | 0.51% | 0.33% | 1.45% | 6.02% | 0 | yes |

Estimated capacity: 25,000,000 notional under configured gates.

Warnings:
- Position concentration breached 35% on 133 rebalance dates.

## Robustness Diagnostics

| Metric | Mean | 2.5% | 97.5% | Positive Probability |
| --- | ---: | ---: | ---: | ---: |
| Test Sharpe | 0.95 | -1.38 | 3.11 | 80.50% |
| Test IC | 0.0380 | -0.0572 | 0.1296 | 79.50% |

Parameter Sensitivity:

| Variant | Holding | Quantile | Cost Mult | Test IC | Test Sharpe | Test Cost | Test Return |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| h3_q20 | 3 | 20% | 1.00 | -0.0512 | -1.29 | 0.30% | -20.18% |
| h3_q25 | 3 | 25% | 1.00 | -0.0512 | -1.29 | 0.30% | -20.18% |
| h5_q20 | 5 | 20% | 1.00 | 0.0358 | 0.76 | 0.31% | 15.93% |
| h5_q25 | 5 | 25% | 1.00 | 0.0358 | 0.76 | 0.31% | 15.93% |
| h10_q20 | 10 | 20% | 1.00 | 0.0084 | -0.15 | 0.34% | -11.63% |
| h10_q25 | 10 | 25% | 1.00 | 0.0084 | -0.15 | 0.34% | -11.63% |

Cost Sensitivity:

| Variant | Holding | Quantile | Cost Mult | Test IC | Test Sharpe | Test Cost | Test Return |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| cost_0.5x | 5 | 25% | 0.50 | 0.0358 | 1.02 | 0.16% | 23.36% |
| cost_1x | 5 | 25% | 1.00 | 0.0358 | 0.76 | 0.31% | 15.93% |
| cost_2x | 5 | 25% | 2.00 | 0.0358 | 0.24 | 0.63% | 2.35% |

## Baseline Comparison

| Strategy | Test IC | Test Sharpe | Test Max Drawdown | Test Turnover | Test Cost | Test Total Return |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| agent_signal | 0.0358 | 0.76 | -19.13% | 1.97 | 0.31% | 15.93% |
| momentum_20d_only | -0.0227 | -1.07 | -44.06% | 1.85 | 0.33% | -33.82% |
| low_volatility_only | 0.0119 | -0.09 | -17.04% | 1.24 | 0.20% | -5.32% |
| random_cross_section | -0.0153 | -0.76 | -26.28% | 3.15 | 0.57% | -18.72% |

## Stress Tests

| Stress Test | Test IC | Test Sharpe | Test Max Drawdown | Test Turnover | Test Cost | Test Total Return |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| sector_neutral_signal | 0.0251 | -0.70 | -45.75% | 1.64 | 0.27% | -23.52% |
| liquidity_top_80pct | 0.0491 | 1.10 | -15.87% | 1.91 | 0.29% | 25.85% |
| sector_neutral_liquidity_top_80pct | 0.0438 | -0.26 | -29.60% | 1.46 | 0.24% | -10.16% |

## Walk-Forward Validation

| Window | Train Through | Test Range | Obs | IC Mean | Sharpe | Avg Cost | Hit Rate | Total Return |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| wf_01 | 2021-05-05 | 2021-05-12 to 2021-11-10 | 27 | 0.1230 | 2.25 | 0.20% | 59.26% | 42.19% |
| wf_02 | 2021-11-10 | 2021-11-17 to 2022-05-18 | 27 | 0.1354 | 0.82 | 0.26% | 77.78% | 12.29% |
| wf_03 | 2022-05-18 | 2022-05-25 to 2022-12-21 | 28 | -0.0356 | -0.50 | 0.34% | 42.86% | -10.72% |

| Strategy | Windows | Mean Test IC | Mean Sharpe | Mean Cost | Positive IC Windows | Median Total Return |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| agent_signal | 3 | 0.0743 | 0.86 | 0.27% | 66.67% | 12.29% |
| momentum_20d_only | 3 | 0.0528 | 1.00 | 0.26% | 66.67% | 26.71% |
| low_volatility_only | 3 | 0.0155 | -0.03 | 0.23% | 66.67% | -11.24% |
| random_cross_section | 3 | 0.0025 | -0.49 | 0.58% | 33.33% | -18.21% |
| sector_neutral_signal | 3 | 0.0459 | 0.16 | 0.25% | 66.67% | -4.97% |
| liquidity_top_80pct | 3 | 0.0838 | 1.45 | 0.24% | 66.67% | 6.43% |
| sector_neutral_liquidity_top_80pct | 3 | 0.0480 | 0.34 | 0.25% | 100.00% | -9.28% |

## Interpretation

The signal is a candidate for deeper research: out-of-sample IC and Sharpe are positive. The next question is whether the effect survives real data, costs, and neutralization.

The agent signal has the strongest out-of-sample Sharpe among configured strategies. Its test IC is 0.0358, so the next validation target is stability across real data and walk-forward windows.

The signal keeps positive test IC and Sharpe under these stress tests: liquidity_top_80pct. Compare their drawdowns and turnover before treating this as robust.

Factor diagnostics flagged potentially redundant exposures. The strongest pair is `momentum_20d` and `drawdown_20d` with Spearman correlation 0.8114; simplify or orthogonalize before adding more factors.

Robustness diagnostics flag caution: parameter sensitivity is fragile.

Capacity diagnostics estimate that the signal passes configured gates up to 25,000,000 notional. Treat this as a research approximation because the model uses average dollar volume, not live order book depth.

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

- Run ID: `institutional-snapshot-momentum-low-volatility-20260617T045621Z-cb436efc02-a6fc213a`
- Generated at: `2026-06-17T04:56:21Z`
- Config SHA-256: `cb436efc02780e9f4791ede8cbe6cc2987c7269815168576ff8c05cc08f95377`
- Git commit: `69b38c7dc11d716c7d2e4a6e608fd6d01d058996`
- Git branch: `main`
- Git dirty: yes
- Manifest: `results/runs/institutional-snapshot-momentum-low-volatility-20260617T045621Z-cb436efc02-a6fc213a/manifest.json`
- Frozen config: `results/runs/institutional-snapshot-momentum-low-volatility-20260617T045621Z-cb436efc02-a6fc213a/config.yaml`
