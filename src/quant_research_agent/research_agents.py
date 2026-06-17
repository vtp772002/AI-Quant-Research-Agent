from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import json
import re

import yaml

from quant_research_agent.config import AppConfig, load_config
from quant_research_agent.experiment_registry import ExperimentRunRecord, list_runs, record_to_dict
from quant_research_agent.factors.registry import factor_names
from quant_research_agent.idea_review import (
    create_review_queue,
    enforce_review_gate,
    mark_configs_ran,
)
from quant_research_agent.llm_provider import (
    PROMPT_SCHEMA_VERSION,
    ProviderArtifacts,
    build_research_prompt_payload,
    run_structured_provider,
)
from quant_research_agent.operations import BatchRunResult, run_research_batch
from quant_research_agent.run_comparison import compare_run_manifests


@dataclass(frozen=True)
class ExperimentIdea:
    name: str
    hypothesis: str
    positive_factors: list[str]
    negative_factors: list[str]
    holding_period: int
    quantile: float
    rationale: str
    confidence: float
    warnings: list[str]


@dataclass(frozen=True)
class IdeaValidation:
    valid: bool
    errors: list[str]
    warnings: list[str]


@dataclass(frozen=True)
class ResearchMemory:
    run_count: int
    best_runs: list[dict[str, object]]
    weak_runs: list[dict[str, object]]
    recurring_warnings: list[str]


@dataclass(frozen=True)
class ResearchCritique:
    run_id: str
    verdict: str
    reasons: list[str]
    next_experiment: ExperimentIdea


@dataclass(frozen=True)
class AlphaMiningResult:
    ideas: list[ExperimentIdea]
    config_paths: list[Path]
    ideas_path: Path
    review_queue_path: Path
    batch_result: BatchRunResult | None
    provider_artifacts: ProviderArtifacts | None


class LLMResearchAgent:
    """LLM-facing research agent with deterministic fallback.

    The public contract is strict JSON-like `ExperimentIdea` objects. A future
    provider can fill this contract from an LLM response; the default generator
    stays deterministic so validation and CI do not require API keys.
    """

    def generate_ideas(
        self,
        base_config: AppConfig,
        memory: ResearchMemory,
        objective: str,
        count: int,
    ) -> list[ExperimentIdea]:
        if count <= 0:
            raise ValueError("count must be positive")
        clean_objective = (objective.strip() or "Cross-sectional equity alpha").rstrip(".:")
        templates = [
            (
                "momentum_quality_low_risk",
                ["momentum_20d", "momentum_60d"],
                ["volatility_20d", "drawdown_20d"],
                "Test whether medium-term momentum survives after penalizing realized risk.",
            ),
            (
                "short_reversal_liquidity_filter",
                ["reversal_5d", "dollar_volume_20d"],
                ["volatility_10d"],
                "Test whether short-term reversal is more robust in liquid, lower-volatility names.",
            ),
            (
                "trend_volume_confirmation",
                ["moving_average_gap_20d", "volume_spike_20d"],
                ["amihud_illiquidity_20d"],
                "Test whether trend continuation improves when volume confirms the move.",
            ),
            (
                "risk_adjusted_breakout",
                ["return_zscore_20d", "momentum_10d"],
                ["downside_volatility_20d"],
                "Test whether positive return shocks work better after downside-risk adjustment.",
            ),
        ]
        ideas: list[ExperimentIdea] = []
        for index in range(count):
            slug, positive, negative, rationale = templates[index % len(templates)]
            holding_period = [3, 5, 10, 21][index % 4]
            quantile = [0.15, 0.20, 0.25][index % 3]
            memory_note = (
                f"Memory contains {memory.run_count} prior runs; avoid repeating weak configurations."
                if memory.run_count
                else "No prior run memory available."
            )
            idea = ExperimentIdea(
                name=f"{slug}_{index + 1}",
                hypothesis=(
                    f"{clean_objective}: {rationale} "
                    f"Expected holding period is {holding_period} trading days."
                ),
                positive_factors=positive,
                negative_factors=negative,
                holding_period=holding_period,
                quantile=quantile,
                rationale=f"{rationale} {memory_note}",
                confidence=max(0.35, 0.70 - index * 0.05),
                warnings=["Generated idea requires validation before use."],
            )
            validation = validate_experiment_idea(idea)
            if validation.valid:
                ideas.append(idea)
            else:
                raise ValueError(f"generated invalid idea {idea.name}: {validation.errors}")
        return ideas


