from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from quant_research_agent.backtest.metrics import compute_metric_summary


@dataclass(frozen=True)
class WalkForwardWindow:
    name: str
    train_start: pd.Timestamp
    train_end: pd.Timestamp
    test_start: pd.Timestamp
    test_end: pd.Timestamp
    metrics: dict[str, float]


@dataclass(frozen=True)
class BacktestResult:
    raw_returns: pd.Series
    returns: pd.Series
    positions: pd.DataFrame
    ic_by_date: pd.Series
    turnover: pd.Series
    costs: pd.DataFrame
    metrics: dict[str, dict[str, float]]
    split_date: pd.Timestamp
    validation_start: pd.Timestamp
    holdout_start: pd.Timestamp | None
    walk_forward: list[WalkForwardWindow]


def run_long_short_backtest(
    market_data: pd.DataFrame,
    signal: pd.Series,
    train_fraction: float,
    holding_period: int,
    rebalance_days: int,
    quantile: float,
    transaction_cost_bps: float,
    spread_cost_bps: float = 0.0,
    market_impact_coefficient: float = 0.0,
    portfolio_notional: float = 1_000_000.0,
    borrow_fee_bps: float = 0.0,
    shortable_symbols: list[str] | None = None,
    shortable_by_date: pd.DataFrame | None = None,
    borrow_fee_bps_by_date: pd.DataFrame | None = None,
    walk_forward_windows: int = 0,
    walk_forward_min_train_fraction: float = 0.4,
    holdout_fraction: float = 0.0,
) -> BacktestResult:
    close = market_data["adj_close"].unstack("symbol")
    forward_returns = close.shift(-holding_period) / close - 1.0
    forward_returns = forward_returns.stack().rename("forward_return")

    aligned = pd.concat([signal.rename("signal"), forward_returns], axis=1).dropna()
    rebalance_dates = _rebalance_dates(aligned.index.get_level_values("date").unique(), rebalance_days)
    aligned = aligned.loc[aligned.index.get_level_values("date").isin(rebalance_dates)]

    positions = _build_positions(
        aligned["signal"],
        quantile=quantile,
        shortable_symbols=shortable_symbols,
        shortable_by_date=shortable_by_date,
    )
    raw_returns = _portfolio_forward_returns(positions, aligned["forward_return"])
    turnover = _turnover(positions)
    costs = _transaction_costs(
        market_data=market_data,
        positions=positions,
        turnover=turnover,
        base_cost_bps=transaction_cost_bps,
        spread_cost_bps=spread_cost_bps,
        market_impact_coefficient=market_impact_coefficient,
        portfolio_notional=portfolio_notional,
        borrow_fee_bps=borrow_fee_bps,
        borrow_fee_bps_by_date=borrow_fee_bps_by_date,
        holding_period=holding_period,
    )
    returns = (raw_returns - costs["total_cost"]).rename("strategy_return").dropna()

    ic_by_date = _information_coefficient(aligned)
    realization_dates = _realization_dates(
        decision_dates=returns.index,
        market_dates=close.index,
        holding_period=holding_period,
    )
    split_date, validation_start, holdout_start = _split_boundaries(
        returns.index,
        train_fraction=train_fraction,
        holdout_fraction=holdout_fraction,
    )
    train_metrics = _metric_summary(
        returns=returns.loc[returns.index <= split_date],
        ic_by_date=ic_by_date.loc[ic_by_date.index <= split_date],
        turnover=turnover.loc[turnover.index <= split_date],
        costs=costs.loc[costs.index <= split_date],
        holding_period=holding_period,
    )
    validation_mask = returns.index >= validation_start
    if holdout_start is not None:
        validation_mask &= returns.index < holdout_start
        validation_mask &= realization_dates < holdout_start
    validation_returns = returns.loc[validation_mask]
    if holdout_start is not None and validation_returns.empty:
        raise ValueError(
            "not enough backtest observations for train, validation, and holdout"
        )
    validation_metrics = _metric_summary(
        returns=validation_returns,
        ic_by_date=ic_by_date.reindex(validation_returns.index),
        turnover=turnover.reindex(validation_returns.index),
        costs=costs.reindex(validation_returns.index),
        holding_period=holding_period,
    )
    holdout_returns = (
        returns.loc[returns.index >= holdout_start]
        if holdout_start is not None
        else returns.iloc[0:0]
    )
    holdout_metrics = _metric_summary(
        returns=holdout_returns,
        ic_by_date=ic_by_date.reindex(holdout_returns.index),
        turnover=turnover.reindex(holdout_returns.index),
        costs=costs.reindex(holdout_returns.index),
        holding_period=holding_period,
    )
    metrics = {
        "train": train_metrics,
        "validation": validation_metrics,
        "test": validation_metrics.copy(),
        "holdout": holdout_metrics,
        "full": _metric_summary(
            returns=returns,
            ic_by_date=ic_by_date,
            turnover=turnover,
            costs=costs,
            holding_period=holding_period,
        ),
    }
    pre_holdout_returns = (
        returns.loc[
            (returns.index < holdout_start)
            & (realization_dates < holdout_start)
        ]
        if holdout_start is not None
        else returns
    )
    walk_forward = _walk_forward_metrics(
        returns=pre_holdout_returns,
        ic_by_date=ic_by_date,
        turnover=turnover,
        costs=costs,
        holding_period=holding_period,
        window_count=walk_forward_windows,
        min_train_fraction=walk_forward_min_train_fraction,
    )

    return BacktestResult(
        raw_returns=raw_returns,
        returns=returns,
        positions=positions,
        ic_by_date=ic_by_date,
        turnover=turnover,
        costs=costs,
        metrics=metrics,
        split_date=split_date,
        validation_start=validation_start,
        holdout_start=holdout_start,
        walk_forward=walk_forward,
    )


