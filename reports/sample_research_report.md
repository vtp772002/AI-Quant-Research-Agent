# AI Quant Research Report

## Experiment

- Name: `momentum_low_volatility_demo`
- Universe: 20 assets from `synthetic`
- Date range: 2020-01-01 to 2024-12-31
- Holding period: 5 trading days
- Rebalance: every 5 trading days
- Long/short quantile: 20%

## Hypothesis

Assets with stronger recent momentum and lower realized risk should outperform over the next 5 trading days.

Expected direction: positive exposure to [momentum_20d, momentum_60d], negative exposure to [volatility_20d, drawdown_20d].

## Signal

Positive factors: momentum_20d, momentum_60d

Negative factors: volatility_20d, drawdown_20d

Signal is built from cross-sectional percentile ranks so each rebalance compares assets only against the active universe on that date.

## Results

| Split | IC Mean | Sharpe | Max Drawdown | Avg Turnover | Total Return |
| --- | ---: | ---: | ---: | ---: | ---: |
| Train | 0.0186 | 0.53 | -29.04% | 1.55 | 37.04% |
| Test | 0.0253 | 0.17 | -22.26% | 1.44 | 2.07% |
| Full | 0.0206 | 0.43 | -29.04% | 1.52 | 39.88% |

## Baseline Comparison

| Strategy | Test IC | Test Sharpe | Test Max Drawdown | Test Turnover | Test Total Return |
| --- | ---: | ---: | ---: | ---: | ---: |
| agent_signal | 0.0253 | 0.17 | -22.26% | 1.44 | 2.07% |
| momentum_20d_only | 0.0375 | 0.47 | -23.07% | 1.64 | 12.73% |
| low_volatility_only | -0.0258 | -1.22 | -45.10% | 0.93 | -34.94% |
| reversal_5d_only | -0.0582 | -2.05 | -60.41% | 3.03 | -51.19% |
| random_cross_section | -0.0432 | -1.33 | -37.23% | 3.12 | -37.36% |

## Walk-Forward Validation

| Window | Train Through | Test Range | Obs | IC Mean | Sharpe | Hit Rate | Total Return |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: |
| wf_01 | 2022-02-09 | 2022-02-16 to 2023-01-18 | 49 | 0.0152 | -0.24 | 53.06% | -7.90% |
| wf_02 | 2023-01-18 | 2023-01-25 to 2023-12-27 | 49 | 0.0298 | 0.88 | 46.94% | 18.52% |
| wf_03 | 2023-12-27 | 2024-01-03 to 2024-12-18 | 51 | 0.0421 | 1.02 | 52.94% | 20.09% |

| Strategy | Windows | Mean Test IC | Mean Sharpe | Positive IC Windows | Median Total Return |
| --- | ---: | ---: | ---: | ---: | ---: |
| agent_signal | 3 | 0.0290 | 0.56 | 100.00% | 18.52% |
| momentum_20d_only | 3 | 0.0205 | 0.10 | 100.00% | -8.96% |
| low_volatility_only | 3 | -0.0059 | -0.48 | 33.33% | -12.94% |
| reversal_5d_only | 3 | -0.0412 | -1.99 | 0.00% | -28.81% |
| random_cross_section | 3 | -0.0041 | -0.38 | 33.33% | -19.17% |

## Interpretation

The signal is a candidate for deeper research: out-of-sample IC and Sharpe are positive. The next question is whether the effect survives real data, costs, and neutralization.

The strongest out-of-sample Sharpe is from `momentum_20d_only`, not the agent signal. Treat this as a useful rejection/iteration signal: inspect which factor exposure is carrying the result before adding model complexity.

Walk-forward validation supports further research: most agent-signal windows have positive IC and the average window Sharpe is positive.

The train/test split is chronological. Test-period results are the primary evidence because they are less exposed to factor selection bias.

## Limitations

- Synthetic data is useful for deterministic validation but is not investment evidence.
- v1 uses a simple long-short ranking portfolio without sector neutralization.
- Transaction costs are modeled as proportional turnover costs only.
- No borrow constraints, liquidity caps, corporate actions, or survivorship controls are included yet.

## Next Experiments

- Run the same signal on Yahoo Finance data for a real equity universe.
- Add factor correlation and redundancy analysis before combining signals.
- Stress-test promising factors with neutralization and liquidity constraints.
- Compare this factor against pure momentum, pure low volatility, and reversal baselines.