def validate_experiment_idea(idea: ExperimentIdea) -> IdeaValidation:
    allowed = set(factor_names())
    errors: list[str] = []
    warnings: list[str] = []
    if not re.fullmatch(r"[a-z0-9_]+", idea.name):
        errors.append("name must be lowercase snake_case")
    unknown = sorted((set(idea.positive_factors) | set(idea.negative_factors)) - allowed)
    if unknown:
        errors.append(f"unknown factors: {unknown}")
    if set(idea.positive_factors) & set(idea.negative_factors):
        errors.append("positive_factors and negative_factors must not overlap")
    if not idea.positive_factors and not idea.negative_factors:
        errors.append("at least one factor is required")
    if not 1 <= idea.holding_period <= 252:
        errors.append("holding_period must be between 1 and 252")
    if not 0.0 < idea.quantile < 0.5:
        errors.append("quantile must be between 0 and 0.5")
    if idea.confidence < 0.5:
        warnings.append("idea confidence is low; require human review before running")
    return IdeaValidation(valid=not errors, errors=errors, warnings=warnings)


def load_research_memory(registry_path: Path, limit: int = 50) -> ResearchMemory:
    records = list_runs(registry_path, limit=limit)
    ranked = sorted(records, key=lambda record: record.test_sharpe, reverse=True)
    best = [record_to_dict(record) for record in ranked[:3]]
    weak = [record_to_dict(record) for record in sorted(records, key=lambda record: record.test_sharpe)[:3]]
    warnings: list[str] = []
    if any(record.code_dirty for record in records):
        warnings.append("Some prior runs came from dirty worktrees.")
    if len({record.config_sha256 for record in records}) > 1:
        warnings.append("Prior memory spans multiple config hashes; compare ideas cautiously.")
    return ResearchMemory(
        run_count=len(records),
        best_runs=best,
        weak_runs=weak,
        recurring_warnings=warnings,
    )


def critique_run_manifest(manifest_path: Path) -> ResearchCritique:
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    metrics = manifest["metrics"]["test"]
    run_id = str(manifest["run_id"])
    sharpe = float(metrics.get("sharpe", 0.0))
    total_return = float(metrics.get("total_return", 0.0))
    ic_mean = float(metrics.get("ic_mean", 0.0))
    max_drawdown = float(metrics.get("max_drawdown", 0.0))
    average_cost = float(metrics.get("average_total_cost", 0.0))
    reasons: list[str] = []
    if sharpe <= 0:
        reasons.append("Reject: test Sharpe is non-positive.")
    elif sharpe < 0.5:
        reasons.append("Weak: test Sharpe is positive but below a strong research threshold.")
    else:
        reasons.append("Promising: test Sharpe clears the initial threshold.")
    if total_return <= 0:
        reasons.append("Total return is non-positive in the test window.")
    if ic_mean <= 0:
        reasons.append("Mean IC is non-positive; cross-sectional ranking quality is weak.")
    if max_drawdown < -0.20:
        reasons.append("Max drawdown is severe for a research candidate.")
    if average_cost > 0.002:
        reasons.append("Average total cost is high enough to threaten deployability.")

    verdict = "accept" if sharpe >= 0.5 and total_return > 0 and ic_mean > 0 else "reject"
    next_idea = ExperimentIdea(
        name=f"critic_followup_{_slug(run_id)[:24].strip('_')}",
        hypothesis="Refine the rejected or marginal signal by reducing cost and redundant risk exposure.",
        positive_factors=["momentum_20d", "dollar_volume_20d"],
        negative_factors=["volatility_20d", "amihud_illiquidity_20d"],
        holding_period=10,
        quantile=0.2,
        rationale="Critic proposes adding liquidity support and penalizing volatility/illiquidity.",
        confidence=0.62,
        warnings=["Critic proposal is a draft; validate against prior run memory before execution."],
    )
    return ResearchCritique(
        run_id=run_id,
        verdict=verdict,
        reasons=reasons,
        next_experiment=next_idea,
    )


