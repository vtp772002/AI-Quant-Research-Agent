from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path


def test_cli_e2e_writes_report_json_and_experiment_rows(tmp_path: Path):
    config_path = tmp_path / "e2e.yaml"
    report_path = tmp_path / "report.md"
    experiments_path = tmp_path / "experiments.csv"
    config_path.write_text(
        f"""
data:
  source: synthetic
  universe: [AAA, BBB, CCC, DDD, EEE, FFF, GGG, HHH]
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
  stress_tests:
    neutralization:
      enabled: true
      group_by: sector
    liquidity:
      enabled: true
      min_dollar_volume_rank: 0.2
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
    assert payload["metrics"]["test"]["average_total_cost"] > 0
    assert payload["metrics"]["test"]["average_impact_cost"] > 0
    assert len(payload["walk_forward"]["agent_signal"]) == 2
    assert payload["data_integrity"]["warnings"]
    assert "sector_neutral_signal" in payload["stress_tests"]

    report = report_path.read_text(encoding="utf-8")
    assert "Data Integrity" in report
    assert "Execution Costs" in report
    assert "Stress Tests" in report

    rows = experiments_path.read_text(encoding="utf-8")
    assert "test_average_total_cost" in rows
    assert "sector_neutral_signal" in rows
