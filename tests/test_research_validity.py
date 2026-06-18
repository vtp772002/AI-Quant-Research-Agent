from __future__ import annotations

from types import SimpleNamespace

import pandas as pd
import pytest

from quant_research_agent.agents.research_validity import (
    ValidityCheck,
    adjust_pvalues_benjamini_hochberg,
    build_candidate_evidence,
    evaluate_research_validity,
    one_sided_positive_pvalue,
    select_validity_verdict,
)
from quant_research_agent.config import parse_config
from quant_research_agent.data.integrity import DataIntegrityReport


def test_one_sided_positive_pvalue_decreases_with_tstat():
    assert one_sided_positive_pvalue(-1.0) > 0.5
    assert one_sided_positive_pvalue(0.0) == 0.5
    assert one_sided_positive_pvalue(2.0) < 0.05


def test_benjamini_hochberg_returns_monotonic_qvalues_in_original_order():
    adjusted = adjust_pvalues_benjamini_hochberg(
        {"agent_signal": 0.01, "baseline": 0.04, "stress": 0.03, "weak": 0.80}
    )

    assert adjusted["agent_signal"] == 0.04
    assert adjusted["baseline"] == pytest.approx(0.0533333333)
    assert adjusted["stress"] == pytest.approx(0.0533333333)
    assert adjusted["weak"] == 0.80


def test_benjamini_hochberg_empty_family_is_empty():
    assert adjust_pvalues_benjamini_hochberg({}) == {}


def test_candidate_evidence_uses_pvalue_one_for_insufficient_ic_observations():
    backtest = _backtest(
        holdout_observations=1,
        holdout_sharpe=1.0,
        holdout_ic_mean=0.05,
        holdout_ic_tstat=4.0,
        holdout_return=0.10,
    )

    evidence = build_candidate_evidence(
        name="agent_signal",
        family="primary",
        backtest=backtest,
    )

    assert evidence.name == "agent_signal"
    assert evidence.family == "primary"
    assert evidence.holdout_observations == 1
    assert evidence.p_value == 1.0
    assert evidence.q_value == 1.0


def test_select_validity_verdict_promotes_when_all_required_checks_pass():
    checks = [
        _check("positive_holdout_sharpe", True),
        _check("positive_holdout_ic", True),
        _check("fdr_significant", True),
        _check("positive_holdout_return", True),
        _check("beats_best_baseline", True),
        _check("walk_forward_stable", True),
        _check("data_ready", True),
    ]

    assert select_validity_verdict(enabled=True, checks=checks) == "PROMOTE"


def test_select_validity_verdict_rejects_when_core_evidence_fails():
    checks = [
        _check("positive_holdout_sharpe", False),
        _check("positive_holdout_ic", True),
        _check("fdr_significant", True),
        _check("positive_holdout_return", True),
        _check("data_ready", True),
    ]

    assert select_validity_verdict(enabled=True, checks=checks) == "REJECT"


def test_select_validity_verdict_reviews_when_core_passes_but_data_not_ready():
    checks = [
        _check("positive_holdout_sharpe", True),
        _check("positive_holdout_ic", True),
        _check("fdr_significant", True),
        _check("positive_holdout_return", True),
        _check("data_ready", False),
    ]

    assert select_validity_verdict(enabled=True, checks=checks) == "REVIEW"


def test_evaluate_research_validity_promotes_when_every_required_check_passes():
    config = _config(
        fdr_alpha=0.20,
        require_data_readiness=True,
        require_baseline_outperformance=True,
        require_walk_forward_stability=True,
    )
    agent = _backtest(
        holdout_observations=40,
        holdout_sharpe=1.2,
        holdout_ic_mean=0.08,
        holdout_ic_tstat=3.0,
        holdout_return=0.12,
        walk_forward_sharpes=[0.2, 0.4, 0.1],
    )
    baselines = {
        "baseline": _backtest(
            holdout_observations=40,
            holdout_sharpe=0.8,
            holdout_ic_mean=0.02,
            holdout_ic_tstat=0.2,
            holdout_return=0.04,
        )
    }

    result = evaluate_research_validity(
        config=config,
        agent=agent,
        baselines=baselines,
        stress_tests={},
        parameter_variants=[],
        cost_variants=[],
        data_integrity=_data_integrity(ready=True),
    )

    assert result.enabled
    assert result.verdict == "PROMOTE"
    assert result.holdout_start == "2024-03-01"
    assert [candidate.name for candidate in result.candidates] == ["agent_signal", "baseline"]
    assert {check.name: check.passed for check in result.checks}["fdr_significant"] is True
    assert result.reasons == []


def test_evaluate_research_validity_rejects_failed_core_evidence():
    config = _config(fdr_alpha=0.10)
    agent = _backtest(
        holdout_observations=30,
        holdout_sharpe=-0.1,
        holdout_ic_mean=0.04,
        holdout_ic_tstat=3.0,
        holdout_return=0.02,
    )

    result = evaluate_research_validity(
        config=config,
        agent=agent,
        baselines={},
        stress_tests={},
        parameter_variants=[],
        cost_variants=[],
        data_integrity=_data_integrity(ready=True),
    )

    assert result.verdict == "REJECT"
    failed = {check.name for check in result.checks if check.required and check.passed is False}
    assert "positive_holdout_sharpe" in failed
    assert any("Holdout Sharpe" in reason for reason in result.reasons)