def idea_to_config(base_config_path: Path, idea: ExperimentIdea, output_path: Path) -> Path:
    validation = validate_experiment_idea(idea)
    if not validation.valid:
        raise ValueError(f"invalid idea {idea.name}: {validation.errors}")
    raw = yaml.safe_load(base_config_path.read_text(encoding="utf-8")) or {}
    experiment = dict(raw["experiment"])
    backtest = dict(experiment["backtest"])
    signal = dict(experiment["signal"])
    signal["positive_factors"] = idea.positive_factors
    signal["negative_factors"] = idea.negative_factors
    backtest["holding_period"] = idea.holding_period
    backtest["rebalance_days"] = idea.holding_period
    backtest["quantile"] = idea.quantile
    experiment["name"] = idea.name
    experiment["hypothesis"] = idea.hypothesis
    experiment["signal"] = signal
    experiment["backtest"] = backtest
    raw["experiment"] = experiment
    report = dict(raw["report"])
    report["output_path"] = str(output_path.with_suffix(".md"))
    report["experiments_path"] = str(output_path.parent / "experiments.csv")
    report["registry_path"] = str(output_path.parent / "experiments.sqlite")
    raw["report"] = report
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(yaml.safe_dump(raw, sort_keys=False), encoding="utf-8")
    return output_path


def generate_idea_configs(
    base_config_path: Path,
    output_dir: Path,
    objective: str,
    count: int,
    registry_path: Path,
) -> tuple[list[ExperimentIdea], list[Path], Path]:
    base_config = load_config(base_config_path)
    memory = load_research_memory(registry_path)
    ideas = LLMResearchAgent().generate_ideas(base_config, memory, objective, count)
    configs_dir = output_dir / "configs"
    config_paths = [
        idea_to_config(base_config_path, idea, configs_dir / f"{idea.name}.yaml")
        for idea in ideas
    ]
    ideas_path = output_dir / "ideas.json"
    ideas_path.parent.mkdir(parents=True, exist_ok=True)
    ideas_path.write_text(json.dumps([idea_to_dict(idea) for idea in ideas], indent=2, sort_keys=True), encoding="utf-8")
    create_review_queue(
        ideas=[idea_to_dict(idea) for idea in ideas],
        config_paths=config_paths,
        output_dir=output_dir,
        source="deterministic",
    )
    return ideas, config_paths, ideas_path


