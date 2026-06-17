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
        decision = _decision_summary(test)
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
                        "Full": full,
                    }
                ),
                "",
                "## Execution Costs",
                "",
                _execution_cost_table(result),
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
                _walk_forward_interpretation(result),
                "",
                "The train/test split is chronological. Test-period results are the primary evidence because they are less exposed to factor selection bias.",
                "",
                "## Limitations",
                "",
                "- Synthetic data is useful for deterministic validation but is not investment evidence.",
                "- Stress tests are diagnostics; the primary portfolio remains a simple long-short ranking portfolio.",
                "- Transaction costs and borrow costs are research approximations, not broker execution or securities-lending records.",
                "- No corporate actions or survivorship controls are included yet.",
                "",
                "## Next Experiments",
                "",
                "- Run the same signal on Yahoo Finance data for a real equity universe.",
                "- Replace redundant factors or orthogonalize correlated exposures before combining signals.",
                "- Add point-in-time vendor data integration with survivorship-safe universes.",
                "- Compare this factor against pure momentum, pure low volatility, and reversal baselines.",
                "",
            ]
        )


def write_experiment_row(result: ResearchRunResult, config: AppConfig) -> Path:
    path = config.report.experiments_path
    path.parent.mkdir(parents=True, exist_ok=True)
    rows = _experiment_rows_for_strategy(
        experiment=config.experiment.name,
        strategy="agent_signal",
        source=config.data.source,
        universe_size=len(result.universe.symbols),
        backtest=result.backtest,
    )
    for name, backtest in result.baselines.items():
        rows.extend(
            _experiment_rows_for_strategy(
                experiment=config.experiment.name,
                strategy=name,
                source=config.data.source,
                universe_size=len(result.universe.symbols),
                backtest=backtest,
            )
        )
    for name, backtest in result.stress_tests.items():
        rows.extend(
            _experiment_rows_for_strategy(
                experiment=config.experiment.name,
                strategy=name,
                source=config.data.source,
                universe_size=len(result.universe.symbols),
                backtest=backtest,
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
        "strategy",
        "window",
        "source",
        "universe_size",
        "train_start",
        "train_end",
        "test_start",
        "test_end",
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
    backtest: BacktestResult,
) -> list[dict[str, object]]:
    base = {
        "experiment": experiment,
        "strategy": strategy,
        "source": source,
        "universe_size": universe_size,
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
    return "\n".join(
        [
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
    )


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


def _decision_summary(metrics: dict[str, float]) -> str:
    if metrics["ic_mean"] > 0 and metrics["sharpe"] > 0:
        return (
            "The signal is a candidate for deeper research: out-of-sample IC and Sharpe are positive. "
            "The next question is whether the effect survives real data, costs, and neutralization."
        )
    if metrics["ic_mean"] > 0:
        return (
            "The signal shows positive out-of-sample rank correlation but weak portfolio conversion. "
            "Investigate turnover, concentration, and whether the long/short cutoffs are too aggressive."
        )
    return (
        "The signal is not supported out-of-sample in this run. Treat it as rejected until a more robust "
        "variant improves IC stability without increasing overfit risk."
    )


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
