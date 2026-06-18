from __future__ import annotations

import pandas as pd

from quant_research_agent.backtest.engine import BacktestResult, run_long_short_backtest
from quant_research_agent.config import AppConfig
from quant_research_agent.data.borrow import BorrowAvailability


def evaluate_stress_tests(
    market_data: pd.DataFrame,
    factors: pd.DataFrame,
    signal: pd.Series,
    config: AppConfig,
    borrow_availability: BorrowAvailability | None = None,
) -> dict[str, BacktestResult]:
    stress_results: dict[str, BacktestResult] = {}
    neutralized_signal: pd.Series | None = None
    liquidity_signal: pd.Series | None = None

    if config.experiment.stress_tests.neutralization.enabled:
        neutralized_signal = _sector_neutralize_signal(signal, config.data.sectors or {})
        stress_results["sector_neutral_signal"] = _run_backtest(market_data, neutralized_signal, config, borrow_availability)

    if config.experiment.stress_tests.liquidity.enabled:
        liquidity_signal = _apply_liquidity_filter(
            signal=signal,
            dollar_volume=factors["dollar_volume_20d"],
            min_rank=config.experiment.stress_tests.liquidity.min_dollar_volume_rank,
        )
        stress_results[_liquidity_strategy_name(config)] = _run_backtest(market_data, liquidity_signal, config, borrow_availability)

    if neutralized_signal is not None and liquidity_signal is not None:
        combined_signal = _apply_liquidity_filter(
            signal=neutralized_signal,
            dollar_volume=factors["dollar_volume_20d"],
            min_rank=config.experiment.stress_tests.liquidity.min_dollar_volume_rank,
        )
        stress_results[f"sector_neutral_{_liquidity_strategy_name(config)}"] = _run_backtest(
            market_data,
            combined_signal,
            config,
            borrow_availability,
        )

    return stress_results


def _run_backtest(
    market_data: pd.DataFrame,
    signal: pd.Series,
    config: AppConfig,
    borrow_availability: BorrowAvailability | None,
) -> BacktestResult:
    return run_long_short_backtest(
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
        portfolio_notional=config.experiment.backtest.portfolio_notional,
        borrow_fee_bps=config.experiment.shorting.borrow_fee_bps,
        shortable_symbols=config.experiment.shorting.shortable_symbols,
        shortable_by_date=borrow_availability.shortable if borrow_availability is not None else None,
        borrow_fee_bps_by_date=borrow_availability.borrow_fee_bps if borrow_availability is not None else None,
        walk_forward_windows=config.experiment.validation.walk_forward.window_count,
        walk_forward_min_train_fraction=config.experiment.validation.walk_forward.min_train_fraction,
    )


def _sector_neutralize_signal(signal: pd.Series, sectors: dict[str, str]) -> pd.Series:
    symbols = set(signal.index.get_level_values("symbol"))
    missing = sorted(symbol for symbol in symbols if symbol not in sectors)
    if missing:
        raise ValueError(f"sector neutralization requires data.sectors for all symbols; missing {missing}")

    wide_signal = signal.unstack("symbol")
    sector_lookup = pd.Series(sectors)
    neutralized = wide_signal.copy()
    for sector in sorted(sector_lookup.loc[list(wide_signal.columns)].unique()):
        columns = sector_lookup[sector_lookup == sector].index.intersection(wide_signal.columns)
        neutralized.loc[:, columns] = wide_signal.loc[:, columns].sub(wide_signal.loc[:, columns].mean(axis=1), axis=0)

    stacked = neutralized.stack().rename("signal")
    stacked.index.names = ["date", "symbol"]
    return stacked.dropna()


def _apply_liquidity_filter(signal: pd.Series, dollar_volume: pd.Series, min_rank: float) -> pd.Series:
    liquidity_rank = dollar_volume.groupby(level="date").rank(pct=True)
    eligible = liquidity_rank >= min_rank
    return signal.reindex(eligible.index).where(eligible).dropna().rename("signal")


def _liquidity_strategy_name(config: AppConfig) -> str:
    retained = int(round((1.0 - config.experiment.stress_tests.liquidity.min_dollar_volume_rank) * 100))
    return f"liquidity_top_{retained}pct"