def generate_idea_configs_with_provider(
    base_config_path: Path,
    output_dir: Path,
    objective: str,
    count: int,
    registry_path: Path,
    provider: str = "deterministic",
    fixture_path: Path | None = None,
    command: str | None = None,
    allow_external: bool = False,
    prompt_version: str = PROMPT_SCHEMA_VERSION,
    model: str | None = None,
    api_url: str | None = None,
    timeout_seconds: float = 60.0,
) -> tuple[list[ExperimentIdea], list[Path], Path, Path, ProviderArtifacts | None]:
    base_config = load_config(base_config_path)
    memory = load_research_memory(registry_path)
    provider_artifacts = None
    if provider == "deterministic":
        ideas = LLMResearchAgent().generate_ideas(base_config, memory, objective, count)
    else:
        prompt_payload = build_research_prompt_payload(
            objective=objective,
            count=count,
            factor_names=factor_names(),
            memory=memory_to_dict(memory),
            base_experiment={
                "name": base_config.experiment.name,
                "positive_factors": base_config.experiment.signal.positive_factors,
                "negative_factors": base_config.experiment.signal.negative_factors,
                "holding_period": base_config.experiment.backtest.holding_period,
                "quantile": base_config.experiment.backtest.quantile,
            },
            prompt_version=prompt_version,
        )
        raw_ideas, provider_artifacts = run_structured_provider(
            provider=provider,
            prompt_payload=prompt_payload,
            transcript_dir=output_dir / "llm_transcripts",
            fixture_path=fixture_path,
            command=command,
            allow_external=allow_external,
            model=model,
            api_url=api_url,
            timeout_seconds=timeout_seconds,
        )
        ideas = [_idea_from_payload(item) for item in raw_ideas[:count]]
        for idea in ideas:
            validation = validate_experiment_idea(idea)
            if not validation.valid:
                raise ValueError(f"provider generated invalid idea {idea.name}: {validation.errors}")
    configs_dir = output_dir / "configs"
    config_paths = [
        idea_to_config(base_config_path, idea, configs_dir / f"{idea.name}.yaml")
        for idea in ideas
    ]
    ideas_path = output_dir / "ideas.json"
    ideas_path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "provider": provider,
        "provider_artifacts": None
        if provider_artifacts is None
        else {
            "prompt_path": str(provider_artifacts.prompt_path),
            "response_path": str(provider_artifacts.response_path),
            "transcript_path": str(provider_artifacts.transcript_path),
            "prompt_version": provider_artifacts.prompt_version,
            "warnings": provider_artifacts.warnings,
        },
        "ideas": [idea_to_dict(idea) for idea in ideas],
    }
    ideas_path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    review_queue_path = create_review_queue(
        ideas=[idea_to_dict(idea) for idea in ideas],
        config_paths=config_paths,
        output_dir=output_dir,
        source=provider,
    )
    return ideas, config_paths, ideas_path, review_queue_path, provider_artifacts


def mine_alpha(
    base_config_path: Path,
    output_dir: Path,
    objective: str,
    count: int,
    registry_path: Path,
    run_generated: bool = False,
    provider: str = "deterministic",
    fixture_path: Path | None = None,
    command: str | None = None,
    allow_external: bool = False,
    prompt_version: str = PROMPT_SCHEMA_VERSION,
    review_override: bool = False,
    model: str | None = None,
    api_url: str | None = None,
    timeout_seconds: float = 60.0,
) -> AlphaMiningResult:
    ideas, config_paths, ideas_path, review_queue_path, provider_artifacts = generate_idea_configs_with_provider(
        base_config_path=base_config_path,
        output_dir=output_dir,
        objective=objective,
        count=count,
        registry_path=registry_path,
        provider=provider,
        fixture_path=fixture_path,
        command=command,
        allow_external=allow_external,
        prompt_version=prompt_version,
        model=model,
        api_url=api_url,
        timeout_seconds=timeout_seconds,
    )
    batch_result = None
    if run_generated:
        enforce_review_gate(review_queue_path, config_paths, override=review_override)
        batch_result = run_research_batch(
            config_paths=config_paths,
            output_dir=output_dir / "batch",
            limit=count,
        )
        mark_configs_ran(
            review_queue_path,
            config_paths,
            note="Ran generated idea configs with review override." if review_override else "Ran approved idea configs.",
        )
    return AlphaMiningResult(
        ideas=ideas,
        config_paths=config_paths,
        ideas_path=ideas_path,
        review_queue_path=review_queue_path,
        batch_result=batch_result,
        provider_artifacts=provider_artifacts,
    )


