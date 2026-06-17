from __future__ import annotations

from dataclasses import dataclass, field
from hashlib import sha256
from pathlib import Path

import pandas as pd
import yaml


@dataclass(frozen=True)
class SnapshotProvenance:
    dataset_id: str
    vendor: str
    as_of: str
    created_at: str
    manifest_path: str
    data_path: str
    content_sha256: str
    expected_sha256: str
    hash_matches: bool
    row_count: int
    expected_row_count: int | None
    row_count_matches: bool
    symbols: list[str]
    expected_symbols: list[str]
    symbol_set_matches: bool
    start: str
    end: str
    expected_start: str
    expected_end: str
    date_range_matches: bool
    point_in_time_universe: bool
    survivorship_bias_free: bool
    corporate_actions_adjusted: bool
    warnings: list[str] = field(default_factory=list)


def load_snapshot_provenance(
    manifest_path: Path | None,
    data_path: Path | None,
    data: pd.DataFrame,
    require_hash: bool,
) -> SnapshotProvenance | None:
    if manifest_path is None:
        return None
    if data_path is None:
        raise ValueError("data.snapshot.path is required when a snapshot manifest is configured")

    raw = yaml.safe_load(manifest_path.read_text()) or {}
    actual_hash = file_sha256(data_path)
    expected_hash = str(raw.get("content_sha256", ""))
    hash_matches = bool(expected_hash and expected_hash == actual_hash)
    if require_hash and not hash_matches:
        raise ValueError(
            "snapshot content hash mismatch: "
            f"expected {expected_hash or '<missing>'}, observed {actual_hash}"
        )

    symbols = sorted(str(symbol).upper() for symbol in data.index.get_level_values("symbol").unique())
    dates = pd.Index(sorted(data.index.get_level_values("date").unique()))
    start = dates.min().date().isoformat()
    end = dates.max().date().isoformat()
    expected_symbols = sorted(str(symbol).upper() for symbol in raw.get("symbols", []))
    expected_start = str(raw.get("start", ""))
    expected_end = str(raw.get("end", ""))
    expected_row_count = raw.get("row_count")
    parsed_expected_row_count = int(expected_row_count) if expected_row_count is not None else None

    row_count_matches = parsed_expected_row_count is None or parsed_expected_row_count == len(data)
    symbol_set_matches = not expected_symbols or expected_symbols == symbols
    date_range_matches = (not expected_start or expected_start == start) and (not expected_end or expected_end == end)

    warnings = _validation_warnings(
        hash_matches=hash_matches,
        row_count_matches=row_count_matches,
        symbol_set_matches=symbol_set_matches,
        date_range_matches=date_range_matches,
    )

    return SnapshotProvenance(
        dataset_id=str(raw.get("dataset_id", "")),
        vendor=str(raw.get("vendor", "")),
        as_of=str(raw.get("as_of", "")),
        created_at=str(raw.get("created_at", "")),
        manifest_path=str(manifest_path),
        data_path=str(data_path),
        content_sha256=actual_hash,
        expected_sha256=expected_hash,
        hash_matches=hash_matches,
        row_count=len(data),
        expected_row_count=parsed_expected_row_count,
        row_count_matches=row_count_matches,
        symbols=symbols,
        expected_symbols=expected_symbols,
        symbol_set_matches=symbol_set_matches,
        start=start,
        end=end,
        expected_start=expected_start,
        expected_end=expected_end,
        date_range_matches=date_range_matches,
        point_in_time_universe=bool(raw.get("point_in_time_universe", False)),
        survivorship_bias_free=bool(raw.get("survivorship_bias_free", False)),
        corporate_actions_adjusted=bool(raw.get("corporate_actions_adjusted", False)),
        warnings=warnings,
    )


def file_sha256(path: Path) -> str:
    digest = sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _validation_warnings(
    hash_matches: bool,
    row_count_matches: bool,
    symbol_set_matches: bool,
    date_range_matches: bool,
) -> list[str]:
    warnings: list[str] = []
    if not hash_matches:
        warnings.append("Snapshot manifest hash does not match the data file.")
    if not row_count_matches:
        warnings.append("Snapshot manifest row count does not match loaded data.")
    if not symbol_set_matches:
        warnings.append("Snapshot manifest symbols do not match loaded data.")
    if not date_range_matches:
        warnings.append("Snapshot manifest date range does not match loaded data.")
    return warnings
