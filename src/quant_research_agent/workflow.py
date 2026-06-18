from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from quant_research_agent.agents.evaluator_agent import ResearchRunResult, run_research_workflow
from quant_research_agent.agents.report_agent import ReportAgent, write_experiment_row
from quant_research_agent.agents.research_validity import research_validity_to_dict
from quant_research_agent.config import AppConfig, load_config
from quant_research_agent.experiment_registry import ExperimentRunRecord, record_run, record_to_dict
from quant_research_agent.locked_holdout import locked_holdout_to_dict
from quant_research_agent.reproducibility import (
    append_reproducibility_section,
    create_run_context,
    write_reproducibility_pack,
)


@dataclass(frozen=True)
class WorkflowRun:
    config: AppConfig
    result: ResearchRunResult
    report_path: Path
    experiments_path: Path
    manifest: dict[str, Any]
    registry_record: ExperimentRunRecord
    payload: dict[str, Any]


def run_configured_workflow(config_path: Path) -> WorkflowRun:
    config = load_config(config_path)
    run_context = create_run_context(config_path, config)
    result = run_research_workflow(config)
    report_path = ReportAgent().write_markdown_report(result, config)
    append_reproducibility_section(report_path, run_context)
    experiments_path = write_experiment_row(
        result,
        config,
        run_id=run_context.run_id,
        config_sha256=run_context.config_sha256,
    )
    manifest = write_reproducibility_pack(
        context=run_context,
        config=config,
        result=result,
        report_path=report_path,
        experiments_path=experiments_path,
    )
    registry_record = record_run(config.report.registry_path, manifest)
    payload = workflow_payload(
        config=config,
        result=result,
        report_path=report_path,
        experiments_path=experiments_path,
        manifest=manifest,
        registry_record=registry_record,
    )
    return WorkflowRun(
        config=config,
        result=result,
        report_path=report_path,
        experiments_path=experiments_path,
        manifest=manifest,
        registry_record=registry_record,
        payload=payload,
    )


def workflow_payload(
    config: AppConfig,
    result: ResearchRunResult,
    report_path: Path,
    experiments_path: Path,
    manifest: dict[str, Any],
    registry_record: ExperimentRunRecord,
) -> dict[str, Any]:
    research_validity = research_validity_to_dict(result.research_validity)
    research_validity["locked_holdout"] = locked_holdout_to_dict(result.locked_holdout)
    return {
        "run": _run_payload(manifest),
        "registry": {
            "path": str(config.report.registry_path),
            "record": record_to_dict(registry_record),
        },
        "experiment": config.experiment.name,
        "report_path": str(report_path),
        "experiments_path": str(experiments_path),
        "universe": _universe_payload(result),
        "data_integrity": _data_integrity_payload(result),
        "shorting": _shorting_payload(config),
        "borrow_availability": _borrow_availability_payload(result),
        "metrics": result.backtest.metrics,
        "baselines": {
            name: backtest.metrics for name, backtest in result.baselines.items()
        },
        "stress_tests": {
            name: backtest.metrics for name, backtest in result.stress_tests.items()
        },
        "walk_forward": {
            "agent_signal": _walk_forward_payload(result.backtest),
            **{
                name: _walk_forward_payload(backtest)
                for name, backtest in result.baselines.items()
            },
            **{
                name: _walk_forward_payload(backtest)
                for name, backtest in result.stress_tests.items()
            },
        },
        "factor_diagnostics": _factor_diagnostics_payload(result),
        "robustness": _robustness_payload(result),
        "capacity": _capacity_payload(result),
        "research_validity": research_validity,
        "locked_holdout": locked_holdout_to_dict(result.locked_holdout),
    }


def _run_payload(manifest: dict[str, Any]) -> dict[str, Any]:
    return {
        "run_id": manifest["run_id"],
        "generated_at": manifest["generated_at"],
        "manifest_path": manifest["artifacts"]["manifest_path"],
        "config_sha256": manifest["config"]["sha256"],
        "code": manifest["code"],
    }


