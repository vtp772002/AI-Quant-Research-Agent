from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pandas as pd


@dataclass(frozen=True)
class UniverseResolution:
    source: str
    symbols: list[str]
    membership: pd.DataFrame
    point_in_time: bool
    survivorship_bias_free: bool
    warnings: list[str]


def resolve_universe(
    static_universe: list[str],
    start: str,
    end: str,
    provider_kind: str = "static",
    provider_path: Path | None = None,
) -> UniverseResolution:
    kind = provider_kind.lower()
    if kind == "static":
        symbols = [symbol.upper() for symbol in static_universe]
        if not symbols:
            raise ValueError("data.universe must not be empty for static universe provider")
        membership = pd.DataFrame(
            {
                "symbol": symbols,
                "start": pd.Timestamp(start),
                "end": pd.Timestamp(end),
            }
        )
        return UniverseResolution(
            source="static",
            symbols=symbols,
            membership=membership,
            point_in_time=False,
            survivorship_bias_free=False,
            warnings=["Static universe is not point-in-time and may contain survivorship bias."],
        )

    if kind == "csv":
        if provider_path is None:
            raise ValueError("data.universe_provider.path is required when kind=csv")
        membership = _load_csv_membership(provider_path=provider_path, start=start, end=end)
        symbols = sorted(membership["symbol"].unique())
        if not symbols:
            raise ValueError("universe membership provider returned no symbols for requested date range")
        return UniverseResolution(
            source=f"csv:{provider_path}",
            symbols=symbols,
            membership=membership,
            point_in_time=True,
            survivorship_bias_free=True,
            warnings=[],
        )

    raise ValueError(f"unsupported universe provider kind: {provider_kind}")


def apply_universe_membership(data: pd.DataFrame, membership: pd.DataFrame) -> pd.DataFrame:
    if membership.empty:
        raise ValueError("universe membership must not be empty")
    frames = []
    for row in membership.itertuples(index=False):
        symbol_data = data.xs(row.symbol, level="symbol", drop_level=False)
        dates = symbol_data.index.get_level_values("date")
        frames.append(symbol_data[(dates >= row.start) & (dates <= row.end)])
    if not frames:
        raise ValueError("no market data rows matched universe membership")
    filtered = pd.concat(frames).sort_index()
    if filtered.empty:
        raise ValueError("market data is empty after applying universe membership")
    return filtered


def _load_csv_membership(provider_path: Path, start: str, end: str) -> pd.DataFrame:
    frame = pd.read_csv(provider_path)
    required = {"symbol", "start"}
    missing = required - set(frame.columns)
    if missing:
        raise ValueError(f"universe membership CSV missing columns: {sorted(missing)}")

    requested_start = pd.Timestamp(start)
    requested_end = pd.Timestamp(end)
    membership = pd.DataFrame(
        {
            "symbol": frame["symbol"].astype(str).str.upper(),
            "start": pd.to_datetime(frame["start"]),
            "end": pd.to_datetime(frame["end"]) if "end" in frame.columns else requested_end,
        }
    )
    membership["end"] = membership["end"].fillna(requested_end)
    membership = membership[(membership["start"] <= requested_end) & (membership["end"] >= requested_start)].copy()
    membership["start"] = membership["start"].clip(lower=requested_start)
    membership["end"] = membership["end"].clip(upper=requested_end)
    return membership.sort_values(["symbol", "start", "end"]).reset_index(drop=True)
