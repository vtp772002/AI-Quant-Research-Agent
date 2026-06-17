from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from quant_research_agent.data.snapshot import SnapshotProvenance


@dataclass(frozen=True)
class SymbolDataQuality:
    symbol: str
    observations: int
    expected_observations: int
    coverage: float
    missing_rows: int
    zero_volume_rows: int
    non_positive_price_rows: int
    stale_price_rows: int
    extreme_return_rows: int


@dataclass(frozen=True)
class DataIntegrityReport:
    source: str
    requested_symbols: list[str]
    observed_symbols: list[str]
    start: str
    end: str
    row_count: int
    date_count: int
    duplicate_index_rows: int
    missing_symbols: list[str]
    point_in_time_universe: bool
    survivorship_bias_free: bool
    corporate_actions_adjusted: bool
    provenance: SnapshotProvenance | None
    quality_by_symbol: list[SymbolDataQuality]
    warnings: list[str]


def assess_market_data_integrity(
    data: pd.DataFrame,
    source: str,
    requested_symbols: list[str],
    start: str,
    end: str,
    point_in_time_universe: bool,
    survivorship_bias_free: bool,
    corporate_actions_adjusted: bool,
    provenance: SnapshotProvenance | None = None,
) -> DataIntegrityReport:
    requested = [symbol.upper() for symbol in requested_symbols]
    observed = sorted(data.index.get_level_values("symbol").unique())
    dates = pd.Index(sorted(data.index.get_level_values("date").unique()))
    duplicate_index_rows = int(data.index.duplicated().sum())
    missing_symbols = [symbol for symbol in requested if symbol not in observed]
    quality = [
        _symbol_quality(data=data, symbol=symbol, expected_dates=dates)
        for symbol in requested
        if symbol in observed
    ]

    effective_point_in_time = point_in_time_universe or bool(provenance and provenance.point_in_time_universe)
    effective_survivorship_free = survivorship_bias_free or bool(provenance and provenance.survivorship_bias_free)
    effective_corporate_actions = corporate_actions_adjusted or bool(provenance and provenance.corporate_actions_adjusted)

    warnings = _source_warnings(
        source=source,
        point_in_time_universe=effective_point_in_time,
        survivorship_bias_free=effective_survivorship_free,
        corporate_actions_adjusted=effective_corporate_actions,
        provenance=provenance,
    )
    if provenance is not None:
        warnings.extend(provenance.warnings)
    if missing_symbols:
        warnings.append(f"Missing requested symbols: {', '.join(missing_symbols)}.")
    if duplicate_index_rows:
        warnings.append(f"Market data contains {duplicate_index_rows} duplicate date-symbol rows.")
    for item in quality:
        if item.coverage < 0.95:
            warnings.append(f"{item.symbol} coverage is {item.coverage:.2%}; inspect missing rows before trusting results.")
        if item.non_positive_price_rows:
            warnings.append(f"{item.symbol} has {item.non_positive_price_rows} rows with non-positive OHLC prices.")
        if item.zero_volume_rows:
            warnings.append(f"{item.symbol} has {item.zero_volume_rows} rows with non-positive volume.")
        if item.extreme_return_rows:
            warnings.append(f"{item.symbol} has {item.extreme_return_rows} rows with absolute adjusted return above 50%.")
        if item.stale_price_rows:
            warnings.append(f"{item.symbol} has {item.stale_price_rows} stale adjusted-close rows.")

    return DataIntegrityReport(
        source=source,
        requested_symbols=requested,
        observed_symbols=observed,
        start=start,
        end=end,
        row_count=int(len(data)),
        date_count=int(len(dates)),
        duplicate_index_rows=duplicate_index_rows,
        missing_symbols=missing_symbols,
        point_in_time_universe=effective_point_in_time,
        survivorship_bias_free=effective_survivorship_free,
        corporate_actions_adjusted=effective_corporate_actions,
        provenance=provenance,
        quality_by_symbol=quality,
        warnings=warnings,
    )


def _symbol_quality(data: pd.DataFrame, symbol: str, expected_dates: pd.Index) -> SymbolDataQuality:
    symbol_data = data.xs(symbol, level="symbol").sort_index()
    expected_observations = len(expected_dates)
    observations = len(symbol_data)
    missing_rows = int(expected_observations - observations)
    price_columns = ["open", "high", "low", "close", "adj_close"]
    non_positive_price_rows = int((symbol_data[price_columns] <= 0).any(axis=1).sum())
    zero_volume_rows = int((symbol_data["volume"] <= 0).sum())
    adjusted_returns = symbol_data["adj_close"].pct_change(fill_method=None)
    extreme_return_rows = int((adjusted_returns.abs() > 0.50).sum())
    stale_price_rows = int((symbol_data["adj_close"].diff().abs() == 0).rolling(5).sum().ge(5).sum())
    coverage = float(observations / expected_observations) if expected_observations else 0.0

    return SymbolDataQuality(
        symbol=symbol,
        observations=int(observations),
        expected_observations=int(expected_observations),
        coverage=coverage,
        missing_rows=missing_rows,
        zero_volume_rows=zero_volume_rows,
        non_positive_price_rows=non_positive_price_rows,
        stale_price_rows=stale_price_rows,
        extreme_return_rows=extreme_return_rows,
    )


def _source_warnings(
    source: str,
    point_in_time_universe: bool,
    survivorship_bias_free: bool,
    corporate_actions_adjusted: bool,
    provenance: SnapshotProvenance | None,
) -> list[str]:
    warnings: list[str] = []
    normalized_source = source.lower()
    if normalized_source == "synthetic":
        warnings.append("Synthetic data validates mechanics but is not investment evidence.")
    if normalized_source == "yahoo":
        warnings.append("Yahoo Finance is a demo source and does not provide an institutional point-in-time research dataset.")
    if normalized_source == "csv_snapshot" and provenance is None:
        warnings.append("CSV snapshot source is configured without a manifest; provenance and golden validation are incomplete.")
    if not point_in_time_universe:
        warnings.append("Universe membership is not marked point-in-time; survivorship or lookahead bias may remain.")
    if not survivorship_bias_free:
        warnings.append("Universe is not marked survivorship-bias-free.")
    if not corporate_actions_adjusted:
        warnings.append("Corporate-action handling is not marked institutional-grade.")
    return warnings
