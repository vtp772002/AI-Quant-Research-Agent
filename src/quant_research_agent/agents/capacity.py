from __future__ import annotations

from dataclasses import dataclass, field

import pandas as pd

from quant_research_agent.backtest.engine import BacktestResult, run_long_short_backtest
from quant_research_agent.config import AppConfig
from quant_research_agent.data.borrow import BorrowAvailability


@dataclass(frozen=True)
class ConcentrationSummary:
    max_single_name_weight: float
    average_single_name_weight: float
    average_effective_positions: float
    min_effective_positions: float
    average_gross_exposure: float
    max_gross_exposure: float
    position_weight_breach_count: int


@dataclass(frozen=True)
class CapacityPoint:
    notional: float
    test_sharpe: float
    test_total_return: float
    average_total_cost: float
    average_impact_cost: float
    average_trade_participation: float
    max_trade_participation: float
    participation_breach_count: int
    passes_participation_limit: bool
    passes_positive_sharpe: bool


@dataclass(frozen=True)
class CapacityDiagnostics:
    concentration: ConcentrationSummary
    capacity_curve: list[CapacityPoint]
    max_capacity_notional: float | None
    warnings: list[str] = field(default_factory=list)


def compute_capacity_diagnostics(
    market_data: pd.DataFrame,
    signal: pd.Series,
    backtest: BacktestResult,
    config: AppConfig,
    borrow_availability: BorrowAvailability | None = None,
) -> CapacityDiagnostics:
    concentration = _concentration_summary(
        backtest=backtest,
        max_position_weight=config.experiment.capacity.max_position_weight,
    )
    curve = _capacity_curve(
        market_data=market_data,
        signal=signal,
        config=config,
        borrow_availability=borrow_availability,
    )
    max_capacity = _max_capacity_notional(curve)
    warnings = _capacity_warnings(
        concentration=concentration,
        curve=curve,
        max_capacity=max_capacity,
        config=config,
    )
    return CapacityDiagnostics(
        concentration=concentration,
        capacity_curve=curve,
        max_capacity_notional=max_capacity,
        warnings=warnings,
    )


def _concentration_summary(backtest: BacktestResult, max_position_weight: float) -> ConcentrationSummary:
    weights = backtest.positions.abs()
    gross_exposure = weights.sum(axis=1)
    max_weight_by_date = weights.max(axis=1)
    weight_square_sum = (weights**2).sum(axis=1).replace(0.0, pd.NA)
    effective_positions = (gross_exposure**2 / weight_square_sum).dropna()
    return ConcentrationSummary(
        max_single_name_weight=float(max_weight_by_date.max()) if not max_weight_by_date.empty else 0.0,
        average_single_name_weight=float(max_weight_by_date.mean()) if not max_weight_by_date.empty else 0.0,
        average_effective_positions=float(effective_positions.mean()) if not effective_positions.empty else 0.0,
        min_effective_positions=float(effective_positions.min()) if not effective_positions.empty else 0.0,
        average_gross_exposure=float(gross_exposure.mean()) if not gross_exposure.empty else 0.0,
        max_gross_exposure=float(gross_exposure.max()) if not gross_exposure.empty else 0.0,
        position_weight_breach_count=int((max_weight_by_date > max_position_weight).sum()),
    )


def _capacity_curve(
    market_data: pd.DataFrame,
    signal: pd.Series,
    config: AppConfig,
    borrow_availability: BorrowAvailability | None,
) -> list[CapacityPoint]:
    notionals = config.experiment.capacity.notionals
    if not notionals:
        return []

    points: list[CapacityPoint] = []
    for notional in notionals:
        result = run_long_short_backtest(
            market_data=market_data,
            signal=signal,
            train_fraction=config.experiment.train_fraction,
            holding_period=config.experiment.backtest.holding_period,
            rebalance_days=config.experiment.backtest.rebalance_days,
            quantile=config.experiment.backtest.quantile,
            transaction_cost_bps=config.experiment.backtest.transaction_cost_bps,
            holdout_fraction=(
                config.experiment.validation.research_validity.holdout_fraction
                if config.experiment.validation.research_validity.enabled
                else 0.0
            ),
            spread_cost_bps=config.experiment.backtest.spread_cost_bps,
            market_impact_coefficient=config.experiment.backtest.market_impact_coefficient,
            portfolio_notional=notional,
            borrow_fee_bps=config.experiment.shorting.borrow_fee_bps,
            shortable_symbols=config.experiment.shorting.shortable_symbols,
            shortable_by_date=borrow_availability.shortable if borrow_availability is not None else None,
            borrow_fee_bps_by_date=borrow_availability.borrow_fee_bps if borrow_availability is not None else None,
        )
        test = result.metrics["test"]
        validation_costs = result.costs.loc[
            result.costs.index >= result.validation_start
        ]
        if result.holdout_start is not None:
            validation_costs = validation_costs.loc[
                validation_costs.index < result.holdout_start
            ]
        breach_count = int(
            (
                validation_costs["max_trade_participation"]
                > config.experiment.capacity.max_trade_participation
            ).sum()
        )
        points.append(
            CapacityPoint(
                notional=notional,
                test_sharpe=test["sharpe"],
                test_total_return=test["total_return"],
                average_total_cost=test["average_total_cost"],
                average_impact_cost=test["average_impact_cost"],
                average_trade_participation=test["average_trade_participation"],
                max_trade_participation=test["max_trade_participation"],
                participation_breach_count=breach_count,
                passes_participation_limit=breach_count == 0,
                passes_positive_sharpe=test["sharpe"] > 0.0,
            )
        )
    return points


def _max_capacity_notional(curve: list[CapacityPoint]) -> float | None:
    passing = [
        point.notional
        for point in curve
        if point.passes_participation_limit and point.passes_positive_sharpe
    ]
    if not passing:
        return None
    return float(max(passing))


def _capacity_warnings(
    concentration: ConcentrationSummary,
    curve: list[CapacityPoint],
    max_capacity: float | None,
    config: AppConfig,
) -> list[str]:
    warnings: list[str] = []
    if concentration.position_weight_breach_count:
        warnings.append(
            f"Position concentration breached {config.experiment.capacity.max_position_weight:.0%} on "
            f"{concentration.position_weight_breach_count} rebalance dates."
        )
    if curve and max_capacity is None:
        warnings.append("No configured notional passed both participation and positive-Sharpe capacity gates.")
    breached = [point for point in curve if not point.passes_participation_limit]
    if breached:
        first = min(breached, key=lambda item: item.notional)
        warnings.append(
            f"Trade participation first breached {config.experiment.capacity.max_trade_participation:.0%} "
            f"at notional {first.notional:,.0f}."
        )
    return warnings
