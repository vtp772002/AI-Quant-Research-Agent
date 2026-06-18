from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pandas as pd

from quant_research_agent.data.loader import generate_synthetic_ohlcv
from quant_research_agent.data.snapshot import file_sha256


def test_cli_e2e_writes_report_json_and_experiment_rows(tmp_path: Path):
    config_path = tmp_path / "e2e.yaml"
    membership_path = tmp_path / "membership.csv"
    locate_path = tmp_path / "locates.csv"
    report_path = tmp_path / "report.md"
    experiments_path = tmp_path / "experiments.csv"
    membership_path.write_text(
        "symbol,start,end\n"
        "AAA,2020-01-01,\n"
        "BBB,2020-01-01,\n"
        "CCC,2020-01-01,\n"
        "DDD,2020-01-01,\n"
        "EEE,2020-01-01,\n"
        "FFF,2020-01-01,\n"
        "GGG,2020-01-01,\n"
        "HHH,2020-01-01,\n",
        encoding="utf-8",
    )
    _write_locate_history(
        path=locate_path,
        symbols=["AAA", "BBB", "CCC", "DDD", "EEE", "FFF", "GGG", "HHH"],
        start="2020-01-01",
        end="2022-12-31",
    )
    config_path.write_text(
        f"""
data:
  source: synthetic
  universe_provider:
    kind: csv
    path: "{membership_path}"
  start: "2020-01-01"
  end: "2022-12-31"
  seed: 19
  point_in_time_universe: false
  survivorship_bias_free: false
  corporate_actions_adjusted: false
  sectors:
    AAA: technology
    BBB: technology
    CCC: consumer
    DDD: consumer
    EEE: industrials
    FFF: industrials
    GGG: healthcare
    HHH: healthcare

experiment:
  name: cli_e2e_signal
  family:
    family_id: cli-e2e-family
    hypothesis_id: cli-e2e-hypothesis
    candidate_id: base
    selection_policy: pre_registered
  train_fraction: 0.7
  signal:
    positive_factors: [momentum_20d]
    negative_factors: [volatility_20d]
    rank_method: percentile
  backtest:
    holding_period: 5
    rebalance_days: 5
    quantile: 0.25
    transaction_cost_bps: 2.0
    spread_cost_bps: 2.0
    market_impact_coefficient: 0.10
    portfolio_notional: 5000000
  validation:
    walk_forward:
      window_count: 2
      min_train_fraction: 0.4
    research_validity:
      enabled: true
      holdout_fraction: 0.15
      fdr_alpha: 0.25
      require_positive_return: true
      require_baseline_outperformance: true
      require_walk_forward_stability: true
      require_data_readiness: true
  stress_tests:
    neutralization:
      enabled: true
      group_by: sector
    liquidity:
      enabled: true
      min_dollar_volume_rank: 0.2
  shorting:
    borrow_fee_bps: 100.0
    shortable_symbols: [AAA, BBB, CCC, DDD, EEE, FFF]
    locate_history_path: "{locate_path}"
  robustness:
    bootstrap_iterations: 50
    bootstrap_seed: 123
    holding_periods: [3, 5]
    quantiles: [0.2, 0.25]
    cost_multipliers: [0.5, 1.0, 2.0]
  capacity:
    notionals: [1000000, 5000000, 20000000]
    max_trade_participation: 0.005
    max_position_weight: 0.35
  baselines:
    - name: momentum_20d_only
      positive_factors: [momentum_20d]
      negative_factors: []
    - name: random_cross_section
      positive_factors: []
      negative_factors: []

report:
  output_path: "{report_path}"
  experiments_path: "{experiments_path}"
""",
        encoding="utf-8",
    )
    env = os.environ.copy()
    env["PYTHONPATH"] = str(Path.cwd() / "src")

    completed = subprocess.run(
        [sys.executable, "-m", "quant_research_agent.main", "--config", str(config_path), "--json"],
        cwd=Path.cwd(),
        env=env,
        check=True,
        text=True,
        capture_output=True,
    )

    payload = json.loads(completed.stdout)
    assert payload["experiment"] == "cli_e2e_signal"
    assert payload["run"]["run_id"]
    assert payload["run"]["config_sha256"] == file_sha256(config_path)
    manifest_path = Path(payload["run"]["manifest_path"])
    assert manifest_path.exists()
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert manifest["run_id"] == payload["run"]["run_id"]
    assert manifest["config"]["sha256"] == file_sha256(config_path)
    assert Path(manifest["config"]["copied_path"]).exists()
    assert manifest["artifacts"]["report_sha256"] == file_sha256(report_path)
    assert manifest["artifacts"]["experiments_sha256"] == file_sha256(experiments_path)
    assert manifest["data"]["locate_history_sha256"] == file_sha256(locate_path)
    assert manifest["experiment_family"] == {
        "candidate_id": "base",
        "family_id": "cli-e2e-family",
        "hypothesis_id": "cli-e2e-hypothesis",
        "selection_policy": "pre_registered",
    }
    assert manifest["research_validity"] == payload["research_validity"]
    assert manifest["metrics"]["holdout"] == payload["metrics"]["holdout"]
    assert manifest["metrics"]["validation"] == payload["metrics"]["test"]
    assert manifest["metrics"]["research_validity"]["verdict"] == payload["research_validity"]["verdict"]
    assert payload["universe"]["point_in_time"]
    assert payload["universe"]["survivorship_bias_free"]
    assert payload["universe"]["symbol_count"] == 8
    assert payload["metrics"]["test"]["average_total_cost"] > 0
    assert payload["metrics"]["test"]["average_impact_cost"] > 0
    assert payload["metrics"]["test"]["average_borrow_cost"] > 0
    assert payload["metrics"]["holdout"]["observations"] > 0.0
    assert payload["research_validity"]["verdict"] in {"PROMOTE", "REVIEW", "REJECT"}
    assert payload["research_validity"]["enabled"] is True
    assert payload["research_validity"]["candidates"][0]["name"] == "agent_signal"
    assert payload["shorting"]["locate_history_path"] == str(locate_path)
    assert payload["borrow_availability"]["unavailable_rows"] > 0
    assert payload["borrow_availability"]["hard_to_borrow_rows"] > 0
    assert payload["robustness"]["bootstrap"]["iterations"] == 50
    assert len(payload["robustness"]["parameter_sensitivity"]) == 4
    assert len(payload["robustness"]["cost_sensitivity"]) == 3
    assert payload["capacity"]["concentration"]["max_single_name_weight"] > 0
    assert len(payload["capacity"]["capacity_curve"]) == 3
    assert any(item["participation_breach_count"] > 0 for item in payload["capacity"]["capacity_curve"])
    assert len(payload["walk_forward"]["agent_signal"]) == 2
    assert payload["data_integrity"]["warnings"]
    assert "sector_neutral_signal" in payload["stress_tests"]

    report = report_path.read_text(encoding="utf-8")
    assert "Data Integrity" in report
    assert "Universe source: `csv:" in report
    assert "Point-in-time universe: yes" in report
    assert "Execution Costs" in report
    assert "Borrow Availability" in report
    assert "Hard-to-borrow rows" in report
    assert "Capacity Diagnostics" in report
    assert "Capacity curve" in report
    assert "Robustness Diagnostics" in report
    assert "Avg borrow cost" in report
    assert "Stress Tests" in report
    assert "Run Reproducibility" in report
    assert f"Run ID: `{payload['run']['run_id']}`" in report

    rows = experiments_path.read_text(encoding="utf-8")
    assert "test_average_total_cost" in rows
    assert "test_average_borrow_cost" in rows
    assert "sector_neutral_signal" in rows
    frame = pd.read_csv(experiments_path)
    assert set(frame["universe_size"]) == {8}
    assert frame["locate_history"].str.contains("locates.csv").any()
    assert set(frame["run_id"]) == {payload["run"]["run_id"]}
    assert set(frame["config_sha256"]) == {file_sha256(config_path)}
    assert set(frame["validity_verdict"]) == {payload["research_validity"]["verdict"]}
    assert frame["validity_enabled"].all()
    assert frame["holdout_start"].notna().all()
    assert frame["holdout_sharpe"].notna().all()
    assert frame["holdout_ic_mean"].notna().all()
    assert frame["holdout_total_return"].notna().all()
    assert frame["agent_fdr_q_value"].between(0.0, 1.0).all()