def _walk_forward_payload(backtest) -> list[dict[str, Any]]:
    return [
        {
            "window": window.name,
            "train_start": window.train_start.date().isoformat(),
            "train_end": window.train_end.date().isoformat(),
            "test_start": window.test_start.date().isoformat(),
            "test_end": window.test_end.date().isoformat(),
            "metrics": window.metrics,
        }
        for window in backtest.walk_forward
    ]


def _factor_diagnostics_payload(result: ResearchRunResult) -> dict[str, Any]:
    diagnostics = result.factor_diagnostics
    return {
        "selected_factors": diagnostics.selected_factors,
        "correlation_threshold": diagnostics.correlation_threshold,
        "coverage": [
            {
                "factor": item.name,
                "observations": item.observations,
                "coverage": item.coverage,
                "missing_rate": item.missing_rate,
            }
            for item in diagnostics.coverage
        ],
        "redundant_pairs": [
            {
                "first": pair.first,
                "second": pair.second,
                "correlation": pair.correlation,
            }
            for pair in diagnostics.redundant_pairs
        ],
    }


def _data_integrity_payload(result: ResearchRunResult) -> dict[str, Any]:
    report = result.data_integrity
    return {
        "source": report.source,
        "requested_symbols": report.requested_symbols,
        "observed_symbols": report.observed_symbols,
        "start": report.start,
        "end": report.end,
        "row_count": report.row_count,
        "date_count": report.date_count,
        "duplicate_index_rows": report.duplicate_index_rows,
        "missing_symbols": report.missing_symbols,
        "point_in_time_universe": report.point_in_time_universe,
        "survivorship_bias_free": report.survivorship_bias_free,
        "corporate_actions_adjusted": report.corporate_actions_adjusted,
        "provenance": _provenance_payload(report.provenance),
        "quality_by_symbol": [
            {
                "symbol": item.symbol,
                "observations": item.observations,
                "expected_observations": item.expected_observations,
                "coverage": item.coverage,
                "missing_rows": item.missing_rows,
                "zero_volume_rows": item.zero_volume_rows,
                "non_positive_price_rows": item.non_positive_price_rows,
                "stale_price_rows": item.stale_price_rows,
                "extreme_return_rows": item.extreme_return_rows,
            }
            for item in report.quality_by_symbol
        ],
        "warnings": report.warnings,
    }


def _provenance_payload(provenance) -> dict[str, Any] | None:
    if provenance is None:
        return None
    return {
        "dataset_id": provenance.dataset_id,
        "vendor": provenance.vendor,
        "as_of": provenance.as_of,
        "created_at": provenance.created_at,
        "manifest_path": provenance.manifest_path,
        "data_path": provenance.data_path,
        "content_sha256": provenance.content_sha256,
        "expected_sha256": provenance.expected_sha256,
        "hash_matches": provenance.hash_matches,
        "row_count": provenance.row_count,
        "expected_row_count": provenance.expected_row_count,
        "row_count_matches": provenance.row_count_matches,
        "symbols": provenance.symbols,
        "expected_symbols": provenance.expected_symbols,
        "symbol_set_matches": provenance.symbol_set_matches,
        "start": provenance.start,
        "end": provenance.end,
        "expected_start": provenance.expected_start,
        "expected_end": provenance.expected_end,
        "date_range_matches": provenance.date_range_matches,
        "point_in_time_universe": provenance.point_in_time_universe,
        "survivorship_bias_free": provenance.survivorship_bias_free,
        "corporate_actions_adjusted": provenance.corporate_actions_adjusted,
        "warnings": provenance.warnings,
    }


def _universe_payload(result: ResearchRunResult) -> dict[str, Any]:
    return {
        "source": result.universe.source,
        "symbols": result.universe.symbols,
        "symbol_count": len(result.universe.symbols),
        "membership_rows": len(result.universe.membership),
        "point_in_time": result.universe.point_in_time,
        "survivorship_bias_free": result.universe.survivorship_bias_free,
        "warnings": result.universe.warnings,
    }


