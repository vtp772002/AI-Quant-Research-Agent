from __future__ import annotations

from dataclasses import dataclass, replace
from math import erfc, isfinite, sqrt
from typing import Any

from quant_research_agent.backtest.engine import BacktestResult
from quant_research_agent.config import AppConfig
from quant_research_agent.data.integrity import DataIntegrityReport


@dataclass(frozen=True)
class CandidateEvidence:
    name: str
    family: str
    holdout_observations: int
    holdout_sharpe: float
    holdout_ic_mean: float
    holdout_ic_tstat: float
    holdout_total_return: float
    p_value: float
    q_value: float


@dataclass(frozen=True)
class ValidityCheck:
    name: str
    required: bool
    passed: bool | None
    observed: float | bool | str | None
    threshold: float | bool | str | None
    reason: str


@dataclass(frozen=True)
class ResearchValidityResult:
    enabled: bool
    verdict: str
    train_end: str
    validation_start: str
    holdout_start: str | None
    fdr_alpha: float
    candidates: list[CandidateEvidence]
    checks: list[ValidityCheck]
    reasons: list[str]


@dataclass(frozen=True)
class BacktestResultCandidate:
    name: str
    backtest: BacktestResult


def one_sided_positive_pvalue(tstat: float) -> float:
    if not isfinite(tstat):
        return 1.0
    return float(0.5 * erfc(tstat / sqrt(2.0)))


def adjust_pvalues_benjamini_hochberg(pvalues: dict[str, float]) -> dict[str, float]:
    if not pvalues:
        return {}
    ordered = sorted(pvalues.items(), key=lambda item: (item[1], item[0]))
    count = len(ordered)
    adjusted_sorted = [1.0] * count
    running = 1.0
    for reverse_index in range(count - 1, -1, -1):
        _, pvalue = ordered[reverse_index]
        rank = reverse_index + 1
        running = min(running, min(1.0, float(pvalue) * count / rank))
        adjusted_sorted[reverse_index] = running
    return {
        name: adjusted_sorted[index]
        for index, (name, _) in enumerate(ordered)
    }


def build_candidate_evidence(name: str, family: str, backtest: BacktestResult) -> CandidateEvidence:
    metrics = backtest.metrics["holdout"]
    observations = int(metrics.get("observations", 0.0))
    ic_tstat = float(metrics.get("ic_tstat", 0.0))
    p_value = 1.0 if observations < 2 else one_sided_positive_pvalue(ic_tstat)
    return CandidateEvidence(
        name=name,
        family=family,
        holdout_observations=observations,
        holdout_sharpe=float(metrics.get("sharpe", 0.0)),
        holdout_ic_mean=float(metrics.get("ic_mean", 0.0)),
        holdout_ic_tstat=ic_tstat,
        holdout_total_return=float(metrics.get("total_return", 0.0)),
        p_value=p_value,
        q_value=1.0,
    )


def evaluate_research_validity(
    *,
    config: AppConfig,
    agent: BacktestResult,
    baselines: dict[str, BacktestResult],
    stress_tests: dict[str, BacktestResult],
    parameter_variants: list[BacktestResultCandidate],
    cost_variants: list[BacktestResultCandidate],
    data_integrity: DataIntegrityReport,
) -> ResearchValidityResult:
    validity = config.experiment.validation.research_validity
    candidates = [
        build_candidate_evidence("agent_signal", "primary", agent),
        *[
            build_candidate_evidence(name, "baseline", backtest)
            for name, backtest in sorted(baselines.items())
        ],
        *[
            build_candidate_evidence(name, "stress_test", backtest)
            for name, backtest in sorted(stress_tests.items())
        ],
        *[
            build_candidate_evidence(item.name, "parameter_sensitivity", item.backtest)
            for item in parameter_variants
        ],
        *[
            build_candidate_evidence(item.name, "cost_sensitivity", item.backtest)
            for item in cost_variants
        ],
    ]
    q_values = adjust_pvalues_benjamini_hochberg(
        {candidate.name: candidate.p_value for candidate in candidates}
    )
    adjusted_candidates = [
        replace(candidate, q_value=float(q_values[candidate.name]))
        for candidate in candidates
    ]
    checks = build_validity_checks(
        config=config,
        agent_evidence=adjusted_candidates[0],
        baselines=baselines,
        agent=agent,
        data_integrity=data_integrity,
    )
    verdict = select_validity_verdict(enabled=validity.enabled, checks=checks)
    reasons = [
        check.reason
        for check in checks
        if check.required and check.passed is False
    ]
    return ResearchValidityResult(
        enabled=validity.enabled,
        verdict=verdict,
        train_end=agent.split_date.date().isoformat(),
        validation_start=agent.validation_start.date().isoformat(),
        holdout_start=agent.holdout_start.date().isoformat() if agent.holdout_start is not None else None,
        fdr_alpha=validity.fdr_alpha,
        candidates=adjusted_candidates,
        checks=checks,
        reasons=reasons,
    )


