from __future__ import annotations

from dataclasses import dataclass

from quant_research_agent.config import ExperimentConfig


@dataclass(frozen=True)
class Hypothesis:
    statement: str
    required_features: list[str]
    expected_direction: str
    holding_period: int


class HypothesisAgent:
    """Deterministic v1 hypothesis agent.

    The LLM-facing seam is the Hypothesis object. In v1 we keep generation
    reproducible so every report can be validated without external API keys.
    """

    def propose(self, experiment: ExperimentConfig) -> Hypothesis:
        positive = ", ".join(experiment.signal.positive_factors)
        negative = ", ".join(experiment.signal.negative_factors)
        statement = (
            "Assets with stronger recent momentum and lower realized risk should "
            f"outperform over the next {experiment.backtest.holding_period} trading days."
        )
        return Hypothesis(
            statement=statement,
            required_features=experiment.signal.positive_factors + experiment.signal.negative_factors,
            expected_direction=f"positive exposure to [{positive}], negative exposure to [{negative}]",
            holding_period=experiment.backtest.holding_period,
        )
