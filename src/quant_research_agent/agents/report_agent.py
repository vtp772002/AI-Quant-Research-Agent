from __future__ import annotations

from pathlib import Path

import pandas as pd

from quant_research_agent.agents.evaluator_agent import ResearchRunResult
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
                "## Baseline Comparison",
                "",
                _baseline_table(result),
                "",
                "## Interpretation",
                "",
                decision,
                "",
                _baseline_interpretation(result),
                "",
                "The train/test split is chronological. Test-period results are the primary evidence because they are less exposed to factor selection bias.",
                "",
                "## Limitations",
                "",
                "- Synthetic data is useful for deterministic validation but is not investment evidence.",
                "- v1 uses a simple long-short ranking portfolio without sector neutralization.",
                "- Transaction costs are modeled as proportional turnover costs only.",
                "- No borrow constraints, liquidity caps, corporate actions, or survivorship controls are included yet.",
                "",
                "## Next Experiments",
                "",
                "- Run the same signal on Yahoo Finance data for a real equity universe.",
                "- Add factor correlation and redundancy analysis before combining signals.",
                "- Add walk-forward validation over multiple expanding windows.",
                "- Compare this factor against pure momentum, pure low volatility, and reversal baselines.",
                "",
            ]
        )


def write_experiment_row(result: ResearchRunResult, config: AppConfig) -> Path:
    path = config.report.experiments_path
    path.parent.mkdir(parents=True, exist_ok=True)
    row = {
        "experiment": config.experiment.name,
        "strategy": "agent_signal",
        "source": config.data.source,
        "universe_size": len(config.data.universe),
        **{f"test_{key}": value for key, value in result.backtest.metrics["test"].items()},
        **{f"full_{key}": value for key, value in result.backtest.metrics["full"].items()},
    }
    rows = [row]
    for name, backtest in result.baselines.items():
        rows.append(
            {
                "experiment": config.experiment.name,
                "strategy": name,
                "source": config.data.source,
                "universe_size": len(config.data.universe),
                **{f"test_{key}": value for key, value in backtest.metrics["test"].items()},
                **{f"full_{key}": value for key, value in backtest.metrics["full"].items()},
            }
        )

    frame = pd.DataFrame(rows)
    if path.exists():
        existing = pd.read_csv(path)
        if "strategy" not in existing.columns:
            existing["strategy"] = "agent_signal"
        incoming_keys = set(zip(frame["experiment"], frame["source"], frame["strategy"]))
        existing = existing[
            ~existing.apply(
                lambda item: (item["experiment"], item["source"], item["strategy"]) in incoming_keys,
                axis=1,
            )
        ]
        frame = pd.concat([existing, frame], ignore_index=True)
    leading = ["experiment", "strategy", "source", "universe_size"]
    trailing = [column for column in frame.columns if column not in leading]
    frame = frame[leading + trailing]
    frame.to_csv(path, index=False)
    return path


def _metrics_table(sections: dict[str, dict[str, float]]) -> str:
    rows = ["| Split | IC Mean | Sharpe | Max Drawdown | Avg Turnover | Total Return |", "| --- | ---: | ---: | ---: | ---: | ---: |"]
    for name, metrics in sections.items():
        rows.append(
            "| {name} | {ic_mean:.4f} | {sharpe:.2f} | {max_drawdown:.2%} | {average_turnover:.2f} | {total_return:.2%} |".format(
                name=name,
                **metrics,
            )
        )
    return "\n".join(rows)


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
        "| Strategy | Test IC | Test Sharpe | Test Max Drawdown | Test Turnover | Test Total Return |",
        "| --- | ---: | ---: | ---: | ---: | ---: |",
    ]
    strategies = {"agent_signal": result.backtest, **result.baselines}
    for name, backtest in strategies.items():
        metrics = backtest.metrics["test"]
        rows.append(
            "| {name} | {ic_mean:.4f} | {sharpe:.2f} | {max_drawdown:.2%} | {average_turnover:.2f} | {total_return:.2%} |".format(
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