def _rebalance_dates(dates: pd.Index, rebalance_days: int) -> pd.Index:
    if rebalance_days <= 0:
        raise ValueError("rebalance_days must be positive")
    return pd.Index(sorted(dates))[::rebalance_days]


def _build_positions(
    signal: pd.Series,
    quantile: float,
    shortable_symbols: list[str] | None = None,
    shortable_by_date: pd.DataFrame | None = None,
) -> pd.DataFrame:
    shortable = set(shortable_symbols) if shortable_symbols is not None else None
    frames = []
    for date, date_signal in signal.groupby(level="date"):
        values = date_signal.droplevel("date").dropna()
        if len(values) < 5:
            continue
        long_cutoff = values.quantile(1.0 - quantile)
        short_cutoff = values.quantile(quantile)
        longs = values[values >= long_cutoff].index
        shorts = values[values <= short_cutoff].index
        if shortable is not None:
            shorts = shorts.intersection(pd.Index(sorted(shortable)))
        if shortable_by_date is not None:
            if date not in shortable_by_date.index:
                shorts = pd.Index([])
            else:
                date_shortable = shortable_by_date.reindex(columns=values.index).loc[date].fillna(False)
                shorts = shorts.intersection(date_shortable[date_shortable].index)
        if len(longs) == 0 or len(shorts) == 0:
            continue

        weights = pd.Series(0.0, index=values.index, name=date)
        weights.loc[longs] = 1.0 / len(longs)
        weights.loc[shorts] = -1.0 / len(shorts)
        frames.append(weights)

    if not frames:
        raise ValueError("no rebalance dates had enough assets to build positions")
    positions = pd.DataFrame(frames)
    positions.index.name = "date"
    positions.columns.name = "symbol"
    return positions.sort_index()


def _portfolio_forward_returns(positions: pd.DataFrame, forward_returns: pd.Series) -> pd.Series:
    returns = forward_returns.unstack("symbol").reindex(index=positions.index, columns=positions.columns)
    return (positions * returns).sum(axis=1, min_count=1)


def _turnover(positions: pd.DataFrame) -> pd.Series:
    previous = positions.shift(1).fillna(0.0)
    return (positions - previous).abs().sum(axis=1).rename("turnover")


