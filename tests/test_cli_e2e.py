from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pandas as pd


def test_cli_e2e_writes_report_json_and_experiment_rows(tmp_path: Path):
    config_path = tmp_path / "e2e.yaml"
    membership_path = tmp_path / "membership.csv"
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
  shorting:
    borrow_fee_bps: 100.0
    shortable_symbols: [AAA, BBB, CCC, DDD, EEE, FFF]
  robustness:
    bootstrap_iterations: 50
    bootstrap_seed: 123
    holding_periods: [3, 5]
    quantiles: [0.2, 0.25]
    cost_multipliers: [0.5, 1.0, 2.0]
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
    assert payload["universe"]["point_in_time"]
    assert payload["universe"]["survivorship_bias_free"]
    assert payload["universe"]["symbol_count"] == 8
    assert payload["metrics"]["test"]["average_total_cost"] > 0
    assert payload["metrics"]["test"]["average_impact_cost"] > 0
    assert payload["metrics"]["test"]["average_borrow_cost"] > 0
    assert payload["robustness"]["bootstrap"]["iterations"] == 50
    assert len(payload["robustness"]["parameter_sensitivity"]) == 4
    assert len(payload["robustness"]["cost_sensitivity"]) == 3
    assert len(payload["walk_forward"]["agent_signal"]) == 2
    assert payload["data_integrity"]["warnings"]
    assert "sector_neutral_signal" in payload["stress_tests"]

    report = report_path.read_text(encoding="utf-8")
    assert "Data Integrity" in report
    assert "Universe source: `csv:" in report
    assert "Point-in-time universe: yes" in report
    assert "Execution Costs" in report
    assert "Robustness Diagnostics" in report
    assert "Avg borrow cost" in report
    assert "Stress Tests" in report

    rows = experiments_path.read_text(encoding="utf-8")
    assert "test_average_total_cost" in rows
    assert "test_average_borrow_cost" in rows
    assert "sector_neutral_signal" in rows
    frame = pd.read_csv(experiments_path)
    assert set(frame["universe_size"]) == {8}
