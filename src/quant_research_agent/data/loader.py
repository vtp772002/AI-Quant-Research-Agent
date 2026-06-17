from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd


REQUIRED_COLUMNS = ["open", "high", "low", "close", "adj_close", "volume"]


@dataclass(frozen=True)
class MarketDataRequest:
    source: str
    universe: list[str]
    start: str
    end: str
    seed: int = 42
    snapshot_path: Path | None = None


def load_market_data(request: MarketDataRequest) -> pd.DataFrame:
    source = request.source.lower()
    if source == "synthetic":
        return generate_synthetic_ohlcv(
            symbols=request.universe,
            start=request.start,
            end=request.end,
            seed=request.seed,
        )
    if source == "yahoo":
        return load_yahoo_ohlcv(request.universe, request.start, request.end)
    if source == "csv_snapshot":
        if request.snapshot_path is None:
            raise ValueError("snapshot_path is required for data.source=csv_snapshot")
        return load_csv_snapshot_ohlcv(request.snapshot_path, request.universe, request.start, request.end)
    raise ValueError(f"unsupported data source: {request.source}")


def generate_synthetic_ohlcv(
    symbols: list[str],
    start: str,
    end: str,
    seed: int = 42,
) -> pd.DataFrame:
    if not symbols:
        raise ValueError("symbols must not be empty")

    dates = pd.bdate_range(start=start, end=end, name="date")
    if len(dates) < 80:
        raise ValueError("synthetic data needs at least 80 business days")

    rng = np.random.default_rng(seed)
    market_shock = rng.normal(0.00025, 0.009, len(dates))
    rows: list[pd.DataFrame] = []

    for index, symbol in enumerate(symbols):
        beta = rng.uniform(0.7, 1.3)
        idiosyncratic = rng.normal(0, rng.uniform(0.010, 0.024), len(dates))
        drift = rng.normal(0.00015, 0.00018)
        returns = drift + beta * market_shock + idiosyncratic

        close = 100.0 * np.exp(np.cumsum(returns))
        open_ = close * (1.0 + rng.normal(0, 0.003, len(dates)))
        spread = np.abs(rng.normal(0.004, 0.002, len(dates)))
        high = np.maximum(open_, close) * (1.0 + spread)
        low = np.minimum(open_, close) * (1.0 - spread)
        base_volume = rng.uniform(2_000_000, 12_000_000) * (1.0 + index / max(len(symbols), 1))
        volume = base_volume * np.exp(rng.normal(0, 0.25, len(dates)))

        frame = pd.DataFrame(
            {
                "date": dates,
                "symbol": symbol,
                "open": open_,
                "high": high,
                "low": low,
                "close": close,
                "adj_close": close,
                "volume": volume.astype(int),
            }
        )
        rows.append(frame)

    data = pd.concat(rows, ignore_index=True)
    data = data.set_index(["date", "symbol"]).sort_index()
    return _validate_market_data(data)


def load_yahoo_ohlcv(symbols: list[str], start: str, end: str) -> pd.DataFrame:
    try:
        import yfinance as yf
    except ImportError as exc:
        raise RuntimeError("yfinance is required for data.source=yahoo") from exc

    raw = yf.download(
        tickers=" ".join(symbols),
        start=start,
        end=end,
        auto_adjust=False,
        progress=False,
        group_by="ticker",
        threads=False,
    )
    if raw.empty:
        raise RuntimeError("Yahoo Finance returned no rows")

    frames: list[pd.DataFrame] = []
    missing_symbols: list[str] = []
    for symbol in symbols:
        symbol_raw = raw[symbol] if isinstance(raw.columns, pd.MultiIndex) else raw
        frame = symbol_raw.rename(
            columns={
                "Open": "open",
                "High": "high",
                "Low": "low",
                "Close": "close",
                "Adj Close": "adj_close",
                "Volume": "volume",
            }
        )
        frame = frame[[col for col in REQUIRED_COLUMNS if col in frame.columns]].copy()
        if frame.dropna(how="all").empty:
            missing_symbols.append(symbol)
            continue
        frame["symbol"] = symbol
        frame.index.name = "date"
        frames.append(frame.reset_index())

    if missing_symbols:
        raise RuntimeError(f"Yahoo Finance returned no usable rows for: {missing_symbols}")
    if not frames:
        raise RuntimeError("Yahoo Finance returned no usable symbol data")

    data = pd.concat(frames, ignore_index=True)
    data = data.set_index(["date", "symbol"]).sort_index()
    return _validate_market_data(data)


def load_csv_snapshot_ohlcv(path: Path, symbols: list[str], start: str, end: str) -> pd.DataFrame:
    frame = pd.read_csv(path)
    required = {"date", "symbol", *REQUIRED_COLUMNS}
    missing = required - set(frame.columns)
    if missing:
        raise ValueError(f"snapshot data missing columns: {sorted(missing)}")

    frame = frame.copy()
    frame["date"] = pd.to_datetime(frame["date"])
    frame["symbol"] = frame["symbol"].astype(str).str.upper()
    start_date = pd.Timestamp(start)
    end_date = pd.Timestamp(end)
    requested_symbols = {symbol.upper() for symbol in symbols}
    frame = frame[
        frame["symbol"].isin(requested_symbols)
        & frame["date"].between(start_date, end_date)
    ]
    if frame.empty:
        raise ValueError("snapshot data has no rows for the requested symbols and date range")

    data = frame.set_index(["date", "symbol"]).sort_index()
    return _validate_market_data(data)


def _validate_market_data(data: pd.DataFrame) -> pd.DataFrame:
    missing = set(REQUIRED_COLUMNS) - set(data.columns)
    if missing:
        raise ValueError(f"market data missing columns: {sorted(missing)}")
    if not isinstance(data.index, pd.MultiIndex) or data.index.names != ["date", "symbol"]:
        raise ValueError("market data index must be MultiIndex(date, symbol)")
    cleaned = data[REQUIRED_COLUMNS].replace([np.inf, -np.inf], np.nan).dropna()
    if cleaned.empty:
        raise ValueError("market data has no valid rows after cleaning")
    return cleaned.sort_index()
