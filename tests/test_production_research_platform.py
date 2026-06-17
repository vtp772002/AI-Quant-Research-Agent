from __future__ import annotations

from pathlib import Path

from fastapi import HTTPException

from quant_research_agent.api import create_app
from quant_research_agent.config import parse_config
from quant_research_agent.experiment_registry import get_run, list_runs, record_run
from quant_research_agent.signals import generate_signal_as_of, signal_result_to_dict


def test_experiment_registry_records_and_queries_run(tmp_path: Path):
    registry_path = tmp_path / "experiments.sqlite"
    manifest = _manifest(run_id="run-001", report_path=tmp_path / "report.md")

    record = record_run(registry_path, manifest)

    assert record.run_id == "run-001"
    assert record.test_sharpe == 1.25
    assert get_run(registry_path, "run-001") == record
    assert [item.run_id for item in list_runs(registry_path)] == ["run-001"]


def test_generate_signal_as_of_uses_only_available_dates(tmp_path: Path):
    config = _config(tmp_path)

    result = generate_signal_as_of(config, as_of_date="2020-06-30")
    payload = signal_result_to_dict(result)

    assert payload["as_of_date"] == "2020-06-30"
    assert payload["signal_date"] <= "2020-06-30"
    assert payload["rows"]
    weights = [row["target_weight"] for row in payload["rows"]]
    assert any(weight > 0 for weight in weights)
    assert any(weight < 0 for weight in weights)
    assert all(row["data_timestamp"] <= "2020-06-30" for row in payload["rows"])
    assert all(row["model_version"] for row in payload["rows"])


def test_api_exposes_health_signal_and_missing_run_contract(tmp_path: Path):
    config_path = tmp_path / "service.yaml"
    config_path.write_text(_config_yaml(tmp_path), encoding="utf-8")
    registry_path = tmp_path / "registry.sqlite"
    app = create_app()

    health = _endpoint(app, "/health")()
    signal = _endpoint(app, "/signals/as-of")(
        config_path=str(config_path),
        date="2020-06-30",
    )

    assert health == {"status": "ok"}
    assert signal["signal_date"] <= "2020-06-30"
    assert signal["rows"]
    try:
        _endpoint(app, "/experiments/{run_id}")(
            run_id="missing-run",
            registry_path=str(registry_path),
        )
    except HTTPException as exc:
        assert exc.status_code == 404
        assert "run not found" in exc.detail
    else:
        raise AssertionError("missing run should raise HTTPException")


def _endpoint(app, path: str):
    for route in app.router.routes:
        if getattr(route, "path", None) == path:
            return route.endpoint
    raise AssertionError(f"route not found: {path}")


def _config(tmp_path: Path):
    return parse_config(_config_dict(tmp_path), base_dir=tmp_path)


def _config_dict(tmp_path: Path) -> dict[str, object]:
    return {
        "data": {
            "source": "synthetic",
            "universe": ["AAA", "BBB", "CCC", "DDD", "EEE", "FFF", "GGG", "HHH"],
            "start": "2020-01-01",
            "end": "2020-12-31",
            "seed": 31,
            "point_in_time_universe": False,
            "survivorship_bias_free": False,
            "corporate_actions_adjusted": False,
        },
        "experiment": {
            "name": "production_slice_signal",
            "train_fraction": 0.7,
            "signal": {
                "positive_factors": ["momentum_20d"],
                "negative_factors": ["volatility_20d"],
            },
            "backtest": {
                "holding_period": 5,
                "rebalance_days": 5,
                "quantile": 0.25,
            },
            "validation": {"walk_forward": {"window_count": 0}},
            "stress_tests": {
                "neutralization": {"enabled": False, "group_by": "sector"},
                "liquidity": {"enabled": False, "min_dollar_volume_rank": 0.0},
            },
            "shorting": {
                "borrow_fee_bps": 0.0,
                "shortable_symbols": ["AAA", "BBB", "CCC", "DDD", "EEE", "FFF", "GGG", "HHH"],
            },
            "robustness": {
                "bootstrap_iterations": 0,
                "holding_periods": [],
                "quantiles": [],
                "cost_multipliers": [],
            },
            "capacity": {
                "notionals": [],
                "max_trade_participation": 0.10,
                "max_position_weight": 0.35,
            },
            "baselines": [],
        },
        "report": {
            "output_path": str(tmp_path / "report.md"),
            "experiments_path": str(tmp_path / "experiments.csv"),
            "registry_path": str(tmp_path / "experiments.sqlite"),
        },
    }


def _config_yaml(tmp_path: Path) -> str:
    return f"""
data:
  source: synthetic
  universe: [AAA, BBB, CCC, DDD, EEE, FFF, GGG, HHH]
  start: "2020-01-01"
  end: "2020-12-31"
  seed: 31
  point_in_time_universe: false
  survivorship_bias_free: false
  corporate_actions_adjusted: false

experiment:
  name: production_slice_signal
  train_fraction: 0.7
  signal:
    positive_factors: [momentum_20d]
    negative_factors: [volatility_20d]
  backtest:
    holding_period: 5
    rebalance_days: 5
    quantile: 0.25
  validation:
    walk_forward:
      window_count: 0
  stress_tests:
    neutralization:
      enabled: false
      group_by: sector
    liquidity:
      enabled: false
      min_dollar_volume_rank: 0.0
  shorting:
    borrow_fee_bps: 0.0
    shortable_symbols: [AAA, BBB, CCC, DDD, EEE, FFF, GGG, HHH]
  robustness:
    bootstrap_iterations: 0
    holding_periods: []
    quantiles: []
    cost_multipliers: []
  capacity:
    notionals: []
    max_trade_participation: 0.10
    max_position_weight: 0.35
  baselines: []

report:
  output_path: "{tmp_path / 'report.md'}"
  experiments_path: "{tmp_path / 'experiments.csv'}"
  registry_path: "{tmp_path / 'experiments.sqlite'}"
"""


def _manifest(run_id: str, report_path: Path) -> dict[str, object]:
    return {
        "run_id": run_id,
        "generated_at": "2026-06-17T00:00:00Z",
        "experiment": "registry_test",
        "config": {
            "path": "configs/base.yaml",
            "copied_path": "results/runs/run-001/config.yaml",
            "sha256": "abc123",
        },
        "code": {
            "commit": "deadbeef",
            "branch": "main",
            "dirty": False,
        },
        "data": {
            "source": "synthetic",
            "snapshot_dataset_id": None,
            "observed_symbols": ["AAA", "BBB"],
        },
        "artifacts": {
            "report_path": str(report_path),
            "experiments_path": str(report_path.with_name("experiments.csv")),
            "manifest_path": str(report_path.with_name("manifest.json")),
        },
        "metrics": {
            "test": {
                "sharpe": 1.25,
                "total_return": 0.12,
                "ic_mean": 0.03,
                "max_drawdown": -0.08,
                "average_turnover": 1.1,
                "average_total_cost": 0.001,
            },
            "full": {
                "sharpe": 1.4,
                "total_return": 0.2,
            },
        },
    }