def _transaction_costs(
    market_data: pd.DataFrame,
    positions: pd.DataFrame,
    turnover: pd.Series,
    base_cost_bps: float,
    spread_cost_bps: float,
    market_impact_coefficient: float,
    portfolio_notional: float,
    borrow_fee_bps: float,
    borrow_fee_bps_by_date: pd.DataFrame | None,
    holding_period: int,
) -> pd.DataFrame:
    close = market_data["adj_close"].unstack("symbol")
    volume = market_data["volume"].unstack("symbol")
    dollar_volume = close * volume
    adv_20d = dollar_volume.rolling(20, min_periods=1).mean().reindex(index=positions.index, columns=positions.columns)

    previous = positions.shift(1).fillna(0.0)
    trades = (positions - previous).abs()
    base_cost = turnover * (base_cost_bps / 10_000.0)
    spread_cost = turnover * (spread_cost_bps / 10_000.0)
    participation = (trades * portfolio_notional) / adv_20d.replace(0, np.nan)
    impact_cost = (trades * participation.fillna(0.0) * market_impact_coefficient).sum(axis=1)
    short_positions = positions.clip(upper=0.0).abs()
    if borrow_fee_bps_by_date is None:
        borrow_fee = pd.DataFrame(borrow_fee_bps, index=positions.index, columns=positions.columns)
    else:
        borrow_fee = borrow_fee_bps_by_date.reindex(index=positions.index, columns=positions.columns).fillna(borrow_fee_bps)
    borrow_cost = (short_positions * (borrow_fee / 10_000.0)).sum(axis=1) * (holding_period / 252.0)
    weighted_participation = (trades * participation.fillna(0.0)).sum(axis=1) / trades.sum(axis=1).replace(0, np.nan)

    costs = pd.DataFrame(
        {
            "base_cost": base_cost,
            "spread_cost": spread_cost,
            "impact_cost": impact_cost,
            "borrow_cost": borrow_cost,
            "average_trade_participation": weighted_participation.fillna(0.0),
            "max_trade_participation": participation.max(axis=1).fillna(0.0),
        }
    )
    costs["total_cost"] = costs["base_cost"] + costs["spread_cost"] + costs["impact_cost"] + costs["borrow_cost"]
    costs.index.name = "date"
    return costs.fillna(0.0)


def _information_coefficient(aligned: pd.DataFrame) -> pd.Series:
    values = {}
    for date, frame in aligned.groupby(level="date"):
        if frame["signal"].nunique() < 2 or frame["forward_return"].nunique() < 2:
            values[date] = np.nan
        else:
            signal_rank = frame["signal"].rank()
            return_rank = frame["forward_return"].rank()
            values[date] = signal_rank.corr(return_rank)
    return pd.Series(values, name="ic").dropna()


def _split_date(index: pd.Index, train_fraction: float) -> pd.Timestamp:
    if len(index) < 4:
        raise ValueError("not enough backtest observations for train/test split")
    split_position = min(max(int(len(index) * train_fraction), 1), len(index) - 2)
    return pd.Timestamp(index[split_position])


def _split_boundaries(
    index: pd.Index,
    train_fraction: float,
    holdout_fraction: float,
) -> tuple[pd.Timestamp, pd.Timestamp, pd.Timestamp | None]:
    if holdout_fraction <= 0.0:
        split_date = _split_date(index, train_fraction)
        validation_index = index[index > split_date]
        return split_date, pd.Timestamp(validation_index[0]), None

    holdout_size = max(1, int(np.ceil(len(index) * holdout_fraction)))
    holdout_position = len(index) - holdout_size
    max_train_position = holdout_position - 2
    if max_train_position < 0:
        raise ValueError(
            "not enough backtest observations for train, validation, and holdout"
        )

    train_position = min(max(int(len(index) * train_fraction), 0), max_train_position)
    validation_position = train_position + 1
    if validation_position >= holdout_position:
        raise ValueError(
            "not enough backtest observations for train, validation, and holdout"
        )

    return (
        pd.Timestamp(index[train_position]),
        pd.Timestamp(index[validation_position]),
        pd.Timestamp(index[holdout_position]),
    )