def test_evaluate_research_validity_reviews_when_core_passes_but_data_is_not_ready():
    config = _config(fdr_alpha=0.20, require_data_readiness=True)
    agent = _backtest(
        holdout_observations=30,
        holdout_sharpe=1.1,
        holdout_ic_mean=0.06,
        holdout_ic_tstat=3.0,
        holdout_return=0.05,
    )

    result = evaluate_research_validity(
        config=config,
        agent=agent,
        baselines={},
        stress_tests={},
        parameter_variants=[],
        cost_variants=[],
        data_integrity=_data_integrity(ready=False),
    )

    assert result.verdict == "REVIEW"
    assert {check.name: check.passed for check in result.checks}["data_ready"] is False


def test_evaluate_research_validity_includes_stress_and_sensitivity_family():
    config = _config(fdr_alpha=0.25, require_baseline_outperformance=False)
    agent = _backtest(
        holdout_observations=30,
        holdout_sharpe=1.0,
        holdout_ic_mean=0.06,
        holdout_ic_tstat=3.0,
        holdout_return=0.05,
    )

    result = evaluate_research_validity(
        config=config,
        agent=agent,
        baselines={"baseline": _backtest(holdout_observations=30)},
        stress_tests={"neutral": _backtest(holdout_observations=30)},
        parameter_variants=[SimpleNamespace(name="h5_q20", backtest=_backtest(holdout_observations=30))],
        cost_variants=[SimpleNamespace(name="cost_2x", backtest=_backtest(holdout_observations=30))],
        data_integrity=_data_integrity(ready=True),
    )

    assert {(item.name, item.family) for item in result.candidates} == {
        ("agent_signal", "primary"),
        ("baseline", "baseline"),
        ("neutral", "stress_test"),
        ("h5_q20", "parameter_sensitivity"),
        ("cost_2x", "cost_sensitivity"),
    }
    assert all(0.0 <= item.q_value <= 1.0 for item in result.candidates)


def _check(name: str, passed: bool, required: bool = True) -> ValidityCheck:
    return ValidityCheck(
        name=name,
        required=required,
        passed=passed,
        observed=passed,
        threshold=True,
        reason=name,
    )


def _backtest(
    *,
    holdout_observations: int,
    holdout_sharpe: float = 0.8,
    holdout_ic_mean: float = 0.04,
    holdout_ic_tstat: float = 2.5,
    holdout_return: float = 0.04,
    walk_forward_sharpes: list[float] | None = None,
):
    windows = [
        SimpleNamespace(metrics={"sharpe": value})
        for value in (walk_forward_sharpes if walk_forward_sharpes is not None else [0.2, 0.3])
    ]
    return SimpleNamespace(
        split_date=pd.Timestamp("2024-01-31"),
        validation_start=pd.Timestamp("2024-02-01"),
        holdout_start=pd.Timestamp("2024-03-01"),
        metrics={
            "holdout": {
                "observations": float(holdout_observations),
                "sharpe": holdout_sharpe,
                "ic_mean": holdout_ic_mean,
                "ic_tstat": holdout_ic_tstat,
                "total_return": holdout_return,
            }
        },
        walk_forward=windows,
    )


def _config(
    *,
    fdr_alpha: float = 0.10,
    require_data_readiness: bool = False,
    require_baseline_outperformance: bool = False,
    require_walk_forward_stability: bool = False,
):
    raw = {
        "data": {
            "source": "synthetic",
            "universe": ["AAA", "BBB", "CCC", "DDD", "EEE"],
            "start": "2024-01-01",
            "end": "2024-06-30",
        },
        "experiment": {
            "name": "validity_test",
            "train_fraction": 0.5,
            "signal": {"positive_factors": ["momentum_20d"], "negative_factors": []},
            "backtest": {"holding_period": 5, "rebalance_days": 5, "quantile": 0.2},
            "validation": {
                "research_validity": {
                    "enabled": True,
                    "holdout_fraction": 0.2,
                    "fdr_alpha": fdr_alpha,
                    "require_positive_return": True,
                    "require_baseline_outperformance": require_baseline_outperformance,
                    "require_walk_forward_stability": require_walk_forward_stability,
                    "require_data_readiness": require_data_readiness,
                }
            },
            "baselines": [],
        },
        "report": {},
    }
    return parse_config(raw)


def _data_integrity(*, ready: bool) -> DataIntegrityReport:
    return DataIntegrityReport(
        source="synthetic",
        requested_symbols=["AAA"],
        observed_symbols=["AAA"],
        start="2024-01-01",
        end="2024-06-30",
        row_count=10,
        date_count=10,
        duplicate_index_rows=0,
        missing_symbols=[],
        point_in_time_universe=ready,
        survivorship_bias_free=ready,
        corporate_actions_adjusted=ready,
        provenance=None,
        quality_by_symbol=[],
        warnings=[],
    )
