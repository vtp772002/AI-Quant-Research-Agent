from __future__ import annotations

from pathlib import Path

import pandas as pd

from quant_research_agent.agents.evaluator_agent import ResearchRunResult
from quant_research_agent.backtest.engine import BacktestResult
from quant_research_agent.config import AppConfig


class ReportAgent:
    def write_markdown_report(self, result: ResearchRunResult, config: AppConfig) -> Path:
        output_path = config.report.output_path
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(self.render_markdown(result, config))
        return output_path

    def render_markdown(self, result: ResearchRunResult, config: AppConfig) -> str:
        full = result.backtest.metrics["full"]
        train = result.backtest.metrics["train"]
        test = result.backtest.metrics["test"]
        holdout = result.backtest.metrics["holdout"]
        decision = _decision_summary(result)
        actual_universe_size = result.market_data.index.get_level_values("symbol").nunique()

        return "\n".join(
            [
                "# AI Quant Research Report",
                "",
                f"## Experiment",
                "",
                f"- Name: `{config.experiment.name}`",
                f"- Universe: {actual_universe_size} assets from `{config.data.source}`",
                f"- Date range: {config.data.start} to {config.data.end}",
                f"- Holding period: {config.experiment.backtest.holding_period} trading days",
                f"- Rebalance: every {config.experiment.backtest.rebalance_days} trading days",
                f"- Long/short quantile: {config.experiment.backtest.quantile:.0%}",
                f"- Borrow fee: {config.experiment.shorting.borrow_fee_bps:.1f} bps annualized",
                f"- Shortable universe: {_shortable_summary(config)}",
                f"- Locate history: {_locate_history_summary(result)}",
                "",
                "## Data Integrity",
                "",
                _data_integrity_summary(result),
                "",
                _data_quality_table(result),
                "",
                _data_integrity_warnings(result),
                "",
                "## Hypothesis",
                "",
                result.hypothesis.statement,
                "",
                f"Expected direction: {result.hypothesis.expected_direction}.",
                "",
                "## Signal",
                "",
                f"Positive factors: {', '.join(config.experiment.signal.positive_factors)}",
                "",
                f"Negative factors: {', '.join(config.experiment.signal.negative_factors)}",
                "",
                "Signal is built from cross-sectional percentile ranks so each rebalance compares assets only against the active universe on that date.",
                "",
                "## Factor Diagnostics",
                "",
                _factor_coverage_table(result),
                "",
                _factor_redundancy_table(result),
                "",
                "## Results",
                "",
                _metrics_table(
                    {
                        "Train": train,
                        "Test": test,
                        "Holdout": holdout,
                        "Full": full,
                    }
                ),
                "",
                "## Execution Costs",
                "",
                _execution_cost_table(result),
                "",
                "## Borrow Availability",
                "",
                _borrow_availability_table(result),
                "",
                "## Capacity Diagnostics",
                "",
                _concentration_table(result),
                "",
                _capacity_curve_table(result),
                "",
                "## Robustness Diagnostics",
                "",
                _bootstrap_table(result),
                "",
                _sensitivity_table("Parameter Sensitivity", result.robustness.parameter_sensitivity),
                "",
                _sensitivity_table("Cost Sensitivity", result.robustness.cost_sensitivity),
                "",
                "## Baseline Comparison",
                "",
                _baseline_table(result),
                "",
                "## Stress Tests",
                "",
                _stress_test_table(result),
                "",
                "## Walk-Forward Validation",
                "",
                _walk_forward_agent_table(result.backtest),
                "",
                _walk_forward_strategy_table(result),
                "",
                "## Research Validity Gate",
                "",
                _research_validity_section(result),
                "",
                "## Interpretation",
                "",
                decision,
                "",
                _baseline_interpretation(result),
                "",
                _stress_test_interpretation(result),
                "",
                _factor_diagnostics_interpretation(result),
                "",
                _robustness_interpretation(result),
                "",
                _capacity_interpretation(result),
                "",
                _walk_forward_interpretation(result),
                "",
                "The train/validation/holdout split is chronological. Validation-period results remain compatibility `test` metrics; holdout-period results drive the research validity gate.",
                "",
                "## Limitations",
                "",
                "- Synthetic data is useful for deterministic validation but is not investment evidence.",
                "- Stress tests are diagnostics; the primary portfolio remains a simple long-short ranking portfolio.",
                "- Transaction costs and borrow costs are research approximations, not broker execution or securities-lending records.",
                "- Snapshot manifests validate reproducibility and provenance, but they are not a substitute for direct vendor entitlements or independent data audits.",
                "",
                "## Next Experiments",
                "",
                "- Run the same signal on Yahoo Finance data for a real equity universe.",
                "- Replace redundant factors or orthogonalize correlated exposures before combining signals.",
                "- Add direct vendor data integration that writes validated snapshot manifests.",
                "- Compare this factor against pure momentum, pure low volatility, and reversal baselines.",
                "",
            ]
        )


