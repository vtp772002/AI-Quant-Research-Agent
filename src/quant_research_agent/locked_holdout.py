from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import pandas as pd
import yaml

from quant_research_agent.backtest.engine import BacktestResult
from quant_research_agent.config import AppConfig
from quant_research_agent.data.snapshot import file_sha256


LOCKED_HOLDOUT_SCHEMA_VERSION = "locked_holdout_v1"


@dataclass(frozen=True)
class LockedHoldoutEvidence:
    enabled: bool
    schema_version: str | None = None
    dataset_id: str | None = None
    owner: str | None = None
    purpose: str | None = None
    manifest_path: str | None = None
    data_path: str | None = None
    content_sha256: str | None = None
    expected_sha256: str | None = None
    hash_matches: bool | None = None
    holdout_start: str | None = None
    expected_start: str | None = None
    holdout_end: str | None = None
    expected_end: str | None = None
    date_range_matches: bool | None = None
    row_count: int | None = None
    expected_row_count: int | None = None
    row_count_matches: bool | None = None
    minimum_row_count: int | None = None
    minimum_row_count_met: bool | None = None
    symbols: list[str] = field(default_factory=list)
    expected_symbols: list[str] = field(default_factory=list)
    symbol_set_matches: bool | None = None
    warnings: list[str] = field(default_factory=list)


def validate_locked_holdout(
    *,
    config: AppConfig,
    market_data: pd.DataFrame,
    backtest: BacktestResult,
) -> LockedHoldoutEvidence | None:
    locked = config.experiment.validation.research_validity.locked_holdout
    if not locked.enabled:
        return None
    if backtest.holdout_start is None:
        raise ValueError("locked holdout requires a configured backtest holdout_start")
    if locked.manifest_path is None:
        raise ValueError("locked holdout manifest_path is required when enabled")

    manifest_path = locked.manifest_path
    raw = yaml.safe_load(manifest_path.read_text(encoding="utf-8")) or {}
    if not isinstance(raw, dict):
        raise ValueError("locked holdout manifest must be a YAML object")
    schema_version = str(raw.get("schema_version", ""))
    if schema_version != LOCKED_HOLDOUT_SCHEMA_VERSION:
        raise ValueError(
            "locked holdout manifest schema_version must be "
            f"{LOCKED_HOLDOUT_SCHEMA_VERSION}"
        )

    data_path = config.data.snapshot.path
    expected_sha256 = _optional_str(raw.get("content_sha256"))
    actual_sha256: str | None = None
    hash_matches: bool | None = None
    if data_path is not None:
        actual_sha256 = file_sha256(data_path)
        hash_matches = bool(expected_sha256 and actual_sha256 == expected_sha256)
    if locked.require_manifest_hash:
        if data_path is None:
            raise ValueError("locked holdout manifest hash requires data.snapshot.path")
        if not hash_matches:
            raise ValueError(
                "locked holdout content hash mismatch: "
                f"expected {expected_sha256 or '<missing>'}, observed {actual_sha256}"
            )

    dates = market_data.index.get_level_values("date")
    holdout_start = pd.Timestamp(backtest.holdout_start)
    holdout_data = market_data.loc[dates >= holdout_start]
    if holdout_data.empty:
        raise ValueError("locked holdout slice has no market data rows")

    holdout_dates = pd.Index(sorted(holdout_data.index.get_level_values("date").unique()))
    actual_start = holdout_dates.min().date().isoformat()
    actual_end = holdout_dates.max().date().isoformat()
    expected_start = _required_str(raw, "start")
    expected_end = _required_str(raw, "end")
    date_range_matches = expected_start == actual_start and expected_end == actual_end
    if not date_range_matches:
        raise ValueError(
            "locked holdout date range mismatch: "
            f"expected {expected_start} to {expected_end}, observed {actual_start} to {actual_end}"
        )

    actual_symbols = sorted(str(symbol).upper() for symbol in holdout_data.index.get_level_values("symbol").unique())
    expected_symbols = sorted(str(symbol).upper() for symbol in raw.get("symbols", []))
    symbol_set_matches = bool(expected_symbols) and expected_symbols == actual_symbols
    if not symbol_set_matches:
        raise ValueError(
            "locked holdout symbol set mismatch: "
            f"expected {expected_symbols or '<missing>'}, observed {actual_symbols}"
        )

    expected_row_count = _optional_int(raw.get("row_count"), "row_count")
    row_count = len(holdout_data)
    row_count_matches = expected_row_count is None or expected_row_count == row_count
    if not row_count_matches:
        raise ValueError(
            "locked holdout row count mismatch: "
            f"expected {expected_row_count}, observed {row_count}"
        )

    minimum_row_count = _optional_int(raw.get("minimum_row_count"), "minimum_row_count")
    minimum_row_count_met = minimum_row_count is None or row_count >= minimum_row_count
    if not minimum_row_count_met:
        raise ValueError(
            "locked holdout row count below minimum: "
            f"minimum {minimum_row_count}, observed {row_count}"
        )

    return LockedHoldoutEvidence(
        enabled=True,
        schema_version=schema_version,
        dataset_id=_optional_str(raw.get("dataset_id")),
        owner=_optional_str(raw.get("owner")),
        purpose=_optional_str(raw.get("purpose")),
        manifest_path=str(manifest_path),
        data_path=str(data_path) if data_path is not None else None,
        content_sha256=actual_sha256,
        expected_sha256=expected_sha256,
        hash_matches=hash_matches,
        holdout_start=actual_start,
        expected_start=expected_start,
        holdout_end=actual_end,
        expected_end=expected_end,
        date_range_matches=True,
        row_count=row_count,
        expected_row_count=expected_row_count,
        row_count_matches=True,
        minimum_row_count=minimum_row_count,
        minimum_row_count_met=True,
        symbols=actual_symbols,
        expected_symbols=expected_symbols,
        symbol_set_matches=True,
        warnings=[
            "Locked holdout is locally verified; storage access control remains outside this run."
        ],
    )