def test_cli_e2e_runs_csv_snapshot_with_manifest_provenance(tmp_path: Path):
    symbols = ["AAA", "BBB", "CCC", "DDD", "EEE", "FFF", "GGG", "HHH"]
    config_path = tmp_path / "snapshot_e2e.yaml"
    snapshot_path = tmp_path / "snapshot.csv"
    manifest_path = tmp_path / "snapshot.yaml"
    membership_path = tmp_path / "membership.csv"
    report_path = tmp_path / "snapshot_report.md"
    experiments_path = tmp_path / "snapshot_experiments.csv"
    source = generate_synthetic_ohlcv(
        symbols=symbols,
        start="2020-01-01",
        end="2022-12-31",
        seed=23,
    )
    source.reset_index().to_csv(snapshot_path, index=False)
    membership_path.write_text(
        "symbol,start,end\n" + "".join(f"{symbol},2020-01-01,\n" for symbol in symbols),
        encoding="utf-8",
    )
    manifest_path.write_text(
        "\n".join(
            [
                "dataset_id: golden-cli-e2e-v1",
                "vendor: InternalGolden",
                "as_of: '2023-01-03'",
                "created_at: '2023-01-03T00:00:00Z'",
                f"content_sha256: {file_sha256(snapshot_path)}",
                f"row_count: {len(source)}",
                "symbols: [AAA, BBB, CCC, DDD, EEE, FFF, GGG, HHH]",
                "start: '2020-01-01'",
                "end: '2022-12-30'",
                "point_in_time_universe: true",
                "survivorship_bias_free: true",
                "corporate_actions_adjusted: true",
            ]
        ),
        encoding="utf-8",
    )
    config_path.write_text(
        f"""
data:
  source: csv_snapshot
  snapshot:
    path: "{snapshot_path}"
    manifest_path: "{manifest_path}"
    require_manifest_hash: true
  universe_provider:
    kind: csv
    path: "{membership_path}"
  start: "2020-01-01"
  end: "2022-12-31"
  sectors:
    AAA: technology
    BBB: technology
    CCC: consumer
    DDD: consumer
    EEE: industrials
    FFF: industrials
    GGG: healthcare
    HHH: healthcare

experiment:
  name: snapshot_cli_e2e_signal
  train_fraction: 0.7
  signal:
    positive_factors: [momentum_20d]
    negative_factors: [volatility_20d]
    rank_method: percentile
  backtest:
    holding_period: 5
    rebalance_days: 5
    quantile: 0.25
    transaction_cost_bps: 2.0
    spread_cost_bps: 2.0
    market_impact_coefficient: 0.10
    portfolio_notional: 5000000
  validation:
    walk_forward:
      window_count: 1
      min_train_fraction: 0.4
  stress_tests:
    neutralization:
      enabled: true
      group_by: sector
    liquidity:
      enabled: true
      min_dollar_volume_rank: 0.2
  shorting:
    borrow_fee_bps: 100.0
    shortable_symbols: [AAA, BBB, CCC, DDD, EEE, FFF]
  robustness:
    bootstrap_iterations: 25
    bootstrap_seed: 123
    holding_periods: [3, 5]
    quantiles: [0.2]
    cost_multipliers: [1.0, 2.0]
  capacity:
    notionals: [1000000, 5000000]
    max_trade_participation: 0.10
    max_position_weight: 0.35
  baselines:
    - name: momentum_20d_only
      positive_factors: [momentum_20d]
      negative_factors: []

report:
  output_path: "{report_path}"
  experiments_path: "{experiments_path}"
""",
        encoding="utf-8",
    )
    env = os.environ.copy()
    env["PYTHONPATH"] = str(Path.cwd() / "src")

    completed = subprocess.run(
        [sys.executable, "-m", "quant_research_agent.main", "--config", str(config_path), "--json"],
        cwd=Path.cwd(),
        env=env,
        check=True,
        text=True,
        capture_output=True,
    )

    payload = json.loads(completed.stdout)
    provenance = payload["data_integrity"]["provenance"]
    manifest = json.loads(Path(payload["run"]["manifest_path"]).read_text(encoding="utf-8"))
    assert payload["experiment"] == "snapshot_cli_e2e_signal"
    assert payload["run"]["config_sha256"] == file_sha256(config_path)
    assert manifest["data"]["snapshot_content_sha256"] == file_sha256(snapshot_path)
    assert provenance["dataset_id"] == "golden-cli-e2e-v1"
    assert provenance["hash_matches"]
    assert provenance["row_count_matches"]
    assert provenance["symbol_set_matches"]
    assert provenance["date_range_matches"]
    assert payload["data_integrity"]["point_in_time_universe"]
    assert payload["data_integrity"]["survivorship_bias_free"]
    assert payload["data_integrity"]["corporate_actions_adjusted"]
    assert payload["robustness"]["bootstrap"]["iterations"] == 25
    assert len(payload["capacity"]["capacity_curve"]) == 2

    report = report_path.read_text(encoding="utf-8")
    assert "Snapshot dataset: `golden-cli-e2e-v1`" in report
    assert "Snapshot hash valid: yes" in report
    assert "Capacity Diagnostics" in report
    assert "Run Reproducibility" in report
    frame = pd.read_csv(experiments_path)
    assert set(frame["dataset_id"]) == {"golden-cli-e2e-v1"}
    assert set(frame["run_id"]) == {payload["run"]["run_id"]}


def _write_locate_history(path: Path, symbols: list[str], start: str, end: str) -> None:
    dates = pd.bdate_range(start=start, end=end)
    rows = ["date,symbol,shortable,borrow_fee_bps,available_quantity"]
    for date in dates:
        for symbol in symbols:
            shortable = symbol not in {"GGG", "HHH"}
            if symbol == "FFF" and date.month in {6, 7}:
                shortable = False
            fee = 900.0 if symbol == "EEE" else 125.0
            quantity = 0 if not shortable else 1_000_000
            rows.append(f"{date.date().isoformat()},{symbol},{str(shortable).lower()},{fee},{quantity}")
    path.write_text("\n".join(rows), encoding="utf-8")