def write_experiment_row(
    result: ResearchRunResult,
    config: AppConfig,
    run_id: str = "",
    config_sha256: str = "",
) -> Path:
    path = config.report.experiments_path
    path.parent.mkdir(parents=True, exist_ok=True)
    validity_columns = _validity_summary_columns(result)
    rows = _experiment_rows_for_strategy(
        experiment=config.experiment.name,
        strategy="agent_signal",
        source=config.data.source,
        universe_size=len(result.universe.symbols),
        data_integrity=result.data_integrity,
        borrow_availability=result.borrow_availability,
        run_id=run_id,
        config_sha256=config_sha256,
        backtest=result.backtest,
        validity_columns=validity_columns,
    )
    for name, backtest in result.baselines.items():
        rows.extend(
            _experiment_rows_for_strategy(
                experiment=config.experiment.name,
                strategy=name,
                source=config.data.source,
                universe_size=len(result.universe.symbols),
                data_integrity=result.data_integrity,
                borrow_availability=result.borrow_availability,
                run_id=run_id,
                config_sha256=config_sha256,
                backtest=backtest,
                validity_columns=validity_columns,
            )
        )
    for name, backtest in result.stress_tests.items():
        rows.extend(
            _experiment_rows_for_strategy(
                experiment=config.experiment.name,
                strategy=name,
                source=config.data.source,
                universe_size=len(result.universe.symbols),
                data_integrity=result.data_integrity,
                borrow_availability=result.borrow_availability,
                run_id=run_id,
                config_sha256=config_sha256,
                backtest=backtest,
                validity_columns=validity_columns,
            )
        )

    frame = pd.DataFrame(rows)
    if path.exists():
        existing = pd.read_csv(path)
        if "strategy" not in existing.columns:
            existing["strategy"] = "agent_signal"
        if "window" not in existing.columns:
            existing["window"] = "full_sample"
        incoming_strategy_keys = set(zip(frame["experiment"], frame["source"], frame["strategy"]))
        existing = existing[
            ~existing.apply(
                lambda item: (item["experiment"], item["source"], item["strategy"]) in incoming_strategy_keys,
                axis=1,
            )
        ]
        frame = pd.concat([existing, frame], ignore_index=True)
    leading = [
        "experiment",
        "run_id",
        "config_sha256",
        "strategy",
        "window",
        "source",
        "dataset_id",
        "vendor",
        "as_of",
        "locate_history",
        "universe_size",
        "train_start",
        "train_end",
        "test_start",
        "test_end",
        "validity_verdict",
        "validity_enabled",
        "holdout_start",
        "holdout_sharpe",
        "holdout_ic_mean",
        "holdout_total_return",
        "agent_fdr_q_value",
    ]
    trailing = [column for column in frame.columns if column not in leading]
    frame = frame[leading + trailing]
    frame.to_csv(path, index=False)
    return path


