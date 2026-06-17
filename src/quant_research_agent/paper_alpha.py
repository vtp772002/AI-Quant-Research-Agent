from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re

import yaml


FACTOR_KEYWORDS = {
    "momentum_20d": ["momentum", "trend", "relative strength"],
    "momentum_60d": ["medium-term momentum", "sixty day", "60-day"],
    "reversal_5d": ["reversal", "mean reversion", "short-term reversal"],
    "volatility_20d": ["volatility", "low risk", "realized risk"],
    "drawdown_20d": ["drawdown", "downside"],
    "dollar_volume_20d": ["liquidity", "volume", "turnover"],
}


@dataclass(frozen=True)
class AlphaTemplate:
    name: str
    hypothesis: str
    positive_factors: list[str]
    negative_factors: list[str]
    holding_period: int
    warnings: list[str]


def extract_alpha_template(text: str, name: str = "paper_alpha_template") -> AlphaTemplate:
    cleaned = _clean_text(text)
    lowered = cleaned.lower()
    positive: list[str] = []
    negative: list[str] = []
    for factor, keywords in FACTOR_KEYWORDS.items():
        if any(keyword in lowered for keyword in keywords):
            if factor in {"volatility_20d", "drawdown_20d"} and ("low" in lowered or "risk" in lowered):
                negative.append(factor)
            else:
                positive.append(factor)

    if not positive:
        positive = ["momentum_20d"]
    if not negative and ("risk" in lowered or "volatility" in lowered):
        negative = ["volatility_20d"]

    holding_period = _holding_period(lowered)
    warnings: list[str] = [
        "Template was extracted heuristically; review factor direction and holding period before running research."
    ]
    if len(cleaned) < 200:
        warnings.append("Input paper text is short; extraction confidence is limited.")

    return AlphaTemplate(
        name=_slug(name),
        hypothesis=_hypothesis(cleaned, positive, negative, holding_period),
        positive_factors=sorted(set(positive)),
        negative_factors=sorted(set(negative)),
        holding_period=holding_period,
        warnings=warnings,
    )


def template_to_config(template: AlphaTemplate) -> dict[str, object]:
    return {
        "experiment": {
            "name": template.name,
            "hypothesis": template.hypothesis,
            "signal": {
                "positive_factors": template.positive_factors,
                "negative_factors": template.negative_factors,
            },
            "backtest": {
                "holding_period": template.holding_period,
                "rebalance_days": template.holding_period,
                "quantile": 0.2,
            },
        },
        "warnings": template.warnings,
    }


def write_alpha_template(input_path: Path, output_path: Path, name: str | None = None) -> AlphaTemplate:
    template = extract_alpha_template(input_path.read_text(encoding="utf-8"), name=name or input_path.stem)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(yaml.safe_dump(template_to_config(template), sort_keys=False), encoding="utf-8")
    return template


def _clean_text(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def _holding_period(lowered: str) -> int:
    match = re.search(r"(\d+)[-\s]*(day|trading day)", lowered)
    if match:
        value = int(match.group(1))
        if 1 <= value <= 252:
            return value
    if "monthly" in lowered:
        return 21
    if "weekly" in lowered:
        return 5
    return 5


def _hypothesis(text: str, positive: list[str], negative: list[str], holding_period: int) -> str:
    first_sentence = text.split(".")[0].strip()
    if len(first_sentence) >= 40:
        return first_sentence[:280]
    return (
        f"Assets with stronger {', '.join(positive)} and weaker {', '.join(negative) or 'risk'} "
        f"should outperform over the next {holding_period} trading days."
    )


def _slug(value: str) -> str:
    slug = re.sub(r"[^a-zA-Z0-9]+", "_", value).strip("_").lower()
    return slug or "paper_alpha_template"
