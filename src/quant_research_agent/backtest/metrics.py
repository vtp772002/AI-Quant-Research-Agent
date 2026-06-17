from __future__ import annotations

import math

import numpy as np
import pandas as pd


def compute_metric_summary(
    returns: pd.Series,
    ic_by_date: pd.Series,
    turnover: pd.Series,
    holding_period: int,
) -> dict[str, float]:
    returns = returns.dropna()
    ic_by_date = ic_by_date.dropna()
    turnover = turnover.reindex(returns.index).dropna()
    periods_per_year = 252.0 / max(holding_period, 1)

    return {
        "observations": float(len(returns)),
        "ic_mean": _safe_mean(ic_by_date),
        "ic_std": _safe_std(ic_by_date),
        "ic_tstat": _t_stat(ic_by_date),
        "ic_hit_rate": _hit_rate(ic_by_date),
        "sharpe": _sharpe(returns, periods_per_year),
        "max_drawdown": _max_drawdown(returns),
        "average_turnover": _safe_mean(turnover),
        "total_return": _total_return(returns),
        "mean_period_return": _safe_mean(returns),
    }


def _safe_mean(values: pd.Series) -> float:
    return float(values.mean()) if len(values) else 0.0


def _safe_std(values: pd.Series) -> float:
    return float(values.std(ddof=1)) if len(values) > 1 else 0.0


def _t_stat(values: pd.Series) -> float:
    if len(values) <= 1:
        return 0.0
    std = values.std(ddof=1)
    if std == 0 or math.isnan(std):
        return 0.0
    return float(values.mean() / (std / np.sqrt(len(values))))


def _hit_rate(values: pd.Series) -> float:
    return float((values > 0).mean()) if len(values) else 0.0


def _sharpe(returns: pd.Series, periods_per_year: float) -> float:
    if len(returns) <= 1:
        return 0.0
    std = returns.std(ddof=1)
    if std == 0 or math.isnan(std):
        return 0.0
    return float((returns.mean() / std) * np.sqrt(periods_per_year))


def _max_drawdown(returns: pd.Series) -> float:
    if returns.empty:
        return 0.0
    equity = (1.0 + returns).cumprod()
    drawdown = equity / equity.cummax() - 1.0
    return float(drawdown.min())


def _total_return(returns: pd.Series) -> float:
    if returns.empty:
        return 0.0
    return float((1.0 + returns).prod() - 1.0)
