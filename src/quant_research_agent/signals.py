from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pandas as pd

from quant_research_agent.agents.factor_agent import FactorAgent
from quant_research_agent.config import AppConfig
from quant_research_agent.data.borrow import load_borrow_availability
from quant_research_agent.data.loader import MarketDataRequest, load_market_data
from quant_research_agent.data.universe import apply_universe_membership, resolve_universe
from quant_research_agent.factors.registry import compute_factor_library
from quant_research_agent.reproducibility import _slug
from quant_research_agent.data.snapshot import file_sha256


@dataclass(frozen=True)
class SignalAsOfRow:
    symbol: str
    signal_score: float
    rank: int
    target_weight: float
    reason: str
    risk_status: str
    data_timestamp: str
    model_version: str


@dataclass(frozen=True)
class SignalAsOfResult:
    as_of_date: str
    signal_date: str
    experiment: str
    model_version: str
    rows: list[SignalAsOfRow]
    warnings: list[str]


def generate_signal_as_of(
    config: AppConfig,
    as_of_date: str,
    config_path: Path | None = None,
) -> SignalAsOfResult:
    as_of = pd.Timestamp(as_of_date)
    if as_of < pd.Timestamp(config.data.start):
        raise ValueError("as_of_date must be on or after data.start")

    universe = resolve_universe(
        static_universe=config.data.universe,
        start=config.data.start,
        end=as_of.date().isoformat(),
        provider_kind=config.data.universe_provider.kind,
        provider_path=config.data.universe_provider.path,
    )
    market_data = load_market_data(
        MarketDataRequest(
            source=config.data.source,
            universe=universe.symbols,
            start=config.data.start,
            end=as_of.date().isoformat(),
            seed=config.data.seed,
            snapshot_path=config.data.snapshot.path,
        )
    )
    market_data = market_data.loc[
        market_data.index.get_level_values("date") <= as_of
    ]
    market_data = apply_universe_membership(market_data, universe.membership)
    factors = compute_factor_library(market_data)
    signal = FactorAgent().build_signal(factors, config.experiment.signal)
    eligible_dates = signal.index.get_level_values("date").unique()
    eligible_dates = eligible_dates[eligible_dates <= as_of]
    if len(eligible_dates) == 0:
        raise ValueError("not enough historical data to compute an as-of signal")

    signal_date = pd.Timestamp(max(eligible_dates))
    signal_slice = signal.loc[signal_date].dropna().sort_values(ascending=False)
    if signal_slice.empty:
        raise ValueError("as-of signal is empty")

    borrow_availability = load_borrow_availability(
        path=config.experiment.shorting.locate_history_path,
        symbols=universe.symbols,
        dates=market_data.index.get_level_values("date").unique(),
    )
    shortable_by_date = borrow_availability.shortable if borrow_availability is not None else None
    target_weights, warnings = _target_weights(
        signal_slice=signal_slice,
        signal_date=signal_date,
        quantile=config.experiment.backtest.quantile,
        shortable_symbols=config.experiment.shorting.shortable_symbols,
        shortable_by_date=shortable_by_date,
    )
    model_version = _model_version(config=config, config_path=config_path)
    positive = ", ".join(config.experiment.signal.positive_factors) or "none"
    negative = ", ".join(config.experiment.signal.negative_factors) or "none"
    rows = [
        SignalAsOfRow(
            symbol=str(symbol),
            signal_score=float(score),
            rank=index + 1,
            target_weight=float(target_weights.get(symbol, 0.0)),
            reason=f"positive={positive}; negative={negative}",
            risk_status="pass" if target_weights.get(symbol, 0.0) != 0.0 else "watch",
            data_timestamp=signal_date.date().isoformat(),
            model_version=model_version,
        )
        for index, (symbol, score) in enumerate(signal_slice.items())
    ]
    return SignalAsOfResult(
        as_of_date=as_of.date().isoformat(),
        signal_date=signal_date.date().isoformat(),
        experiment=config.experiment.name,
        model_version=model_version,
        rows=rows,
        warnings=warnings,
    )


def signal_result_to_dict(result: SignalAsOfResult) -> dict[str, object]:
    return {
        "as_of_date": result.as_of_date,
        "signal_date": result.signal_date,
        "experiment": result.experiment,
        "model_version": result.model_version,
        "warnings": result.warnings,
        "rows": [row.__dict__ for row in result.rows],
    }


def _target_weights(
    signal_slice: pd.Series,
    signal_date: pd.Timestamp,
    quantile: float,
    shortable_symbols: list[str] | None,
    shortable_by_date: pd.DataFrame | None,
) -> tuple[pd.Series, list[str]]:
    warnings: list[str] = []
    weights = pd.Series(0.0, index=signal_slice.index)
    if len(signal_slice) < 5:
        warnings.append("Fewer than five assets were available for portfolio construction.")
        return weights, warnings

    long_cutoff = signal_slice.quantile(1.0 - quantile)
    short_cutoff = signal_slice.quantile(quantile)
    longs = signal_slice[signal_slice >= long_cutoff].index
    shorts = signal_slice[signal_slice <= short_cutoff].index
    if shortable_symbols is not None:
        shorts = shorts.intersection(pd.Index(sorted(set(shortable_symbols))))
    if shortable_by_date is not None:
        if signal_date not in shortable_by_date.index:
            shorts = pd.Index([])
        else:
            date_shortable = shortable_by_date.reindex(columns=signal_slice.index).loc[signal_date].fillna(False)
            shorts = shorts.intersection(date_shortable[date_shortable].index)

    if len(longs) == 0:
        warnings.append("No long candidates passed the configured quantile.")
    else:
        weights.loc[longs] = 1.0 / len(longs)

    if len(shorts) == 0:
        warnings.append("No short candidates passed configured shortability constraints.")
    else:
        weights.loc[shorts] = -1.0 / len(shorts)

    return weights, warnings


def _model_version(config: AppConfig, config_path: Path | None) -> str:
    if config_path is not None and config_path.exists():
        return file_sha256(config_path)[:12]
    return _slug(config.experiment.name)
