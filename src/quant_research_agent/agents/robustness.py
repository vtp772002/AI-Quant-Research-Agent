from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from quant_research_agent.backtest.engine import BacktestResult, run_long_short_backtest
from quant_research_agent.config import AppConfig
from quant_research_agent.data.borrow import BorrowAvailability


@dataclass(frozen=True)
class BootstrapSummary:
    iterations: int
    seed: int
    sharpe_mean: float
    sharpe_ci_low: float
    sharpe_ci_high: float
    ic_mean: float
    ic_ci_low: float
    ic_ci_high: float
    positive_sharpe_probability: float
    positive_ic_probability: float


@dataclass(frozen=True)
class SensitivityResult:
    name: str
    holding_period: int
    quantile: float
    cost_multiplier: float
    metrics: dict[str, float]


@dataclass(frozen=True)
class RobustnessDiagnostics:
    bootstrap: BootstrapSummary | None
    parameter_sensitivity: list[SensitivityResult]
    cost_sensitivity: list[SensitivityResult]


def compute_robustness_diagnostics(
    market_data: pd.DataFrame,
    signal: pd.Series,
    backtest: BacktestResult,
    config: AppConfig,
    borrow_availability: BorrowAvailability | None = None,
) -> RobustnessDiagnostics:
    return RobustnessDiagnostics(
        bootstrap=_bootstrap_summary(backtest=backtest, config=config),
        parameter_sensitivity=_parameter_sensitivity(
            market_data=market_data,
            signal=signal,
            config=config,
            borrow_availability=borrow_availability,
        ),
        cost_sensitivity=_cost_sensitivity(
            market_data=market_data,
            signal=signal,
            config=config,
            borrow_availability=borrow_availability,
        ),
    )


def _bootstrap_summary(backtest: BacktestResult, config: AppConfig) -> BootstrapSummary | None:
    iterations = config.experiment.robustness.bootstrap_iterations
    if iterations <= 0:
        return None

    test_returns = backtest.returns.loc[backtest.returns.index > backtest.split_date].dropna()
    test_ic = backtest.ic_by_date.loc[backtest.ic_by_date.index > backtest.split_date].dropna()
    if len(test_returns) < 2 or len(test_ic) < 2:
        return None

    rng = np.random.default_rng(config.experiment.robustness.bootstrap_seed)
    periods_per_year = 252.0 / max(config.experiment.backtest.holding_period, 1)
    sharpe_values = []
    ic_values = []
    returns_array = test_returns.to_numpy()
    ic_array = test_ic.to_numpy()
    for _ in range(iterations):
        sampled_returns = rng.choice(returns_array, size=len(returns_array), replace=True)
        sampled_ic = rng.choice(ic_array, size=len(ic_array), replace=True)
        sharpe_values.append(_sharpe(sampled_returns, periods_per_year))
        ic_values.append(float(sampled_ic.mean()))

    sharpe = np.array(sharpe_values)
    ic = np.array(ic_values)
    return BootstrapSummary(
        iterations=iterations,
        seed=config.experiment.robustness.bootstrap_seed,
        sharpe_mean=float(sharpe.mean()),
        sharpe_ci_low=float(np.quantile(sharpe, 0.025)),
        sharpe_ci_high=float(np.quantile(sharpe, 0.975)),
        ic_mean=float(ic.mean()),
        ic_ci_low=float(np.quantile(ic, 0.025)),
        ic_ci_high=float(np.quantile(ic, 0.975)),
        positive_sharpe_probability=float((sharpe > 0).mean()),
        positive_ic_probability=float((ic > 0).mean()),
    )


def _parameter_sensitivity(
    market_data: pd.DataFrame,
    signal: pd.Series,
    config: AppConfig,
    borrow_availability: BorrowAvailability | None,
) -> list[SensitivityResult]:
    holding_periods = config.experiment.robustness.holding_periods
    quantiles = config.experiment.robustness.quantiles
    if not holding_periods or not quantiles:
        return []

    results: list[SensitivityResult] = []
    for holding_period in holding_periods:
        for quantile in quantiles:
            result = _run_variant(
                market_data=market_data,
                signal=signal,
                config=config,
                holding_period=holding_period,
                quantile=quantile,
                cost_multiplier=1.0,
                borrow_availability=borrow_availability,
            )
            results.append(
                SensitivityResult(
                    name=f"h{holding_period}_q{int(quantile * 100)}",
                    holding_period=holding_period,
                    quantile=quantile,
                    cost_multiplier=1.0,
                    metrics=result.metrics["test"],
                )
            )
    return results


def _cost_sensitivity(
    market_data: pd.DataFrame,
    signal: pd.Series,
    config: AppConfig,
    borrow_availability: BorrowAvailability | None,
) -> list[SensitivityResult]:
    multipliers = config.experiment.robustness.cost_multipliers
    if not multipliers:
        return []

    results: list[SensitivityResult] = []
    for multiplier in multipliers:
        result = _run_variant(
            market_data=market_data,
            signal=signal,
            config=config,
            holding_period=config.experiment.backtest.holding_period,
            quantile=config.experiment.backtest.quantile,
            cost_multiplier=multiplier,
            borrow_availability=borrow_availability,
        )
        results.append(
            SensitivityResult(
                name=f"cost_{multiplier:g}x",
                holding_period=config.experiment.backtest.holding_period,
                quantile=config.experiment.backtest.quantile,
                cost_multiplier=multiplier,
                metrics=result.metrics["test"],
            )
        )
    return results


def _run_variant(
    market_data: pd.DataFrame,
    signal: pd.Series,
    config: AppConfig,
    holding_period: int,
    quantile: float,
    cost_multiplier: float,
    borrow_availability: BorrowAvailability | None,
) -> BacktestResult:
    return run_long_short_backtest(
        market_data=market_data,
        signal=signal,
        train_fraction=config.experiment.train_fraction,
        holding_period=holding_period,
        rebalance_days=config.experiment.backtest.rebalance_days,
        quantile=quantile,
        transaction_cost_bps=config.experiment.backtest.transaction_cost_bps * cost_multiplier,
        spread_cost_bps=config.experiment.backtest.spread_cost_bps * cost_multiplier,
        market_impact_coefficient=config.experiment.backtest.market_impact_coefficient * cost_multiplier,
        portfolio_notional=config.experiment.backtest.portfolio_notional,
        borrow_fee_bps=config.experiment.shorting.borrow_fee_bps * cost_multiplier,
        shortable_symbols=config.experiment.shorting.shortable_symbols,
        shortable_by_date=borrow_availability.shortable if borrow_availability is not None else None,
        borrow_fee_bps_by_date=(
            borrow_availability.borrow_fee_bps * cost_multiplier if borrow_availability is not None else None
        ),
    )


def _sharpe(returns: np.ndarray, periods_per_year: float) -> float:
    if len(returns) <= 1:
        return 0.0
    std = returns.std(ddof=1)
    if std == 0 or np.isnan(std):
        return 0.0
    return float((returns.mean() / std) * np.sqrt(periods_per_year))