def _realization_dates(
    decision_dates: pd.Index,
    market_dates: pd.Index,
    holding_period: int,
) -> pd.Series:
    ordered_market_dates = pd.Index(market_dates).sort_values().unique()
    realization_by_decision = pd.Series(
        ordered_market_dates[holding_period:],
        index=ordered_market_dates[:-holding_period],
    )
    return realization_by_decision.reindex(decision_dates)


def _walk_forward_metrics(
    returns: pd.Series,
    ic_by_date: pd.Series,
    turnover: pd.Series,
    costs: pd.DataFrame,
    holding_period: int,
    window_count: int,
    min_train_fraction: float,
) -> list[WalkForwardWindow]:
    if window_count <= 0:
        return []

    returns = returns.sort_index().dropna()
    if len(returns) < 4:
        return []

    min_train_size = min(max(int(len(returns) * min_train_fraction), 1), len(returns) - 1)
    remaining = len(returns) - min_train_size
    if remaining <= 0:
        return []

    actual_window_count = min(window_count, remaining)
    test_size = max(1, remaining // actual_window_count)
    windows: list[WalkForwardWindow] = []

    for index in range(actual_window_count):
        test_start_position = min_train_size + (index * test_size)
        test_end_position = len(returns) if index == actual_window_count - 1 else min(
            min_train_size + ((index + 1) * test_size),
            len(returns),
        )
        if test_start_position >= len(returns) or test_start_position >= test_end_position:
            continue

        train_returns = returns.iloc[:test_start_position]
        test_returns = returns.iloc[test_start_position:test_end_position]
        windows.append(
            WalkForwardWindow(
                name=f"wf_{index + 1:02d}",
                train_start=pd.Timestamp(train_returns.index[0]),
                train_end=pd.Timestamp(train_returns.index[-1]),
                test_start=pd.Timestamp(test_returns.index[0]),
                test_end=pd.Timestamp(test_returns.index[-1]),
                metrics=compute_metric_summary(
                    returns=test_returns,
                    ic_by_date=ic_by_date.reindex(test_returns.index),
                    turnover=turnover.reindex(test_returns.index),
                    holding_period=holding_period,
                )
                | _cost_metric_summary(costs.reindex(test_returns.index)),
            )
        )

    return windows


def _metric_summary(
    returns: pd.Series,
    ic_by_date: pd.Series,
    turnover: pd.Series,
    costs: pd.DataFrame,
    holding_period: int,
) -> dict[str, float]:
    return compute_metric_summary(
        returns=returns,
        ic_by_date=ic_by_date,
        turnover=turnover,
        holding_period=holding_period,
    ) | _cost_metric_summary(costs.reindex(returns.index))


def _cost_metric_summary(costs: pd.DataFrame) -> dict[str, float]:
    costs = costs.fillna(0.0)
    if costs.empty:
        return {
            "average_total_cost": 0.0,
            "average_base_cost": 0.0,
            "average_spread_cost": 0.0,
            "average_impact_cost": 0.0,
            "average_borrow_cost": 0.0,
            "cumulative_total_cost": 0.0,
            "average_trade_participation": 0.0,
            "max_trade_participation": 0.0,
        }
    return {
        "average_total_cost": float(costs["total_cost"].mean()),
        "average_base_cost": float(costs["base_cost"].mean()),
        "average_spread_cost": float(costs["spread_cost"].mean()),
        "average_impact_cost": float(costs["impact_cost"].mean()),
        "average_borrow_cost": float(costs["borrow_cost"].mean()),
        "cumulative_total_cost": float(costs["total_cost"].sum()),
        "average_trade_participation": float(costs["average_trade_participation"].mean()),
        "max_trade_participation": float(costs["max_trade_participation"].max()),
    }