def _shorting_payload(config: AppConfig) -> dict[str, Any]:
    shortable = config.experiment.shorting.shortable_symbols
    return {
        "borrow_fee_bps": config.experiment.shorting.borrow_fee_bps,
        "shortable_symbols": shortable,
        "shortable_symbol_count": len(shortable) if shortable is not None else len(config.data.universe),
        "locate_history_path": str(config.experiment.shorting.locate_history_path)
        if config.experiment.shorting.locate_history_path is not None
        else None,
    }


def _borrow_availability_payload(result: ResearchRunResult) -> dict[str, Any] | None:
    if result.borrow_availability is None:
        return None
    summary = result.borrow_availability.summary
    return {
        "path": summary.path,
        "row_count": summary.row_count,
        "symbols": summary.symbols,
        "start": summary.start,
        "end": summary.end,
        "coverage": summary.coverage,
        "unavailable_rows": summary.unavailable_rows,
        "hard_to_borrow_rows": summary.hard_to_borrow_rows,
        "average_borrow_fee_bps": summary.average_borrow_fee_bps,
        "max_borrow_fee_bps": summary.max_borrow_fee_bps,
        "warnings": summary.warnings,
    }


def _robustness_payload(result: ResearchRunResult) -> dict[str, Any]:
    bootstrap = result.robustness.bootstrap
    return {
        "bootstrap": None
        if bootstrap is None
        else {
            "iterations": bootstrap.iterations,
            "seed": bootstrap.seed,
            "sharpe_mean": bootstrap.sharpe_mean,
            "sharpe_ci_low": bootstrap.sharpe_ci_low,
            "sharpe_ci_high": bootstrap.sharpe_ci_high,
            "ic_mean": bootstrap.ic_mean,
            "ic_ci_low": bootstrap.ic_ci_low,
            "ic_ci_high": bootstrap.ic_ci_high,
            "positive_sharpe_probability": bootstrap.positive_sharpe_probability,
            "positive_ic_probability": bootstrap.positive_ic_probability,
        },
        "parameter_sensitivity": [_sensitivity_payload(item) for item in result.robustness.parameter_sensitivity],
        "cost_sensitivity": [_sensitivity_payload(item) for item in result.robustness.cost_sensitivity],
    }


def _capacity_payload(result: ResearchRunResult) -> dict[str, Any]:
    concentration = result.capacity.concentration
    return {
        "concentration": {
            "max_single_name_weight": concentration.max_single_name_weight,
            "average_single_name_weight": concentration.average_single_name_weight,
            "average_effective_positions": concentration.average_effective_positions,
            "min_effective_positions": concentration.min_effective_positions,
            "average_gross_exposure": concentration.average_gross_exposure,
            "max_gross_exposure": concentration.max_gross_exposure,
            "position_weight_breach_count": concentration.position_weight_breach_count,
        },
        "capacity_curve": [
            {
                "notional": item.notional,
                "test_sharpe": item.test_sharpe,
                "test_total_return": item.test_total_return,
                "average_total_cost": item.average_total_cost,
                "average_impact_cost": item.average_impact_cost,
                "average_trade_participation": item.average_trade_participation,
                "max_trade_participation": item.max_trade_participation,
                "participation_breach_count": item.participation_breach_count,
                "passes_participation_limit": item.passes_participation_limit,
                "passes_positive_sharpe": item.passes_positive_sharpe,
            }
            for item in result.capacity.capacity_curve
        ],
        "max_capacity_notional": result.capacity.max_capacity_notional,
        "warnings": result.capacity.warnings,
    }


def _sensitivity_payload(item) -> dict[str, Any]:
    return {
        "name": item.name,
        "holding_period": item.holding_period,
        "quantile": item.quantile,
        "cost_multiplier": item.cost_multiplier,
        "metrics": item.metrics,
    }
