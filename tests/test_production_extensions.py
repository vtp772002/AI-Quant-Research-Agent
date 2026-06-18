from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import pytest

from quant_research_agent.config import parse_config
from quant_research_agent.data.loader import MarketDataRequest, load_market_data
from quant_research_agent.execution_simulator import simulate_execution_plan
from quant_research_agent.main import main
from quant_research_agent.operations import batch_result_to_dict, run_research_batch
from quant_research_agent.paper_alpha import extract_alpha_template, template_to_config
from quant_research_agent.registry_export import export_registry_snapshot, verify_registry_governance_pack
from quant_research_agent.signals import SignalAsOfResult, SignalAsOfRow
from quant_research_agent.experiment_registry import record_run


def test_batch_runner_executes_config_and_writes_comparison_artifacts(tmp_path: Path):
    config_path = tmp_path / "batch.yaml"
    config_path.write_text(_config_yaml(tmp_path), encoding="utf-8")

    result = run_research_batch(
        config_paths=[config_path],
        output_dir=tmp_path / "batch",
        limit=1,
    )
    payload = batch_result_to_dict(result)

    assert result.status == "completed"
    assert payload["successful_runs"] == 1
    assert result.summary_path.exists()
    assert result.comparison_markdown_path is not None
    assert result.comparison_markdown_path.exists()
    assert result.comparison_json_path is not None
    assert result.comparison_json_path.exists()


def test_registry_export_writes_ndjson_manifest_and_postgres_handoff(tmp_path: Path):
    registry_path = tmp_path / "experiments.sqlite"
    record_run(registry_path, _manifest("run-001", tmp_path / "report.md"))

    export = export_registry_snapshot(registry_path, tmp_path / "registry_export")

    assert export.run_count == 1
    assert export.records_path.read_text(encoding="utf-8").count("\n") == 1
    manifest = json.loads(export.manifest_path.read_text(encoding="utf-8"))
    assert manifest["run_count"] == 1
    assert manifest["hash_chain_path"] == str(export.hash_chain_path)
    assert manifest["governance_manifest_path"] == str(export.governance_manifest_path)
    assert "CREATE TABLE IF NOT EXISTS experiment_runs" in export.postgres_sql_path.read_text(encoding="utf-8")


def test_registry_export_writes_verifiable_governance_pack(tmp_path: Path):
    registry_path = tmp_path / "experiments.sqlite"
    record_run(registry_path, _manifest("run-001", tmp_path / "report.md"))
    record_run(registry_path, _manifest("run-002", tmp_path / "report-2.md"))

    export = export_registry_snapshot(
        registry_path,
        tmp_path / "registry_export",
        owner="research-ops",
        minimum_retention_days=730,
    )

    governance = json.loads(export.governance_manifest_path.read_text(encoding="utf-8"))
    assert governance["schema_version"] == "registry_governance_v1"
    assert governance["owner"] == "research-ops"
    assert governance["retention"]["minimum_days"] == 730
    assert governance["run_count"] == 2
    assert governance["final_chain_hash"]
    assert {row["run_id"] for row in governance["family_evidence"]} == {"run-001", "run-002"}

    verification = verify_registry_governance_pack(export.output_dir)

    assert verification.valid
    assert verification.errors == []
    assert export.records_path in verification.checked_files
    assert export.hash_chain_path in verification.checked_files


def test_registry_governance_verification_detects_record_tampering(tmp_path: Path):
    registry_path = tmp_path / "experiments.sqlite"
    record_run(registry_path, _manifest("run-001", tmp_path / "report.md"))
    export = export_registry_snapshot(registry_path, tmp_path / "registry_export")
    line = json.loads(export.records_path.read_text(encoding="utf-8").splitlines()[0])
    line["selection_policy"] = "winner_after_search"
    export.records_path.write_text(json.dumps(line, sort_keys=True) + "\n", encoding="utf-8")

    verification = verify_registry_governance_pack(export.output_dir)

    assert not verification.valid
    assert "artifact records sha256 mismatch" in verification.errors
    assert any("record hash mismatch" in error for error in verification.errors)


def test_registry_governance_cli_verify_returns_failure_for_tampered_pack(tmp_path: Path, capsys: pytest.CaptureFixture[str]):
    registry_path = tmp_path / "experiments.sqlite"
    record_run(registry_path, _manifest("run-001", tmp_path / "report.md"))
    export = export_registry_snapshot(registry_path, tmp_path / "registry_export")
    export.hash_chain_path.write_text("", encoding="utf-8")

    exit_code = main(["--verify-registry-governance", str(export.output_dir)])
    payload = json.loads(capsys.readouterr().out)

    assert exit_code == 1
    assert payload["valid"] is False
    assert "artifact hash_chain sha256 mismatch" in payload["errors"]


def test_registry_governance_verification_reports_malformed_manifest(tmp_path: Path):
    output_dir = tmp_path / "registry_export"
    output_dir.mkdir()
    (output_dir / "registry_governance_manifest.json").write_text("{not json", encoding="utf-8")

    verification = verify_registry_governance_pack(output_dir)

    assert not verification.valid
    assert verification.errors == ["governance manifest is not valid JSON: Expecting property name enclosed in double quotes"]


