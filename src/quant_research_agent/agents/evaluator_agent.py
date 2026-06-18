from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from quant_research_agent.agents.baseline_agent import BaselineAgent
from quant_research_agent.agents.capacity import CapacityDiagnostics, compute_capacity_diagnostics
from quant_research_agent.agents.factor_agent import FactorAgent
from quant_research_agent.agents.hypothesis_agent import Hypothesis, HypothesisAgent
from quant_research_agent.agents.robustness import RobustnessDiagnostics, compute_robustness_diagnostics
from quant_research_agent.agents.research_validity import (
    BacktestResultCandidate,
    ResearchValidityResult,
    evaluate_research_validity,
)
from quant_research_agent.agents.stress_tests import evaluate_stress_tests
from quant_research_agent.backtest.engine import BacktestResult, run_long_short_backtest
from quant_research_agent.config import AppConfig
from quant_research_agent.data.borrow import BorrowAvailability, load_borrow_availability
from quant_research_agent.data.integrity import DataIntegrityReport, assess_market_data_integrity
from quant_research_agent.data.loader import MarketDataRequest, load_market_data
from quant_research_agent.data.snapshot import load_snapshot_provenance
from quant_research_agent.data.universe import UniverseResolution, apply_universe_membership, resolve_universe
from quant_research_agent.factors.diagnostics import (
    FactorDiagnostics,
    compute_factor_diagnostics,
    selected_factor_names,
)
from quant_research_agent.factors.registry import compute_factor_library
from quant_research_agent.locked_holdout import LockedHoldoutEvidence, validate_locked_holdout


@dataclass(frozen=True)
class ResearchRunResult:
    hypothesis: Hypothesis
    universe: UniverseResolution
    market_data: pd.DataFrame
    borrow_availability: BorrowAvailability | None
    data_integrity: DataIntegrityReport
    factors: pd.DataFrame
    signal: pd.Series
    backtest: BacktestResult
    baselines: dict[str, BacktestResult]
    stress_tests: dict[str, BacktestResult]
    factor_diagnostics: FactorDiagnostics
    robustness: RobustnessDiagnostics
    capacity: CapacityDiagnostics
    research_validity: ResearchValidityResult
    locked_holdout: LockedHoldoutEvidence | None


def run_research_workflow(config: AppConfig) -> ResearchRunResult:
    hypothesis = HypothesisAgent().propose(config.experiment)
    universe = resolve_universe(
        static_universe=config.data.universe,
        start=config.data.start,
        end=config.data.end,
        provider_kind=config.data.universe_provider.kind,
        provider_path=config.data.universe_provider.path,
    )
    market_data = load_market_data(
        MarketDataRequest(
            source=config.data.source,
            universe=universe.symbols,
            start=config.data.start,
            end=config.data.end,
            seed=config.data.seed,
            snapshot_path=config.data.snapshot.path,
        )
    )
    market_data = apply_universe_membership(market_data, universe.membership)
    borrow_availability = load_borrow_availability(
        path=config.experiment.shorting.locate_history_path,
        symbols=universe.symbols,
        dates=market_data.index.get_level_values("date").unique(),
    )
    provenance = load_snapshot_provenance(
        manifest_path=config.data.snapshot.manifest_path,
        data_path=config.data.snapshot.path,
        data=market_data,
        require_hash=config.data.snapshot.require_manifest_hash,
    )
    data_integrity = assess_market_data_integrity(
        data=market_data,
        source=config.data.source,
        requested_symbols=universe.symbols,
        start=config.data.start,
        end=config.data.end,
        point_in_time_universe=config.data.point_in_time_universe or universe.point_in_time,
        survivorship_bias_free=config.data.survivorship_bias_free or universe.survivorship_bias_free,
        corporate_actions_adjusted=config.data.corporate_actions_adjusted,
        provenance=provenance,
    )
    factors = compute_factor_library(market_data)
    signal = FactorAgent().build_signal(factors, config.experiment.signal)
    backtest = run_long_short_backtest(
        market_data=market_data,
        signal=signal,
        train_fraction=config.experiment.train_fraction,
        holding_period=config.experiment.backtest.holding_period,
        rebalance_days=config.experiment.backtest.rebalance_days,
        quantile=config.experiment.backtest.quantile,
        transaction_cost_bps=config.experiment.backtest.transaction_cost_bps,
        holdout_fraction=(
            config.experiment.validation.research_validity.holdout_fraction
            if config.experiment.validation.research_validity.enabled
            else 0.0
        ),
        spread_cost_bps=config.experiment.backtest.spread_cost_bps,
        market_impact_coefficient=config.experiment.backtest.market_impact_coefficient,
        portfolio_notional=config.experiment.backtest.portfolio_notional,
        borrow_fee_bps=config.experiment.shorting.borrow_fee_bps,
        shortable_symbols=config.experiment.shorting.shortable_symbols,
        shortable_by_date=borrow_availability.shortable if borrow_availability is not None else None,
        borrow_fee_bps_by_date=borrow_availability.borrow_fee_bps if borrow_availability is not None else None,
        walk_forward_windows=config.experiment.validation.walk_forward.window_count,
        walk_forward_min_train_fraction=config.experiment.validation.walk_forward.min_train_fraction,
    )
    locked_holdout = validate_locked_holdout(
        config=config,
        market_data=market_data,
        backtest=backtest,
    )
    baselines = BaselineAgent().evaluate_baselines(
        market_data=market_data,
        factors=factors,
        config=config,
        reference_index=signal.index,
        borrow_availability=borrow_availability,
    )
    stress_tests = evaluate_stress_tests(
        market_data=market_data,
        factors=factors,
        signal=signal,
        config=config,
        borrow_availability=borrow_availability,
    )
    factor_diagnostics = compute_factor_diagnostics(
        factors=factors,
        selected_factors=selected_factor_names(config),
    )
    robustness = compute_robustness_diagnostics(
        market_data=market_data,
        signal=signal,
        backtest=backtest,
        config=config,
        borrow_availability=borrow_availability,
    )
    capacity = compute_capacity_diagnostics(
        market_data=market_data,
        signal=signal,
        backtest=backtest,
        config=config,
        borrow_availability=borrow_availability,
    )
    research_validity = evaluate_research_validity(
        config=config,
        agent=backtest,
        baselines=baselines,
        stress_tests=stress_tests,
        parameter_variants=[
            BacktestResultCandidate(item.name, item.backtest)
            for item in robustness.parameter_sensitivity
        ],
        cost_variants=[
            BacktestResultCandidate(item.name, item.backtest)
            for item in robustness.cost_sensitivity
        ],
        data_integrity=data_integrity,
    )
    return ResearchRunResult(
        hypothesis=hypothesis,
        universe=universe,
        market_data=market_data,
        borrow_availability=borrow_availability,
        data_integrity=data_integrity,
        factors=factors,
        signal=signal,
        backtest=backtest,
        baselines=baselines,
        stress_tests=stress_tests,
        factor_diagnostics=factor_diagnostics,
        robustness=robustness,
        capacity=capacity,
        research_validity=research_validity,
        locked_holdout=locked_holdout,
    )
