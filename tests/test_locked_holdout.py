from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pandas as pd
import pytest
import yaml

from quant_research_agent.config import parse_config
from quant_research_agent.data.snapshot import file_sha256
from quant_research_agent.locked_holdout import (
    LOCKED_HOLDOUT_SCHEMA_VERSION,
    locked_holdout_to_dict,
    validate_locked_holdout,
)
from quant_research_agent.workflow import run_configured_workflow


def test_parse_config_supports_locked_holdout(tmp_path: Path):
    manifest_path = tmp_path / "locked_holdout.yaml"
    raw = _raw_config(tmp_path)
    raw["experiment"]["validation"]["research_validity"]["locked_holdout"] = {
        "enabled": True,
        "manifest_path": str(manifest_path),
        "require_manifest_hash": False,
    }

    locked = parse_config(raw).experiment.validation.research_validity.locked_holdout

    assert locked.enabled is True
    assert locked.manifest_path == manifest_path
    assert locked.require_manifest_hash is False


def test_parse_config_rejects_locked_holdout_without_research_validity(tmp_path: Path):
    raw = _raw_config(tmp_path)
    raw["experiment"]["validation"]["research_validity"]["enabled"] = False
    raw["experiment"]["validation"]["research_validity"]["locked_holdout"] = {
        "enabled": True,
        "manifest_path": str(tmp_path / "locked.yaml"),
    }

    with pytest.raises(ValueError, match="locked_holdout.enabled requires research_validity.enabled"):
        parse_config(raw)


def test_parse_config_rejects_locked_holdout_without_manifest(tmp_path: Path):
    raw = _raw_config(tmp_path)
    raw["experiment"]["validation"]["research_validity"]["locked_holdout"] = {"enabled": True}

    with pytest.raises(ValueError, match="locked_holdout.manifest_path is required"):
        parse_config(raw)


def test_validate_locked_holdout_accepts_matching_manifest(tmp_path: Path):
    data_path, market_data = _market_data(tmp_path)
    manifest_path = _locked_manifest(
        tmp_path,
        data_path=data_path,
        start="2020-05-01",
        end="2020-06-30",
        symbols=["AAA", "BBB"],
        row_count=86,
    )
    config = parse_config(
        _raw_config(tmp_path, snapshot_path=data_path, locked_manifest_path=manifest_path),
        base_dir=tmp_path,
    )

    evidence = validate_locked_holdout(
        config=config,
        market_data=market_data,
        backtest=SimpleNamespace(holdout_start=pd.Timestamp("2020-05-01")),
    )

    payload = locked_holdout_to_dict(evidence)
    assert payload is not None
    assert payload["dataset_id"] == "locked-holdout-test"
    assert payload["hash_matches"] is True
    assert payload["date_range_matches"] is True
    assert payload["row_count"] == 86
    assert payload["symbols"] == ["AAA", "BBB"]


@pytest.mark.parametrize(
    ("field", "value", "message"),
    [
        ("content_sha256", "bad-hash", "content hash mismatch"),
        ("start", "2020-05-04", "date range mismatch"),
        ("symbols", ["AAA"], "symbol set mismatch"),
        ("row_count", 85, "row count mismatch"),
        ("minimum_row_count", 1000, "row count below minimum"),
    ],
)
def test_validate_locked_holdout_fails_closed_on_manifest_mismatch(
    tmp_path: Path,
    field: str,
    value: object,
    message: str,
):
    data_path, market_data = _market_data(tmp_path)
    manifest_path = _locked_manifest(
        tmp_path,
        data_path=data_path,
        start="2020-05-01",
        end="2020-06-30",
        symbols=["AAA", "BBB"],
        row_count=86,
    )
    raw_manifest = yaml.safe_load(manifest_path.read_text(encoding="utf-8"))
    raw_manifest[field] = value
    manifest_path.write_text(yaml.safe_dump(raw_manifest, sort_keys=True), encoding="utf-8")
    config = parse_config(
        _raw_config(tmp_path, snapshot_path=data_path, locked_manifest_path=manifest_path),
        base_dir=tmp_path,
    )

    with pytest.raises(ValueError, match=message):
        validate_locked_holdout(
            config=config,
            market_data=market_data,
            backtest=SimpleNamespace(holdout_start=pd.Timestamp("2020-05-01")),
        )


def test_workflow_writes_locked_holdout_evidence_to_payload_and_manifest(tmp_path: Path):
    data_path = _workflow_market_csv(tmp_path)
    unlocked_config = _workflow_config(tmp_path, data_path=data_path, locked_manifest_path=None)
    unlocked_config_path = tmp_path / "unlocked.yaml"
    unlocked_config_path.write_text(yaml.safe_dump(unlocked_config, sort_keys=False), encoding="utf-8")
    unlocked = run_configured_workflow(unlocked_config_path)
    holdout_start = unlocked.result.backtest.holdout_start
    assert holdout_start is not None
    holdout = unlocked.result.market_data.loc[
        unlocked.result.market_data.index.get_level_values("date") >= holdout_start
    ]
    manifest_path = _locked_manifest(
        tmp_path,
        data_path=data_path,
        start=holdout.index.get_level_values("date").min().date().isoformat(),
        end=holdout.index.get_level_values("date").max().date().isoformat(),
        symbols=sorted(holdout.index.get_level_values("symbol").unique()),
        row_count=len(holdout),
    )
    locked_config = _workflow_config(tmp_path, data_path=data_path, locked_manifest_path=manifest_path)
    locked_config_path = tmp_path / "locked.yaml"
    locked_config_path.write_text(yaml.safe_dump(locked_config, sort_keys=False), encoding="utf-8")

    workflow = run_configured_workflow(locked_config_path)

    payload = workflow.payload["locked_holdout"]
    assert payload["enabled"] is True
    assert payload["dataset_id"] == "locked-holdout-test"
    assert payload["hash_matches"] is True
    assert workflow.manifest["metrics"]["research_validity"]["locked_holdout"]["row_count"] == payload["row_count"]
    assert "Locked holdout: `verified`" in workflow.report_path.read_text(encoding="utf-8")


