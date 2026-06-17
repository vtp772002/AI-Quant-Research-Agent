from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import pandas as pd


@dataclass(frozen=True)
class BorrowAvailability:
    path: str
    records: pd.DataFrame
    shortable: pd.DataFrame
    borrow_fee_bps: pd.DataFrame
    summary: "BorrowAvailabilitySummary"


@dataclass(frozen=True)
class BorrowAvailabilitySummary:
    path: str
    row_count: int
    symbols: list[str]
    start: str
    end: str
    coverage: float
    unavailable_rows: int
    hard_to_borrow_rows: int
    average_borrow_fee_bps: float
    max_borrow_fee_bps: float
    warnings: list[str] = field(default_factory=list)


def load_borrow_availability(
    path: Path | None,
    symbols: list[str],
    dates: pd.Index,
    hard_to_borrow_fee_bps: float = 500.0,
) -> BorrowAvailability | None:
    if path is None:
        return None

    frame = pd.read_csv(path)
    required = {"date", "symbol", "shortable", "borrow_fee_bps"}
    missing = required - set(frame.columns)
    if missing:
        raise ValueError(f"borrow availability missing columns: {sorted(missing)}")

    requested_symbols = sorted({symbol.upper() for symbol in symbols})
    requested_dates = pd.Index(sorted(pd.to_datetime(dates).unique()), name="date")
    if requested_dates.empty:
        raise ValueError("borrow availability requires at least one market data date")

    records = frame.copy()
    records["date"] = pd.to_datetime(records["date"])
    records["symbol"] = records["symbol"].astype(str).str.upper()
    records["shortable"] = records["shortable"].map(_parse_bool)
    records["borrow_fee_bps"] = records["borrow_fee_bps"].astype(float)
    if "available_quantity" in records.columns:
        records["available_quantity"] = records["available_quantity"].astype(float)
        records.loc[records["available_quantity"] <= 0, "shortable"] = False

    start = requested_dates.min()
    end = requested_dates.max()
    records = records[
        records["symbol"].isin(requested_symbols)
        & records["date"].between(start, end)
    ].sort_values(["date", "symbol"])
    if records.empty:
        raise ValueError("borrow availability has no rows for requested symbols and date range")
    if records.duplicated(["date", "symbol"]).any():
        raise ValueError("borrow availability contains duplicate date-symbol rows")

    full_index = pd.MultiIndex.from_product([requested_dates, requested_symbols], names=["date", "symbol"])
    indexed = records.set_index(["date", "symbol"]).reindex(full_index)
    shortable = indexed["shortable"].unstack("symbol").fillna(False).astype(bool)
    borrow_fee_bps = indexed["borrow_fee_bps"].unstack("symbol")
    observed = indexed["borrow_fee_bps"].notna()
    coverage = float(observed.mean()) if len(observed) else 0.0
    unavailable_rows = int((~shortable).sum().sum())
    hard_to_borrow_rows = int((borrow_fee_bps >= hard_to_borrow_fee_bps).sum().sum())
    warnings = []
    if coverage < 0.95:
        warnings.append(f"Borrow availability coverage is {coverage:.2%}; missing rows are treated as not shortable.")
    if unavailable_rows:
        warnings.append(f"Borrow availability marks {unavailable_rows} date-symbol rows as not shortable.")
    if hard_to_borrow_rows:
        warnings.append(f"Borrow availability flags {hard_to_borrow_rows} hard-to-borrow rows at or above {hard_to_borrow_fee_bps:.0f} bps.")

    summary = BorrowAvailabilitySummary(
        path=str(path),
        row_count=int(len(records)),
        symbols=sorted(records["symbol"].unique()),
        start=start.date().isoformat(),
        end=end.date().isoformat(),
        coverage=coverage,
        unavailable_rows=unavailable_rows,
        hard_to_borrow_rows=hard_to_borrow_rows,
        average_borrow_fee_bps=float(borrow_fee_bps.stack().mean()) if not borrow_fee_bps.stack().empty else 0.0,
        max_borrow_fee_bps=float(borrow_fee_bps.stack().max()) if not borrow_fee_bps.stack().empty else 0.0,
        warnings=warnings,
    )
    return BorrowAvailability(
        path=str(path),
        records=records,
        shortable=shortable,
        borrow_fee_bps=borrow_fee_bps,
        summary=summary,
    )


def _parse_bool(value: object) -> bool:
    if isinstance(value, bool):
        return value
    text = str(value).strip().lower()
    if text in {"1", "true", "yes", "y"}:
        return True
    if text in {"0", "false", "no", "n"}:
        return False
    raise ValueError(f"invalid borrow shortable value: {value!r}")