def _experiment_rows_for_strategy(
    experiment: str,
    strategy: str,
    source: str,
    universe_size: int,
    data_integrity,
    borrow_availability,
    run_id: str,
    config_sha256: str,
    backtest: BacktestResult,
    validity_columns: dict[str, object],
) -> list[dict[str, object]]:
    provenance = data_integrity.provenance
    base = {
        "experiment": experiment,
        "run_id": run_id,
        "config_sha256": config_sha256,
        "strategy": strategy,
        "source": source,
        "dataset_id": provenance.dataset_id if provenance is not None else "",
        "vendor": provenance.vendor if provenance is not None else "",
        "as_of": provenance.as_of if provenance is not None else "",
        "locate_history": borrow_availability.summary.path if borrow_availability is not None else "",
        "universe_size": universe_size,
        **validity_columns,
    }
    rows: list[dict[str, object]] = [
        {
            **base,
            "window": "full_sample",
            "train_start": "",
            "train_end": "",
            "test_start": "",
            "test_end": "",
            **{f"test_{key}": value for key, value in backtest.metrics["test"].items()},
            **{f"full_{key}": value for key, value in backtest.metrics["full"].items()},
        }
    ]
    for window in backtest.walk_forward:
        rows.append(
            {
                **base,
                "window": window.name,
                "train_start": _date_text(window.train_start),
                "train_end": _date_text(window.train_end),
                "test_start": _date_text(window.test_start),
                "test_end": _date_text(window.test_end),
                **{f"test_{key}": value for key, value in window.metrics.items()},
            }
        )
    return rows


def _validity_summary_columns(result: ResearchRunResult) -> dict[str, object]:
    agent = next(
        candidate
        for candidate in result.research_validity.candidates
        if candidate.name == "agent_signal"
    )
    return {
        "validity_verdict": result.research_validity.verdict,
        "validity_enabled": result.research_validity.enabled,
        "holdout_start": result.research_validity.holdout_start or "",
        "holdout_sharpe": agent.holdout_sharpe,
        "holdout_ic_mean": agent.holdout_ic_mean,
        "holdout_total_return": agent.holdout_total_return,
        "agent_fdr_q_value": agent.q_value,
    }