def build_validity_checks(
    *,
    config: AppConfig,
    agent_evidence: CandidateEvidence,
    baselines: dict[str, BacktestResult],
    agent: BacktestResult,
    data_integrity: DataIntegrityReport,
) -> list[ValidityCheck]:
    validity = config.experiment.validation.research_validity
    checks = [
        _threshold_check(
            name="positive_holdout_sharpe",
            observed=agent_evidence.holdout_sharpe,
            threshold=validity.min_holdout_sharpe,
            passed=agent_evidence.holdout_sharpe > validity.min_holdout_sharpe,
            reason=(
                f"Holdout Sharpe {agent_evidence.holdout_sharpe:.4f} must be greater than "
                f"{validity.min_holdout_sharpe:.4f}."
            ),
        ),
        _threshold_check(
            name="positive_holdout_ic",
            observed=agent_evidence.holdout_ic_mean,
            threshold=validity.min_holdout_ic,
            passed=agent_evidence.holdout_ic_mean > validity.min_holdout_ic,
            reason=(
                f"Holdout IC {agent_evidence.holdout_ic_mean:.4f} must be greater than "
                f"{validity.min_holdout_ic:.4f}."
            ),
        ),
        _threshold_check(
            name="fdr_significant",
            observed=agent_evidence.q_value,
            threshold=validity.fdr_alpha,
            passed=agent_evidence.q_value <= validity.fdr_alpha,
            reason=(
                f"Agent FDR q-value {agent_evidence.q_value:.4f} must be at most "
                f"{validity.fdr_alpha:.4f}."
            ),
        ),
        _optional_check(
            name="positive_holdout_return",
            required=validity.require_positive_return,
            observed=agent_evidence.holdout_total_return,
            threshold=0.0,
            passed=agent_evidence.holdout_total_return > 0.0,
            reason=f"Holdout total return {agent_evidence.holdout_total_return:.4f} must be positive.",
        ),
        _baseline_check(
            required=validity.require_baseline_outperformance,
            agent_sharpe=agent_evidence.holdout_sharpe,
            baselines=baselines,
        ),
        _walk_forward_check(
            required=validity.require_walk_forward_stability,
            agent=agent,
        ),
        _data_ready_check(
            required=validity.require_data_readiness,
            data_integrity=data_integrity,
        ),
    ]
    return checks


def select_validity_verdict(enabled: bool, checks: list[ValidityCheck]) -> str:
    if not enabled:
        return "REVIEW"
    core_names = {
        "positive_holdout_sharpe",
        "positive_holdout_ic",
        "fdr_significant",
        "positive_holdout_return",
    }
    failed_required = {
        check.name
        for check in checks
        if check.required and check.passed is False
    }
    if failed_required & core_names:
        return "REJECT"
    if failed_required:
        return "REVIEW"
    return "PROMOTE"


def research_validity_to_dict(result: ResearchValidityResult) -> dict[str, Any]:
    return {
        "enabled": result.enabled,
        "verdict": result.verdict,
        "train_end": result.train_end,
        "validation_start": result.validation_start,
        "holdout_start": result.holdout_start,
        "fdr_alpha": result.fdr_alpha,
        "candidates": [candidate.__dict__ for candidate in result.candidates],
        "checks": [check.__dict__ for check in result.checks],
        "reasons": result.reasons,
    }


def _threshold_check(
    *,
    name: str,
    observed: float,
    threshold: float,
    passed: bool,
    reason: str,
) -> ValidityCheck:
    return ValidityCheck(
        name=name,
        required=True,
        passed=passed,
        observed=observed,
        threshold=threshold,
        reason=reason,
    )


def _optional_check(
    *,
    name: str,
    required: bool,
    observed: float,
    threshold: float,
    passed: bool,
    reason: str,
) -> ValidityCheck:
    return ValidityCheck(
        name=name,
        required=required,
        passed=passed if required else None,
        observed=observed,
        threshold=threshold,
        reason=reason,
    )


def _baseline_check(
    *,
    required: bool,
    agent_sharpe: float,
    baselines: dict[str, BacktestResult],
) -> ValidityCheck:
    if not baselines:
        return ValidityCheck(
            name="beats_best_baseline",
            required=False,
            passed=None,
            observed="not_applicable",
            threshold="baseline required",
            reason="No configured baselines are available for holdout comparison.",
        )
    best = max(backtest.metrics["holdout"]["sharpe"] for backtest in baselines.values())
    return ValidityCheck(
        name="beats_best_baseline",
        required=required,
        passed=(agent_sharpe >= best) if required else None,
        observed=agent_sharpe,
        threshold=float(best),
        reason=f"Agent holdout Sharpe {agent_sharpe:.4f} must be at least best baseline {best:.4f}.",
    )


def _walk_forward_check(*, required: bool, agent: BacktestResult) -> ValidityCheck:
    if not agent.walk_forward:
        passed = False
        observed: float | str = "no_windows"
    else:
        positive = sum(window.metrics["sharpe"] >= 0.0 for window in agent.walk_forward)
        observed = positive / len(agent.walk_forward)
        passed = observed >= 0.5
    return ValidityCheck(
        name="walk_forward_stable",
        required=required,
        passed=passed if required else None,
        observed=observed,
        threshold=">= 50% non-negative Sharpe windows",
        reason="At least half of walk-forward windows must have non-negative Sharpe.",
    )


def _data_ready_check(*, required: bool, data_integrity: DataIntegrityReport) -> ValidityCheck:
    ready = (
        data_integrity.point_in_time_universe
        and data_integrity.survivorship_bias_free
        and data_integrity.corporate_actions_adjusted
    )
    return ValidityCheck(
        name="data_ready",
        required=required,
        passed=ready if required else None,
        observed=ready,
        threshold=True,
        reason=(
            "Data must be point-in-time, survivorship-bias-free, and corporate-action adjusted."
        ),
    )
