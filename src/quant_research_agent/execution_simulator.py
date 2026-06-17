from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import json

from quant_research_agent.config import AppConfig, load_config
from quant_research_agent.signals import SignalAsOfResult, generate_signal_as_of


@dataclass(frozen=True)
class SimulatedOrder:
    symbol: str
    side: str
    target_weight: float
    target_notional: float
    scheduled_notional: float
    estimated_participation: float
    status: str
    reason: str


@dataclass(frozen=True)
class ExecutionSimulation:
    experiment: str
    signal_date: str
    portfolio_notional: float
    max_participation: float
    orders: list[SimulatedOrder]
    warnings: list[str]


def simulate_execution_plan(
    config: AppConfig,
    signal: SignalAsOfResult,
    max_participation: float | None = None,
) -> ExecutionSimulation:
    participation_limit = max_participation or config.experiment.capacity.max_trade_participation
    if not 0.0 < participation_limit <= 1.0:
        raise ValueError("max_participation must be between 0 and 1")

    orders: list[SimulatedOrder] = []
    for row in signal.rows:
        if row.target_weight == 0.0:
            continue
        target_notional = row.target_weight * config.experiment.backtest.portfolio_notional
        estimated_participation = min(abs(row.target_weight), 1.0)
        passes = estimated_participation <= participation_limit
        orders.append(
            SimulatedOrder(
                symbol=row.symbol,
                side="buy" if target_notional > 0 else "sell_short",
                target_weight=row.target_weight,
                target_notional=target_notional,
                scheduled_notional=target_notional if passes else 0.0,
                estimated_participation=estimated_participation,
                status="scheduled" if passes else "blocked",
                reason="within participation limit" if passes else "participation limit breached",
            )
        )

    warnings: list[str] = []
    if any(order.status == "blocked" for order in orders):
        warnings.append("One or more orders were blocked by simulated participation limits.")
    warnings.append("Simulation does not route orders, contact brokers, reserve locates, or place trades.")
    return ExecutionSimulation(
        experiment=config.experiment.name,
        signal_date=signal.signal_date,
        portfolio_notional=config.experiment.backtest.portfolio_notional,
        max_participation=participation_limit,
        orders=orders,
        warnings=warnings,
    )


def run_execution_simulation(
    config_path: Path,
    as_of_date: str | None,
    output_path: Path | None = None,
    max_participation: float | None = None,
) -> ExecutionSimulation:
    config = load_config(config_path)
    signal = generate_signal_as_of(config, as_of_date=as_of_date or config.data.end, config_path=config_path)
    simulation = simulate_execution_plan(config, signal, max_participation=max_participation)
    if output_path is not None:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps(execution_simulation_to_dict(simulation), indent=2, sort_keys=True), encoding="utf-8")
    return simulation


def execution_simulation_to_dict(simulation: ExecutionSimulation) -> dict[str, object]:
    return {
        "experiment": simulation.experiment,
        "signal_date": simulation.signal_date,
        "portfolio_notional": simulation.portfolio_notional,
        "max_participation": simulation.max_participation,
        "orders": [order.__dict__ for order in simulation.orders],
        "warnings": simulation.warnings,
    }
