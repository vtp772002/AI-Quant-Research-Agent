from __future__ import annotations

import json
from pathlib import Path

import pytest
import yaml

from quant_research_agent.experiment_registry import record_run
from quant_research_agent.idea_review import (
    approved_config_paths,
    enforce_review_gate,
    load_review_queue,
    mark_configs_ran,
    review_audit_events,
    review_summary,
    update_idea_status,
)
from quant_research_agent.llm_provider import build_research_prompt_payload, run_structured_provider
from quant_research_agent.research_agents import (
    ExperimentIdea,
    LLMResearchAgent,
    critique_run_manifest,
    generate_idea_configs,
    generate_idea_configs_with_provider,
    load_research_memory,
    mine_alpha,
    paper_to_alpha_v2,
    validate_experiment_idea,
)
from quant_research_agent.config import load_config


def test_validate_experiment_idea_rejects_unknown_factor():
    idea = ExperimentIdea(
        name="bad_idea",
        hypothesis="Bad idea",
        positive_factors=["unknown_factor"],
        negative_factors=[],
        holding_period=5,
        quantile=0.2,
        rationale="test",
        confidence=0.8,
        warnings=[],
    )

    validation = validate_experiment_idea(idea)

    assert not validation.valid
    assert "unknown factors" in validation.errors[0]


def test_llm_research_agent_generates_valid_ideas_from_memory(tmp_path: Path):
    registry_path = tmp_path / "experiments.sqlite"
    record_run(registry_path, _manifest("run-good", tmp_path / "report.md", sharpe=1.1))
    memory = load_research_memory(registry_path)
    base_config = load_config(_base_config(tmp_path))

    ideas = LLMResearchAgent().generate_ideas(
        base_config=base_config,
        memory=memory,
        objective="Find robust alpha after costs",
        count=3,
    )

    assert len(ideas) == 3
    assert all(validate_experiment_idea(idea).valid for idea in ideas)
    assert all("Find robust alpha" in idea.hypothesis for idea in ideas)


def test_generate_idea_configs_writes_valid_config_variants(tmp_path: Path):
    base_config_path = _base_config(tmp_path)
    ideas, config_paths, ideas_path = generate_idea_configs(
        base_config_path=base_config_path,
        output_dir=tmp_path / "ideas",
        objective="Generate cost-aware alpha ideas",
        count=2,
        registry_path=tmp_path / "empty.sqlite",
    )

    assert len(ideas) == 2
    assert len(config_paths) == 2
    assert ideas_path.exists()
    review_queue_path = tmp_path / "ideas" / "review_queue.json"
    assert review_queue_path.exists()
    summary = review_summary(review_queue_path)
    assert summary["counts"]["draft"] == 2
    assert Path(str(summary["audit_path"])).exists()
    assert [event["event_type"] for event in review_audit_events(review_queue_path)] == ["created", "created"]
    for config_path in config_paths:
        config = yaml.safe_load(config_path.read_text(encoding="utf-8"))
        assert config["experiment"]["name"]
        assert config["report"]["registry_path"].endswith("experiments.sqlite")


def test_critic_rejects_weak_manifest_and_proposes_followup(tmp_path: Path):
    manifest_path = tmp_path / "manifest.json"
    manifest_path.write_text(json.dumps(_manifest("weak-run", tmp_path / "report.md", sharpe=-0.2)), encoding="utf-8")

    critique = critique_run_manifest(manifest_path)

    assert critique.verdict == "reject"
    assert any("Sharpe" in reason for reason in critique.reasons)
    assert validate_experiment_idea(critique.next_experiment).valid


def test_paper_to_alpha_v2_returns_validation_and_bias_warnings():
    payload = paper_to_alpha_v2(
        """
        This paper studies weekly momentum, liquidity, and low volatility.
        It also discusses analyst sentiment and next quarter revisions.
        """,
        name="Paper V2",
    )

    assert payload["validation"]["valid"] is True
    assert "sentiment" in payload["factor_mapping"]["unsupported_concepts"]
    assert payload["bias_warnings"]


def test_mine_alpha_generates_configs_without_running_batch(tmp_path: Path):
    result = mine_alpha(
        base_config_path=_base_config(tmp_path),
        output_dir=tmp_path / "mining",
        objective="Mine alpha ideas",
        count=2,
        registry_path=tmp_path / "memory.sqlite",
        run_generated=False,
    )

    assert result.batch_result is None
    assert result.ideas_path.exists()
    assert result.review_queue_path.exists()
    assert len(result.config_paths) == 2
    assert all(path.exists() for path in result.config_paths)


def test_mine_alpha_requires_human_approval_before_running_generated_configs(tmp_path: Path):
    with pytest.raises(PermissionError, match="must be approved"):
        mine_alpha(
            base_config_path=_base_config(tmp_path),
            output_dir=tmp_path / "mining",
            objective="Mine alpha ideas",
            count=1,
            registry_path=tmp_path / "memory.sqlite",
            run_generated=True,
        )