def paper_to_alpha_v2(text: str, name: str = "paper_alpha_template") -> dict[str, object]:
    from quant_research_agent.paper_alpha import extract_alpha_template

    template = extract_alpha_template(text, name=name)
    idea = ExperimentIdea(
        name=template.name,
        hypothesis=template.hypothesis,
        positive_factors=template.positive_factors,
        negative_factors=template.negative_factors,
        holding_period=template.holding_period,
        quantile=0.2,
        rationale="Extracted from paper text and mapped to the available factor grammar.",
        confidence=0.55 if len(text.strip()) < 500 else 0.70,
        warnings=template.warnings,
    )
    validation = validate_experiment_idea(idea)
    unsupported = _unsupported_concepts(text)
    return {
        "idea": idea_to_dict(idea),
        "validation": validation.__dict__,
        "factor_mapping": {
            "available_factor_count": len(factor_names()),
            "positive_factors": idea.positive_factors,
            "negative_factors": idea.negative_factors,
            "unsupported_concepts": unsupported,
        },
        "bias_warnings": _bias_warnings(text),
    }


def idea_to_dict(idea: ExperimentIdea) -> dict[str, object]:
    return {
        "name": idea.name,
        "hypothesis": idea.hypothesis,
        "positive_factors": idea.positive_factors,
        "negative_factors": idea.negative_factors,
        "holding_period": idea.holding_period,
        "quantile": idea.quantile,
        "rationale": idea.rationale,
        "confidence": idea.confidence,
        "warnings": idea.warnings,
    }


def critique_to_dict(critique: ResearchCritique) -> dict[str, object]:
    return {
        "run_id": critique.run_id,
        "verdict": critique.verdict,
        "reasons": critique.reasons,
        "next_experiment": idea_to_dict(critique.next_experiment),
    }


def mining_result_to_dict(result: AlphaMiningResult) -> dict[str, object]:
    return {
        "ideas_path": str(result.ideas_path),
        "review_queue_path": str(result.review_queue_path),
        "config_paths": [str(path) for path in result.config_paths],
        "ideas": [idea_to_dict(idea) for idea in result.ideas],
        "batch": None
        if result.batch_result is None
        else {
            "status": result.batch_result.status,
            "successful_runs": len(result.batch_result.runs),
            "failed_runs": len(result.batch_result.failures),
            "summary_path": str(result.batch_result.summary_path),
        },
        "provider_artifacts": None
        if result.provider_artifacts is None
        else {
            "provider": result.provider_artifacts.provider,
            "prompt_version": result.provider_artifacts.prompt_version,
            "prompt_path": str(result.provider_artifacts.prompt_path),
            "response_path": str(result.provider_artifacts.response_path),
            "transcript_path": str(result.provider_artifacts.transcript_path),
            "warnings": result.provider_artifacts.warnings,
        },
    }


def memory_to_dict(memory: ResearchMemory) -> dict[str, object]:
    return {
        "run_count": memory.run_count,
        "best_runs": memory.best_runs,
        "weak_runs": memory.weak_runs,
        "recurring_warnings": memory.recurring_warnings,
    }


def _idea_from_payload(payload: dict[str, Any]) -> ExperimentIdea:
    return ExperimentIdea(
        name=str(payload["name"]),
        hypothesis=str(payload["hypothesis"]),
        positive_factors=[str(item) for item in payload.get("positive_factors", [])],
        negative_factors=[str(item) for item in payload.get("negative_factors", [])],
        holding_period=int(payload["holding_period"]),
        quantile=float(payload["quantile"]),
        rationale=str(payload.get("rationale", "")),
        confidence=float(payload.get("confidence", 0.5)),
        warnings=[str(item) for item in payload.get("warnings", [])],
    )


def _unsupported_concepts(text: str) -> list[str]:
    lowered = text.lower()
    concepts = []
    for keyword in ["sentiment", "earnings", "options", "fundamental", "news", "analyst"]:
        if keyword in lowered:
            concepts.append(keyword)
    return concepts


def _bias_warnings(text: str) -> list[str]:
    warnings = ["Check for survivorship bias, lookahead bias, and data-snooping before treating the idea as research evidence."]
    lowered = text.lower()
    if "future" in lowered or "next quarter" in lowered:
        warnings.append("Paper text references future-looking language; verify features are available at decision time.")
    return warnings


def _slug(value: str) -> str:
    slug = re.sub(r"[^a-zA-Z0-9]+", "_", value).strip("_").lower()
    return slug or "run"