def _raw_config(
    tmp_path: Path,
    *,
    snapshot_path: Path | None = None,
    locked_manifest_path: Path | None = None,
) -> dict[str, object]:
    locked = {
        "enabled": locked_manifest_path is not None,
        "manifest_path": str(locked_manifest_path) if locked_manifest_path is not None else None,
        "require_manifest_hash": True,
    }
    return {
        "data": {
            "source": "csv_snapshot" if snapshot_path is not None else "synthetic",
            "snapshot": {"path": str(snapshot_path)} if snapshot_path is not None else {},
            "universe": ["AAA", "BBB"],
            "start": "2020-01-01",
            "end": "2020-06-30",
        },
        "experiment": {
            "name": "locked_holdout_config_test",
            "train_fraction": 0.6,
            "signal": {"positive_factors": ["momentum_20d"], "negative_factors": []},
            "backtest": {"holding_period": 5, "rebalance_days": 5, "quantile": 0.2},
            "validation": {
                "walk_forward": {"window_count": 0, "min_train_fraction": 0.4},
                "research_validity": {
                    "enabled": True,
                    "holdout_fraction": 0.2,
                    "require_baseline_outperformance": False,
                    "require_walk_forward_stability": False,
                    "require_data_readiness": False,
                    "locked_holdout": locked,
                },
            },
            "baselines": [],
        },
        "report": {
            "output_path": str(tmp_path / "report.md"),
            "experiments_path": str(tmp_path / "experiments.csv"),
            "registry_path": str(tmp_path / "experiments.sqlite"),
        },
    }


def _workflow_config(tmp_path: Path, *, data_path: Path, locked_manifest_path: Path | None) -> dict[str, object]:
    symbols = ["AAA", "BBB", "CCC", "DDD", "EEE", "FFF"]
    raw = _raw_config(tmp_path, snapshot_path=data_path, locked_manifest_path=locked_manifest_path)
    raw["data"]["universe"] = symbols
    raw["experiment"]["train_fraction"] = 0.65
    raw["experiment"]["backtest"]["quantile"] = 0.25
    raw["experiment"]["shorting"] = {"shortable_symbols": symbols}
    raw["experiment"]["capacity"] = {"notionals": []}
    raw["experiment"]["robustness"] = {"bootstrap_iterations": 0}
    raw["experiment"]["stress_tests"] = {
        "neutralization": {"enabled": False, "group_by": "sector"},
        "liquidity": {"enabled": False, "min_dollar_volume_rank": 0.0},
    }
    return raw


def _market_data(tmp_path: Path) -> tuple[Path, pd.DataFrame]:
    data_path = tmp_path / "market.csv"
    rows = []
    for date in pd.bdate_range("2020-01-01", "2020-06-30"):
        for symbol, offset in [("AAA", 0), ("BBB", 1)]:
            close = 100.0 + offset
            rows.append(
                {
                    "date": date.date().isoformat(),
                    "symbol": symbol,
                    "open": close,
                    "high": close + 1,
                    "low": close - 1,
                    "close": close,
                    "adj_close": close,
                    "volume": 1_000_000,
                }
            )
    frame = pd.DataFrame(rows)
    frame.to_csv(data_path, index=False)
    market_data = frame.assign(date=lambda item: pd.to_datetime(item["date"]))
    market_data = market_data.set_index(["date", "symbol"]).sort_index()
    return data_path, market_data


def _workflow_market_csv(tmp_path: Path) -> Path:
    data_path = tmp_path / "workflow_market.csv"
    rows = []
    for date_index, date in enumerate(pd.bdate_range("2020-01-01", "2020-12-31")):
        for symbol_index, symbol in enumerate(["AAA", "BBB", "CCC", "DDD", "EEE", "FFF"]):
            close = 100.0 + symbol_index * 3.0 + date_index * (0.05 + symbol_index * 0.005)
            rows.append(
                {
                    "date": date.date().isoformat(),
                    "symbol": symbol,
                    "open": close - 0.1,
                    "high": close + 0.2,
                    "low": close - 0.2,
                    "close": close,
                    "adj_close": close,
                    "volume": 1_000_000 + symbol_index * 1000,
                }
            )
    pd.DataFrame(rows).to_csv(data_path, index=False)
    return data_path


def _locked_manifest(
    tmp_path: Path,
    *,
    data_path: Path,
    start: str,
    end: str,
    symbols: list[str],
    row_count: int,
) -> Path:
    manifest_path = tmp_path / "locked_holdout.yaml"
    manifest_path.write_text(
        yaml.safe_dump(
            {
                "schema_version": LOCKED_HOLDOUT_SCHEMA_VERSION,
                "dataset_id": "locked-holdout-test",
                "owner": "research-ops",
                "purpose": "final_promotion_holdout",
                "content_sha256": file_sha256(data_path),
                "start": start,
                "end": end,
                "symbols": symbols,
                "row_count": row_count,
                "minimum_row_count": row_count,
            },
            sort_keys=True,
        ),
        encoding="utf-8",
    )
    return manifest_path
