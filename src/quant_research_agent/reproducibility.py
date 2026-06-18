from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from shutil import copy2
from subprocess import run
from uuid import uuid4

import json

from quant_research_agent.agents.evaluator_agent import ResearchRunResult
from quant_research_agent.agents.research_validity import research_validity_to_dict
from quant_research_agent.config import AppConfig
from quant_research_agent.data.snapshot import file_sha256
from quant_research_agent.locked_holdout import locked_holdout_to_dict


@dataclass(frozen=True)
class RunContext:
    run_id: str
    generated_at: str
    config_path: Path
    config_sha256: str
    bundle_dir: Path
    manifest_path: Path
    copied_config_path: Path
    code: dict[str, object]


def create_run_context(config_path: Path, config: AppConfig) -> RunContext:
    config_path = config_path.resolve()
    generated_at = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
    config_hash = file_sha256(config_path)
    short_hash = config_hash[:10]
    run_id = f"{_slug(config.experiment.name)}-{datetime.now(UTC).strftime('%Y%m%dT%H%M%SZ')}-{short_hash}-{uuid4().hex[:8]}"
    bundle_dir = config.report.experiments_path.parent / "runs" / run_id
    return RunContext(
        run_id=run_id,
        generated_at=generated_at,
        config_path=config_path,
        config_sha256=config_hash,
        bundle_dir=bundle_dir,
        manifest_path=bundle_dir / "manifest.json",
        copied_config_path=bundle_dir / "config.yaml",
        code=_git_metadata(),
    )


def append_reproducibility_section(report_path: Path, context: RunContext) -> None:
    section = "\n".join(
        [
            "",
            "## Run Reproducibility",
            "",
            f"- Run ID: `{context.run_id}`",
            f"- Generated at: `{context.generated_at}`",
            f"- Config SHA-256: `{context.config_sha256}`",
            f"- Git commit: `{context.code['commit']}`",
            f"- Git branch: `{context.code['branch']}`",
            f"- Git dirty: {_yes_no(bool(context.code['dirty']))}",
            f"- Manifest: `{context.manifest_path}`",
            f"- Frozen config: `{context.copied_config_path}`",
            "",
        ]
    )
    with report_path.open("a", encoding="utf-8") as handle:
        handle.write(section)


def write_reproducibility_pack(
    context: RunContext,
    config: AppConfig,
    result: ResearchRunResult,
    report_path: Path,
    experiments_path: Path,
) -> dict[str, object]:
    context.bundle_dir.mkdir(parents=True, exist_ok=True)
    copy2(context.config_path, context.copied_config_path)

    research_validity = research_validity_to_dict(result.research_validity)
    research_validity["locked_holdout"] = locked_holdout_to_dict(result.locked_holdout)
    manifest = {
        "run_id": context.run_id,
        "generated_at": context.generated_at,
        "experiment": config.experiment.name,
        "config": {
            "path": str(context.config_path),
            "copied_path": str(context.copied_config_path),
            "sha256": context.config_sha256,
        },
        "experiment_family": {
            "family_id": config.experiment.family.family_id,
            "hypothesis_id": config.experiment.family.hypothesis_id,
            "candidate_id": config.experiment.family.candidate_id,
            "selection_policy": config.experiment.family.selection_policy,
        },
        "code": context.code,
        "data": _data_fingerprint(config=config, result=result),
        "artifacts": {
            "report_path": str(report_path),
            "report_sha256": file_sha256(report_path),
            "experiments_path": str(experiments_path),
            "experiments_sha256": file_sha256(experiments_path),
            "manifest_path": str(context.manifest_path),
        },
        "metrics": {
            "test": result.backtest.metrics["test"],
            "validation": result.backtest.metrics["validation"],
            "holdout": result.backtest.metrics["holdout"],
            "full": result.backtest.metrics["full"],
            "research_validity": research_validity,
        },
        "research_validity": research_validity,
    }
    context.manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True), encoding="utf-8")
    return manifest


def _data_fingerprint(config: AppConfig, result: ResearchRunResult) -> dict[str, object]:
    provenance = result.data_integrity.provenance
    locate_path = config.experiment.shorting.locate_history_path
    return {
        "source": config.data.source,
        "row_count": result.data_integrity.row_count,
        "date_count": result.data_integrity.date_count,
        "observed_symbols": result.data_integrity.observed_symbols,
        "snapshot_dataset_id": provenance.dataset_id if provenance is not None else None,
        "snapshot_content_sha256": provenance.content_sha256 if provenance is not None else None,
        "snapshot_manifest_path": provenance.manifest_path if provenance is not None else None,
        "locate_history_path": str(locate_path) if locate_path is not None else None,
        "locate_history_sha256": file_sha256(locate_path) if locate_path is not None and locate_path.exists() else None,
    }


def _git_metadata() -> dict[str, object]:
    return {
        "commit": _git("rev-parse", "HEAD"),
        "branch": _git("branch", "--show-current"),
        "dirty": bool(_git("status", "--short")),
    }


def _git(*args: str) -> str:
    completed = run(["git", *args], check=False, capture_output=True, text=True)
    if completed.returncode != 0:
        return "unknown"
    return completed.stdout.strip()


def _slug(value: str) -> str:
    allowed = []
    for char in value.lower():
        if char.isalnum():
            allowed.append(char)
        elif char in {"-", "_", " "}:
            allowed.append("-")
    text = "".join(allowed).strip("-")
    while "--" in text:
        text = text.replace("--", "-")
    return text or "run"


def _yes_no(value: bool) -> str:
    return "yes" if value else "no"