def test_registry_export_rejects_unsafe_postgres_table_identifier(tmp_path: Path):
    with pytest.raises(ValueError, match="simple SQL identifier"):
        export_registry_snapshot(tmp_path / "experiments.sqlite", tmp_path / "export", postgres_table="runs;drop")


def test_registry_export_rejects_invalid_governance_metadata(tmp_path: Path):
    with pytest.raises(ValueError, match="owner must not be blank"):
        export_registry_snapshot(tmp_path / "experiments.sqlite", tmp_path / "export", owner=" ")
    with pytest.raises(ValueError, match="minimum_retention_days must be positive"):
        export_registry_snapshot(tmp_path / "experiments.sqlite", tmp_path / "export", minimum_retention_days=0)


def test_vendor_snapshot_source_loads_validated_snapshot_rows(tmp_path: Path):
    snapshot_path = tmp_path / "vendor_snapshot.csv"
    _write_market_csv(snapshot_path)

    data = load_market_data(
        MarketDataRequest(
            source="vendor_snapshot",
            universe=["AAA", "BBB"],
            start="2020-01-01",
            end="2020-04-30",
            snapshot_path=snapshot_path,
        )
    )

    assert sorted(data.index.get_level_values("symbol").unique()) == ["AAA", "BBB"]
    assert {"open", "high", "low", "close", "adj_close", "volume"}.issubset(data.columns)


def test_paper_to_alpha_extracts_template_from_research_text():
    template = extract_alpha_template(
        """
        A weekly momentum and low volatility strategy shows that relative strength
        signals combined with lower realized risk can improve forward returns.
        The holding period is 10 trading days in the reported backtest.
        """,
        name="Momentum Paper",
    )
    payload = template_to_config(template)

    assert template.name == "momentum_paper"
    assert "momentum_20d" in template.positive_factors
    assert "volatility_20d" in template.negative_factors
    assert template.holding_period == 10
    assert payload["experiment"]["signal"]["positive_factors"]


def test_execution_simulator_blocks_orders_that_breach_participation(tmp_path: Path):
    config = parse_config(_config_dict(tmp_path), base_dir=tmp_path)
    signal = SignalAsOfResult(
        as_of_date="2020-06-30",
        signal_date="2020-06-30",
        experiment=config.experiment.name,
        model_version="test",
        warnings=[],
        rows=[
            SignalAsOfRow(
                symbol="AAA",
                signal_score=1.0,
                rank=1,
                target_weight=0.50,
                reason="test",
                risk_status="pass",
                data_timestamp="2020-06-30",
                model_version="test",
            ),
            SignalAsOfRow(
                symbol="BBB",
                signal_score=-1.0,
                rank=2,
                target_weight=-0.50,
                reason="test",
                risk_status="pass",
                data_timestamp="2020-06-30",
                model_version="test",
            ),
        ],
    )

    simulation = simulate_execution_plan(config, signal, max_participation=0.25)

    assert {order.status for order in simulation.orders} == {"blocked"}
    assert all(order.scheduled_notional == 0.0 for order in simulation.orders)
    assert any("does not route orders" in warning for warning in simulation.warnings)


def _write_market_csv(path: Path) -> None:
    dates = pd.bdate_range("2020-01-01", "2020-04-30")
    rows = []
    for symbol, offset in [("AAA", 0), ("BBB", 5)]:
        for index, date in enumerate(dates):
            close = 100.0 + offset + index * 0.1
            rows.append(
                {
                    "date": date.date().isoformat(),
                    "symbol": symbol,
                    "open": close - 0.1,
                    "high": close + 0.2,
                    "low": close - 0.2,
                    "close": close,
                    "adj_close": close,
                    "volume": 1_000_000 + index,
                }
            )
    pd.DataFrame(rows).to_csv(path, index=False)


def _config_yaml(tmp_path: Path) -> str:
    return f"""
data:
  source: synthetic
  universe: [AAA, BBB, CCC, DDD, EEE, FFF, GGG, HHH]
  start: "2020-01-01"
  end: "2020-12-31"
  seed: 17
  point_in_time_universe: false
  survivorship_bias_free: false
  corporate_actions_adjusted: false

experiment:
  name: batch_extension_signal
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


def _config_dict(tmp_path: Path) -> dict[str, object]:
    import yaml

    return yaml.safe_load(_config_yaml(tmp_path))


def _manifest(run_id: str, report_path: Path) -> dict[str, object]:
    return {
        "run_id": run_id,
        "generated_at": "2026-06-17T00:00:00Z",
        "experiment": "registry_export_test",
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
            "research_validity": {
                "verdict": "PROMOTE",
                "agent_p_value": 0.01,
                "agent_q_value": 0.02,
            },
        },
        "experiment_family": {
            "family_id": "governance-family-v1",
            "hypothesis_id": "governance-hypothesis",
            "candidate_id": run_id,
            "selection_policy": "pre_registered",
        },
    }