def test_review_queue_tracks_human_approval_and_ran_status(tmp_path: Path):
    _, config_paths, _ = generate_idea_configs(
        base_config_path=_base_config(tmp_path),
        output_dir=tmp_path / "ideas",
        objective="Generate cost-aware alpha ideas",
        count=1,
        registry_path=tmp_path / "empty.sqlite",
    )
    queue_path = tmp_path / "ideas" / "review_queue.json"

    payload = load_review_queue(queue_path)
    idea_name = payload["records"][0]["idea_name"]
    assert approved_config_paths(queue_path) == []

    update_idea_status(
        queue_path,
        idea_name=idea_name,
        status="approved",
        note="Human approved.",
        actor="researcher@example.test",
    )

    assert approved_config_paths(queue_path) == config_paths
    assert enforce_review_gate(queue_path, config_paths) == config_paths
    summary = review_summary(queue_path)
    assert summary["counts"]["approved"] == 1
    assert summary["records"][0]["note"] == "Human approved."

    mark_configs_ran(queue_path, config_paths, note="Ran after approval.", actor="batch-runner")

    summary = review_summary(queue_path)
    assert summary["counts"]["ran"] == 1
    assert summary["records"][0]["note"] == "Ran after approval."
    events = review_audit_events(queue_path)
    assert [event["event_type"] for event in events] == ["created", "status_changed", "ran"]
    assert events[1]["from_status"] == "draft"
    assert events[1]["to_status"] == "approved"
    assert events[1]["actor"] == "researcher@example.test"
    assert events[2]["from_status"] == "approved"
    assert events[2]["to_status"] == "ran"
    assert events[2]["actor"] == "batch-runner"


def test_fixture_provider_generates_validated_ideas_and_transcript(tmp_path: Path):
    fixture_path = tmp_path / "fixture.json"
    fixture_path.write_text(
        json.dumps(
            {
                "ideas": [
                    {
                        "name": "fixture_momentum_low_risk",
                        "hypothesis": "Fixture idea should validate through the provider boundary.",
                        "positive_factors": ["momentum_20d"],
                        "negative_factors": ["volatility_20d"],
                        "holding_period": 5,
                        "quantile": 0.2,
                        "rationale": "Fixture provider test.",
                        "confidence": 0.8,
                        "warnings": ["review before running"],
                    }
                ]
            }
        ),
        encoding="utf-8",
    )

    ideas, config_paths, ideas_path, review_queue_path, artifacts = generate_idea_configs_with_provider(
        base_config_path=_base_config(tmp_path),
        output_dir=tmp_path / "fixture_ideas",
        objective="Use fixture provider",
        count=1,
        registry_path=tmp_path / "memory.sqlite",
        provider="fixture",
        fixture_path=fixture_path,
    )

    assert [idea.name for idea in ideas] == ["fixture_momentum_low_risk"]
    assert config_paths[0].exists()
    assert ideas_path.exists()
    assert review_queue_path.exists()
    assert review_summary(review_queue_path)["counts"]["draft"] == 1
    assert artifacts is not None
    assert artifacts.prompt_path.exists()
    assert artifacts.response_path.exists()
    assert artifacts.transcript_path.exists()


def test_command_provider_requires_explicit_external_allowance(tmp_path: Path):
    prompt = build_research_prompt_payload(
        objective="guard external command",
        count=1,
        factor_names=["momentum_20d"],
        memory={"run_count": 0},
        base_experiment={"name": "base"},
    )

    with pytest.raises(PermissionError, match="requires --allow-external-llm"):
        run_structured_provider(
            provider="command",
            prompt_payload=prompt,
            transcript_dir=tmp_path / "transcripts",
            command="python -c 'print({})'",
            allow_external=False,
        )


def _base_config(tmp_path: Path) -> Path:
    config_path = tmp_path / "base.yaml"
    config_path.write_text(
        f"""
data:
  source: synthetic
  universe: [AAA, BBB, CCC, DDD, EEE, FFF, GGG, HHH]
  start: "2020-01-01"
  end: "2020-12-31"
  seed: 19
  point_in_time_universe: false
  survivorship_bias_free: false
  corporate_actions_adjusted: false

experiment:
  name: research_agent_base
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
""",
        encoding="utf-8",
    )
    return config_path


def _manifest(run_id: str, report_path: Path, sharpe: float = 1.0) -> dict[str, object]:
    return {
        "run_id": run_id,
        "generated_at": "2026-06-17T00:00:00Z",
        "experiment": "research_agent_test",
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
                "sharpe": sharpe,
                "total_return": 0.10 if sharpe > 0 else -0.05,
                "ic_mean": 0.03 if sharpe > 0 else -0.01,
                "max_drawdown": -0.08,
                "average_turnover": 1.1,
                "average_total_cost": 0.001,
            },
            "full": {
                "sharpe": sharpe,
                "total_return": 0.2,
            },
        },
    }