def locked_holdout_to_dict(evidence: LockedHoldoutEvidence | None) -> dict[str, Any] | None:
    if evidence is None:
        return None
    return {
        "enabled": evidence.enabled,
        "schema_version": evidence.schema_version,
        "dataset_id": evidence.dataset_id,
        "owner": evidence.owner,
        "purpose": evidence.purpose,
        "manifest_path": evidence.manifest_path,
        "data_path": evidence.data_path,
        "content_sha256": evidence.content_sha256,
        "expected_sha256": evidence.expected_sha256,
        "hash_matches": evidence.hash_matches,
        "holdout_start": evidence.holdout_start,
        "expected_start": evidence.expected_start,
        "holdout_end": evidence.holdout_end,
        "expected_end": evidence.expected_end,
        "date_range_matches": evidence.date_range_matches,
        "row_count": evidence.row_count,
        "expected_row_count": evidence.expected_row_count,
        "row_count_matches": evidence.row_count_matches,
        "minimum_row_count": evidence.minimum_row_count,
        "minimum_row_count_met": evidence.minimum_row_count_met,
        "symbols": evidence.symbols,
        "expected_symbols": evidence.expected_symbols,
        "symbol_set_matches": evidence.symbol_set_matches,
        "warnings": evidence.warnings,
    }


def _required_str(raw: dict[str, Any], key: str) -> str:
    value = _optional_str(raw.get(key))
    if value is None:
        raise ValueError(f"locked holdout manifest {key} is required")
    return value


def _optional_str(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _optional_int(value: Any, key: str) -> int | None:
    if value is None:
        return None
    if isinstance(value, bool):
        raise ValueError(f"locked holdout manifest {key} must be an integer")
    parsed = int(value)
    if parsed <= 0:
        raise ValueError(f"locked holdout manifest {key} must be positive")
    return parsed