def _metrics_table(sections: dict[str, dict[str, float]]) -> str:
    rows = [
        "| Split | IC Mean | Sharpe | Max Drawdown | Avg Turnover | Avg Cost | Total Return |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for name, metrics in sections.items():
        rows.append(
            "| {name} | {ic_mean:.4f} | {sharpe:.2f} | {max_drawdown:.2%} | {average_turnover:.2f} | {average_total_cost:.2%} | {total_return:.2%} |".format(
                name=name,
                **metrics,
            )
        )
    return "\n".join(rows)


def _execution_cost_table(result: ResearchRunResult) -> str:
    rows = [
        "| Component | Train | Test | Full |",
        "| --- | ---: | ---: | ---: |",
    ]
    labels = {
        "average_base_cost": "Avg base cost",
        "average_spread_cost": "Avg spread cost",
        "average_impact_cost": "Avg impact cost",
        "average_borrow_cost": "Avg borrow cost",
        "average_total_cost": "Avg total cost",
        "cumulative_total_cost": "Cumulative cost",
        "average_trade_participation": "Avg trade participation",
        "max_trade_participation": "Max trade participation",
    }
    for key, label in labels.items():
        rows.append(
            "| {label} | {train:.2%} | {test:.2%} | {full:.2%} |".format(
                label=label,
                train=result.backtest.metrics["train"][key],
                test=result.backtest.metrics["test"][key],
                full=result.backtest.metrics["full"][key],
            )
        )
    return "\n".join(rows)


def _borrow_availability_table(result: ResearchRunResult) -> str:
    if result.borrow_availability is None:
        return "No date-aware locate or borrow availability history was configured."

    summary = result.borrow_availability.summary
    rows = [
        "| Field | Value |",
        "| --- | ---: |",
        f"| Rows | {summary.row_count} |",
        f"| Symbols | {len(summary.symbols)} |",
        f"| Date range | {summary.start} to {summary.end} |",
        f"| Coverage | {summary.coverage:.2%} |",
        f"| Unavailable rows | {summary.unavailable_rows} |",
        f"| Hard-to-borrow rows | {summary.hard_to_borrow_rows} |",
        f"| Avg borrow fee | {summary.average_borrow_fee_bps:.1f} bps |",
        f"| Max borrow fee | {summary.max_borrow_fee_bps:.1f} bps |",
    ]
    if summary.warnings:
        rows.extend(["", "Warnings:"] + [f"- {warning}" for warning in summary.warnings])
    return "\n".join(rows)


def _concentration_table(result: ResearchRunResult) -> str:
    item = result.capacity.concentration
    return "\n".join(
        [
            "| Metric | Value |",
            "| --- | ---: |",
            f"| Max single-name weight | {item.max_single_name_weight:.2%} |",
            f"| Avg single-name max weight | {item.average_single_name_weight:.2%} |",
            f"| Avg effective positions | {item.average_effective_positions:.2f} |",
            f"| Min effective positions | {item.min_effective_positions:.2f} |",
            f"| Avg gross exposure | {item.average_gross_exposure:.2f}x |",
            f"| Max gross exposure | {item.max_gross_exposure:.2f}x |",
            f"| Position weight breaches | {item.position_weight_breach_count} |",
        ]
    )


def _capacity_curve_table(result: ResearchRunResult) -> str:
    if not result.capacity.capacity_curve:
        return "Capacity curve is not configured."

    rows = [
        "Capacity curve:",
        "",
        "| Notional | Test Sharpe | Test Return | Avg Cost | Avg Impact | Avg Participation | Max Participation | Breaches | Pass |",
        "| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |",
    ]
    for item in result.capacity.capacity_curve:
        passed = "yes" if item.passes_participation_limit and item.passes_positive_sharpe else "no"
        rows.append(
            "| {notional:,.0f} | {sharpe:.2f} | {total_return:.2%} | {avg_cost:.2%} | {impact:.2%} | {avg_part:.2%} | {max_part:.2%} | {breaches} | {passed} |".format(
                notional=item.notional,
                sharpe=item.test_sharpe,
                total_return=item.test_total_return,
                avg_cost=item.average_total_cost,
                impact=item.average_impact_cost,
                avg_part=item.average_trade_participation,
                max_part=item.max_trade_participation,
                breaches=item.participation_breach_count,
                passed=passed,
            )
        )
    if result.capacity.max_capacity_notional is not None:
        rows.extend(["", f"Estimated capacity: {result.capacity.max_capacity_notional:,.0f} notional under configured gates."])
    if result.capacity.warnings:
        rows.extend(["", "Warnings:"] + [f"- {warning}" for warning in result.capacity.warnings])
    return "\n".join(rows)


def _bootstrap_table(result: ResearchRunResult) -> str:
    bootstrap = result.robustness.bootstrap
    if bootstrap is None:
        return "Bootstrap robustness diagnostics are not configured or lack enough test observations."
    return "\n".join(
        [
            "| Metric | Mean | 2.5% | 97.5% | Positive Probability |",
            "| --- | ---: | ---: | ---: | ---: |",
            "| Test Sharpe | {mean:.2f} | {low:.2f} | {high:.2f} | {prob:.2%} |".format(
                mean=bootstrap.sharpe_mean,
                low=bootstrap.sharpe_ci_low,
                high=bootstrap.sharpe_ci_high,
                prob=bootstrap.positive_sharpe_probability,
            ),
            "| Test IC | {mean:.4f} | {low:.4f} | {high:.4f} | {prob:.2%} |".format(
                mean=bootstrap.ic_mean,
                low=bootstrap.ic_ci_low,
                high=bootstrap.ic_ci_high,
                prob=bootstrap.positive_ic_probability,
            ),
        ]
    )


def _sensitivity_table(title: str, rows_data) -> str:
    if not rows_data:
        return f"{title} is not configured."

    rows = [
        f"{title}:",
        "",
        "| Variant | Holding | Quantile | Cost Mult | Test IC | Test Sharpe | Test Cost | Test Return |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for item in rows_data:
        metrics = item.metrics
        rows.append(
            "| {name} | {holding} | {quantile:.0%} | {cost_multiplier:.2f} | {ic_mean:.4f} | {sharpe:.2f} | {average_total_cost:.2%} | {total_return:.2%} |".format(
                name=item.name,
                holding=item.holding_period,
                quantile=item.quantile,
                cost_multiplier=item.cost_multiplier,
                **metrics,
            )
        )
    return "\n".join(rows)


def _data_integrity_summary(result: ResearchRunResult) -> str:
    report = result.data_integrity
    rows = [
        f"- Source: `{report.source}`",
        f"- Universe source: `{result.universe.source}`",
        f"- Membership rows: {len(result.universe.membership)}",
        f"- Requested symbols: {len(report.requested_symbols)}",
        f"- Observed symbols: {len(report.observed_symbols)}",
        f"- Date rows: {report.date_count}",
        f"- Panel rows: {report.row_count}",
        f"- Point-in-time universe: {_yes_no(report.point_in_time_universe)}",
        f"- Survivorship-bias-free: {_yes_no(report.survivorship_bias_free)}",
        f"- Corporate actions institutional-grade: {_yes_no(report.corporate_actions_adjusted)}",
    ]
    if report.provenance is not None:
        rows.extend(_provenance_summary(report.provenance))
    return "\n".join(rows)


def _provenance_summary(provenance) -> list[str]:
    return [
        f"- Snapshot dataset: `{provenance.dataset_id}`",
        f"- Snapshot vendor: `{provenance.vendor}`",
        f"- Snapshot as-of: `{provenance.as_of}`",
        f"- Snapshot manifest: `{provenance.manifest_path}`",
        f"- Snapshot hash valid: {_yes_no(provenance.hash_matches)}",
        f"- Snapshot row count valid: {_yes_no(provenance.row_count_matches)}",
        f"- Snapshot symbol set valid: {_yes_no(provenance.symbol_set_matches)}",
        f"- Snapshot date range valid: {_yes_no(provenance.date_range_matches)}",
    ]


def _data_quality_table(result: ResearchRunResult) -> str:
    rows = [
        "| Symbol | Observations | Coverage | Missing Rows | Zero Volume | Bad Prices | Extreme Returns | Stale Prices |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for item in result.data_integrity.quality_by_symbol:
        rows.append(
            "| {symbol} | {observations} | {coverage:.2%} | {missing_rows} | {zero_volume_rows} | {non_positive_price_rows} | {extreme_return_rows} | {stale_price_rows} |".format(
                symbol=item.symbol,
                observations=item.observations,
                coverage=item.coverage,
                missing_rows=item.missing_rows,
                zero_volume_rows=item.zero_volume_rows,
                non_positive_price_rows=item.non_positive_price_rows,
                extreme_return_rows=item.extreme_return_rows,
                stale_price_rows=item.stale_price_rows,
            )
        )
    return "\n".join(rows)


def _data_integrity_warnings(result: ResearchRunResult) -> str:
    warnings = result.data_integrity.warnings
    if not warnings:
        return "No data integrity warnings were detected."
    return "\n".join(["Warnings:"] + [f"- {warning}" for warning in warnings])


def _research_validity_section(result: ResearchRunResult) -> str:
    validity = result.research_validity
    candidate_rows = [
        "| Candidate | Family | Holdout Obs | Holdout IC | Holdout Sharpe | Holdout Return | p-value | FDR q-value |",
        "| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for candidate in validity.candidates:
        candidate_rows.append(
            "| {name} | {family} | {observations} | {ic:.4f} | {sharpe:.2f} | {total_return:.2%} | {p_value:.4f} | {q_value:.4f} |".format(
                name=candidate.name,
                family=candidate.family,
                observations=candidate.holdout_observations,
                ic=candidate.holdout_ic_mean,
                sharpe=candidate.holdout_sharpe,
                total_return=candidate.holdout_total_return,
                p_value=candidate.p_value,
                q_value=candidate.q_value,
            )
        )

    check_rows = [
        "| Check | Required | Status | Observed | Threshold | Reason |",
        "| --- | --- | --- | ---: | --- | --- |",
    ]
    for check in validity.checks:
        check_rows.append(
            "| {name} | {required} | {status} | {observed} | {threshold} | {reason} |".format(
                name=check.name,
                required=_yes_no(check.required),
                status=_check_status(check.passed),
                observed=_format_check_value(check.observed),
                threshold=_format_check_value(check.threshold),
                reason=check.reason,
            )
        )

    reasons = (
        "No required validity checks failed."
        if not validity.reasons
        else "\n".join(["Reasons preventing promotion:"] + [f"- {reason}" for reason in validity.reasons])
    )
    return "\n".join(
        [
            f"Verdict: `{validity.verdict}`",
            f"Gate enabled: {_yes_no(validity.enabled)}",
            f"Train ends: `{validity.train_end}`",
            f"Validation starts: `{validity.validation_start}`",
            f"Holdout starts: `{validity.holdout_start or 'not configured'}`",
            f"FDR alpha: {validity.fdr_alpha:.2f}",
            "",
            "\n".join(candidate_rows),
            "",
            "\n".join(check_rows),
            "",
            reasons,
        ]
    )


def _decision_summary(result: ResearchRunResult) -> str:
    validity = result.research_validity
    metrics = result.backtest.metrics["test"]
    if validity.verdict == "PROMOTE":
        return (
            "The run-level research validity gate promotes this signal for the next research stage. "
            "Promotion is still not investment approval or final family-level approval; it means the configured holdout, FDR, "
            "baseline, stability, and data checks passed for this run."
        )
    if validity.verdict == "REVIEW":
        return (
            "The run-level research validity gate requires human review before this signal can advance. "
            "Core evidence may be acceptable, but at least one comparative, stability, or data-readiness requirement needs inspection."
        )
    if metrics["ic_mean"] > 0 and metrics["sharpe"] > 0:
        return (
            "The run-level research validity gate rejects promotion even though validation IC and Sharpe are positive. "
            "Use the failed holdout or FDR checks as the next iteration target."
        )
    if metrics["ic_mean"] > 0:
        return (
            "The run-level research validity gate rejects promotion. The signal shows positive validation rank correlation but weak portfolio conversion. "
            "Investigate turnover, concentration, and whether the long/short cutoffs are too aggressive."
        )
    return (
        "The run-level research validity gate rejects promotion. The signal is not supported in validation in this run. Treat it as rejected until a more robust "
        "variant improves IC stability without increasing overfit risk."
    )


def _check_status(value: bool | None) -> str:
    if value is True:
        return "pass"
    if value is False:
        return "fail"
    return "not_applicable"


def _format_check_value(value) -> str:
    if isinstance(value, bool):
        return _yes_no(value)
    if isinstance(value, float):
        return f"{value:.4f}"
    if value is None:
        return "not_applicable"
    return str(value)


def _baseline_table(result: ResearchRunResult) -> str:
    rows = [
        "| Strategy | Test IC | Test Sharpe | Test Max Drawdown | Test Turnover | Test Cost | Test Total Return |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    strategies = {"agent_signal": result.backtest, **result.baselines}
    for name, backtest in strategies.items():
        metrics = backtest.metrics["test"]
        rows.append(
            "| {name} | {ic_mean:.4f} | {sharpe:.2f} | {max_drawdown:.2%} | {average_turnover:.2f} | {average_total_cost:.2%} | {total_return:.2%} |".format(
                name=name,
                **metrics,
            )
        )
    return "\n".join(rows)


def _stress_test_table(result: ResearchRunResult) -> str:
    if not result.stress_tests:
        return "No neutralization or liquidity stress tests were configured for this run."

    rows = [
        "| Stress Test | Test IC | Test Sharpe | Test Max Drawdown | Test Turnover | Test Cost | Test Total Return |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for name, backtest in result.stress_tests.items():
        metrics = backtest.metrics["test"]
        rows.append(
            "| {name} | {ic_mean:.4f} | {sharpe:.2f} | {max_drawdown:.2%} | {average_turnover:.2f} | {average_total_cost:.2%} | {total_return:.2%} |".format(
                name=name,
                **metrics,
            )
        )
    return "\n".join(rows)


def _baseline_interpretation(result: ResearchRunResult) -> str:
    if not result.baselines:
        return "No baseline strategies were configured for this run."

    agent_sharpe = result.backtest.metrics["test"]["sharpe"]
    agent_ic = result.backtest.metrics["test"]["ic_mean"]
    best_name = "agent_signal"
    best_sharpe = agent_sharpe
    for name, backtest in result.baselines.items():
        sharpe = backtest.metrics["test"]["sharpe"]
        if sharpe > best_sharpe:
            best_name = name
            best_sharpe = sharpe

    if best_name == "agent_signal":
        return (
            "The agent signal has the strongest out-of-sample Sharpe among configured strategies. "
            f"Its test IC is {agent_ic:.4f}, so the next validation target is stability across real data and walk-forward windows."
        )
    return (
        f"The strongest out-of-sample Sharpe is from `{best_name}`, not the agent signal. "
        "Treat this as a useful rejection/iteration signal: inspect which factor exposure is carrying the result before adding model complexity."
    )


def _stress_test_interpretation(result: ResearchRunResult) -> str:
    if not result.stress_tests:
        return "No stress-test variants were configured for neutralization or liquidity constraints."

    agent_sharpe = result.backtest.metrics["test"]["sharpe"]
    agent_ic = result.backtest.metrics["test"]["ic_mean"]
    passing = [
        name
        for name, backtest in result.stress_tests.items()
        if backtest.metrics["test"]["ic_mean"] > 0 and backtest.metrics["test"]["sharpe"] > 0
    ]
    if passing:
        return (
            "The signal keeps positive test IC and Sharpe under these stress tests: "
            f"{', '.join(passing)}. Compare their drawdowns and turnover before treating this as robust."
        )
    return (
        "The stress-test variants did not preserve both positive IC and positive Sharpe. "
        f"The base agent test IC is {agent_ic:.4f} and Sharpe is {agent_sharpe:.2f}; investigate sector or liquidity dependence."
    )


def _factor_coverage_table(result: ResearchRunResult) -> str:
    diagnostics = result.factor_diagnostics
    if not diagnostics.coverage:
        return "No configured factor exposures were available for diagnostics."

    rows = [
        "| Factor | Observations | Coverage | Missing Rate |",
        "| --- | ---: | ---: | ---: |",
    ]
    for item in diagnostics.coverage:
        rows.append(
            "| {name} | {observations} | {coverage:.2%} | {missing_rate:.2%} |".format(
                name=item.name,
                observations=item.observations,
                coverage=item.coverage,
                missing_rate=item.missing_rate,
            )
        )
    return "\n".join(rows)


def _factor_redundancy_table(result: ResearchRunResult) -> str:
    diagnostics = result.factor_diagnostics
    if not diagnostics.redundant_pairs:
        return f"No selected factor pairs exceeded absolute Spearman correlation of {diagnostics.correlation_threshold:.2f}."

    rows = [
        f"Pairs above absolute Spearman correlation of {diagnostics.correlation_threshold:.2f}:",
        "",
        "| Factor A | Factor B | Spearman Corr |",
        "| --- | --- | ---: |",
    ]
    for pair in diagnostics.redundant_pairs:
        rows.append(f"| {pair.first} | {pair.second} | {pair.correlation:.4f} |")
    return "\n".join(rows)


def _factor_diagnostics_interpretation(result: ResearchRunResult) -> str:
    diagnostics = result.factor_diagnostics
    if not diagnostics.redundant_pairs:
        return "Factor diagnostics did not flag high pairwise redundancy among selected exposures."

    strongest = diagnostics.redundant_pairs[0]
    return (
        "Factor diagnostics flagged potentially redundant exposures. "
        f"The strongest pair is `{strongest.first}` and `{strongest.second}` "
        f"with Spearman correlation {strongest.correlation:.4f}; simplify or orthogonalize before adding more factors."
    )


def _robustness_interpretation(result: ResearchRunResult) -> str:
    bootstrap = result.robustness.bootstrap
    weak_points = []
    if bootstrap is not None:
        if bootstrap.positive_sharpe_probability < 0.6:
            weak_points.append("bootstrap Sharpe confidence is weak")
        if bootstrap.positive_ic_probability < 0.6:
            weak_points.append("bootstrap IC confidence is weak")
    if result.robustness.parameter_sensitivity:
        positive_sharpe = sum(item.metrics["sharpe"] > 0 for item in result.robustness.parameter_sensitivity)
        if positive_sharpe / len(result.robustness.parameter_sensitivity) < 0.5:
            weak_points.append("parameter sensitivity is fragile")
    if result.robustness.cost_sensitivity:
        high_cost = result.robustness.cost_sensitivity[-1]
        if high_cost.metrics["sharpe"] <= 0:
            weak_points.append("high-cost sensitivity erases positive Sharpe")

    if not weak_points:
        return "Robustness diagnostics do not flag a major overfit warning under the configured bootstrap and sensitivity checks."
    return "Robustness diagnostics flag caution: " + "; ".join(weak_points) + "."


def _capacity_interpretation(result: ResearchRunResult) -> str:
    if not result.capacity.capacity_curve:
        return "Capacity diagnostics were limited to concentration because no notional curve was configured."
    if result.capacity.max_capacity_notional is None:
        return "Capacity diagnostics do not identify a configured notional that passes both participation and positive-Sharpe gates."
    return (
        "Capacity diagnostics estimate that the signal passes configured gates up to "
        f"{result.capacity.max_capacity_notional:,.0f} notional. "
        "Treat this as a research approximation because the model uses average dollar volume, not live order book depth."
    )


def _walk_forward_agent_table(backtest: BacktestResult) -> str:
    if not backtest.walk_forward:
        return "Walk-forward validation is not configured for this experiment."

    rows = [
        "| Window | Train Through | Test Range | Obs | IC Mean | Sharpe | Avg Cost | Hit Rate | Total Return |",
        "| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for window in backtest.walk_forward:
        metrics = window.metrics
        rows.append(
            "| {name} | {train_end} | {test_start} to {test_end} | {observations:.0f} | {ic_mean:.4f} | {sharpe:.2f} | {average_total_cost:.2%} | {ic_hit_rate:.2%} | {total_return:.2%} |".format(
                name=window.name,
                train_end=_date_text(window.train_end),
                test_start=_date_text(window.test_start),
                test_end=_date_text(window.test_end),
                **metrics,
            )
        )
    return "\n".join(rows)


def _walk_forward_strategy_table(result: ResearchRunResult) -> str:
    strategies = {"agent_signal": result.backtest, **result.baselines, **result.stress_tests}
    if not any(backtest.walk_forward for backtest in strategies.values()):
        return ""

    rows = [
        "| Strategy | Windows | Mean Test IC | Mean Sharpe | Mean Cost | Positive IC Windows | Median Total Return |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for name, backtest in strategies.items():
        windows = backtest.walk_forward
        if not windows:
            continue
        ic_values = pd.Series([window.metrics["ic_mean"] for window in windows])
        sharpe_values = pd.Series([window.metrics["sharpe"] for window in windows])
        cost_values = pd.Series([window.metrics["average_total_cost"] for window in windows])
        total_returns = pd.Series([window.metrics["total_return"] for window in windows])
        rows.append(
            "| {name} | {count} | {mean_ic:.4f} | {mean_sharpe:.2f} | {mean_cost:.2%} | {positive_ic:.2%} | {median_return:.2%} |".format(
                name=name,
                count=len(windows),
                mean_ic=float(ic_values.mean()),
                mean_sharpe=float(sharpe_values.mean()),
                mean_cost=float(cost_values.mean()),
                positive_ic=float((ic_values > 0).mean()),
                median_return=float(total_returns.median()),
            )
        )
    return "\n".join(rows)


def _walk_forward_interpretation(result: ResearchRunResult) -> str:
    windows = result.backtest.walk_forward
    if not windows:
        return "Walk-forward validation was skipped because it is not configured."

    positive_ic_rate = sum(window.metrics["ic_mean"] > 0 for window in windows) / len(windows)
    mean_sharpe = sum(window.metrics["sharpe"] for window in windows) / len(windows)
    if positive_ic_rate >= 0.67 and mean_sharpe > 0:
        return (
            "Walk-forward validation supports further research: most agent-signal windows have positive IC "
            "and the average window Sharpe is positive."
        )
    return (
        "Walk-forward validation is not yet stable enough for promotion: inspect the weak windows before adding factor complexity."
    )


def _date_text(value: pd.Timestamp) -> str:
    return pd.Timestamp(value).date().isoformat()


def _yes_no(value: bool) -> str:
    return "yes" if value else "no"


def _shortable_summary(config: AppConfig) -> str:
    shortable = config.experiment.shorting.shortable_symbols
    if shortable is None:
        return "all configured symbols"
    return f"{len(shortable)} configured symbols"


def _locate_history_summary(result: ResearchRunResult) -> str:
    if result.borrow_availability is None:
        return "not configured"
    return f"`{result.borrow_availability.summary.path}`"
