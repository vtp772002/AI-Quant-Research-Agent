from __future__ import annotations

from dataclasses import dataclass, replace
from pathlib import Path
from statistics import mean
from typing import Any

import json

from quant_research_agent.agents.research_validity import adjust_pvalues_benjamini_hochberg


@dataclass(frozen=True)
class ExperimentFamilyRow:
    run_id: str
    experiment: str
    generated_at: str
    family_id: str | None
    hypothesis_id: str | None
    candidate_id: str | None
    selection_policy: str | None
    config_sha256: str
    code_commit: str
    code_dirty: bool
    source: str
    dataset_id: str | None
    run_validity_verdict: str
    holdout_ic_mean: float
    holdout_sharpe: float
    holdout_total_return: float
    agent_p_value: float
    agent_q_value: float
    family_q_value: float
    family_verdict: str
    reasons: list[str]
    manifest_path: str
    missing_agent_evidence: bool


@dataclass(frozen=True)
class ExperimentFamilyComparison:
    family_id: str | None
    run_count: int
    fdr_alpha: float
    rows: list[ExperimentFamilyRow]
    warnings: list[str]
    summary: dict[str, object]


def compare_experiment_family(
    path: Path,
    *,
    family_id: str | None = None,
    fdr_alpha: float = 0.10,
    limit: int | None = None,
) -> ExperimentFamilyComparison:
    if not 0.0 < fdr_alpha <= 0.25:
        raise ValueError("family_fdr_alpha must be greater than 0 and at most 0.25")
    rows = [_row_from_manifest(manifest_path) for manifest_path in _discover_manifests(path)]
    if family_id is not None:
        rows = [row for row in rows if row.family_id == family_id]
    if not rows:
        raise FileNotFoundError(f"No experiment family manifests found under {path}")

    q_values = adjust_pvalues_benjamini_hochberg(
        {row.run_id: row.agent_p_value for row in rows}
    )
    rows = [replace(row, family_q_value=float(q_values[row.run_id])) for row in rows]
    warnings = _warnings(rows)
    pre_registered_count = sum(row.selection_policy == "pre_registered" for row in rows)
    rows = [
        replace(
            row,
            family_verdict=_family_verdict(
                row=row,
                fdr_alpha=fdr_alpha,
                warnings=warnings,
                pre_registered_count=pre_registered_count,
            ),
            reasons=_family_reasons(
                row=row,
                fdr_alpha=fdr_alpha,
                warnings=warnings,
                pre_registered_count=pre_registered_count,
            ),
        )
        for row in rows
    ]
    rows = sorted(rows, key=lambda row: (row.family_q_value, row.generated_at, row.run_id))
    display_rows = rows[:limit] if limit is not None else rows
    return ExperimentFamilyComparison(
        family_id=family_id,
        run_count=len(rows),
        fdr_alpha=fdr_alpha,
        rows=display_rows,
        warnings=warnings,
        summary=_summary(rows),
    )


def family_comparison_to_dict(comparison: ExperimentFamilyComparison) -> dict[str, object]:
    return {
        "family_id": comparison.family_id,
        "run_count": comparison.run_count,
        "fdr_alpha": comparison.fdr_alpha,
        "summary": comparison.summary,
        "warnings": comparison.warnings,
        "rows": [
            {
                "run_id": row.run_id,
                "experiment": row.experiment,
                "generated_at": row.generated_at,
                "family_id": row.family_id,
                "hypothesis_id": row.hypothesis_id,
                "candidate_id": row.candidate_id,
                "selection_policy": row.selection_policy,
                "config_sha256": row.config_sha256,
                "code_commit": row.code_commit,
                "code_dirty": row.code_dirty,
                "source": row.source,
                "dataset_id": row.dataset_id,
                "run_validity_verdict": row.run_validity_verdict,
                "holdout_ic_mean": row.holdout_ic_mean,
                "holdout_sharpe": row.holdout_sharpe,
                "holdout_total_return": row.holdout_total_return,
                "agent_p_value": row.agent_p_value,
                "agent_q_value": row.agent_q_value,
                "family_q_value": row.family_q_value,
                "family_verdict": row.family_verdict,
                "reasons": row.reasons,
                "manifest_path": row.manifest_path,
                "missing_agent_evidence": row.missing_agent_evidence,
            }
            for row in comparison.rows
        ],
    }


def family_comparison_to_markdown(comparison: ExperimentFamilyComparison) -> str:
    lines = [
        "# Experiment Family Comparison",
        "",
        f"- Family filter: `{comparison.family_id or 'all'}`",
        f"- Runs discovered: `{comparison.run_count}`",
        f"- Family FDR alpha: `{comparison.fdr_alpha:.2f}`",
        f"- Pre-registered candidates: `{comparison.summary['pre_registered_count']}`",
        "",
        "## Summary",
        "",
    ]
    for key, value in comparison.summary.items():
        lines.append(f"- {key}: `{value}`")
    lines.extend(
        [
            "",
            "## Family Rows",
            "",
            "| Run ID | Candidate | Selection | Run Verdict | Agent p | Family q | Family Verdict |",
            "| --- | --- | --- | --- | ---: | ---: | --- |",
        ]
    )
    for row in comparison.rows:
        lines.append(
            f"| `{row.run_id}` | `{row.candidate_id or ''}` | {row.selection_policy or ''} | "
            f"{row.run_validity_verdict} | {row.agent_p_value:.4f} | {row.family_q_value:.4f} | {row.family_verdict} |"
        )
    if comparison.warnings:
        lines.extend(["", "## Warnings", ""])
        for warning in comparison.warnings:
            lines.append(f"- {warning}")
    row_reasons = [(row.run_id, row.reasons) for row in comparison.rows if row.reasons]
    if row_reasons:
        lines.extend(["", "## Reasons", ""])
        for run_id, reasons in row_reasons:
            lines.append(f"- `{run_id}`:")
            for reason in reasons:
                lines.append(f"  - {reason}")
    lines.append("")
    return "\n".join(lines)


def _discover_manifests(path: Path) -> list[Path]:
    path = path.expanduser()
    if path.is_file():
        manifest_paths = [path]
    else:
        manifest_paths = sorted(path.glob("*/manifest.json"))
    if not manifest_paths:
        raise FileNotFoundError(f"No manifest.json files found under {path}")
    return manifest_paths


def _row_from_manifest(path: Path) -> ExperimentFamilyRow:
    manifest = json.loads(path.read_text(encoding="utf-8"))
    family = _as_dict(manifest.get("experiment_family"))
    code = _as_dict(manifest.get("code"))
    data = _as_dict(manifest.get("data"))
    config = _as_dict(manifest.get("config"))
    validity = _as_dict(manifest.get("research_validity"))
    if not validity:
        validity = _as_dict(_as_dict(manifest.get("metrics")).get("research_validity"))
    agent = _agent_candidate(validity)
    holdout = _as_dict(_as_dict(manifest.get("metrics")).get("holdout"))
    missing_agent = agent is None
    return ExperimentFamilyRow(
        run_id=str(manifest["run_id"]),
        experiment=str(manifest["experiment"]),
        generated_at=str(manifest["generated_at"]),
        family_id=_optional_str(family.get("family_id")),
        hypothesis_id=_optional_str(family.get("hypothesis_id")),
        candidate_id=_optional_str(family.get("candidate_id")),
        selection_policy=_optional_str(family.get("selection_policy")),
        config_sha256=str(config.get("sha256", "unknown")),
        code_commit=str(code.get("commit", "unknown")),
        code_dirty=bool(code.get("dirty", False)),
        source=str(data.get("source", "unknown")),
        dataset_id=_optional_str(data.get("snapshot_dataset_id")),
        run_validity_verdict=str(validity.get("verdict", "REVIEW")),
        holdout_ic_mean=float((agent or holdout).get("holdout_ic_mean", holdout.get("ic_mean", 0.0))),
        holdout_sharpe=float((agent or holdout).get("holdout_sharpe", holdout.get("sharpe", 0.0))),
        holdout_total_return=float((agent or holdout).get("holdout_total_return", holdout.get("total_return", 0.0))),
        agent_p_value=1.0 if missing_agent else float(agent.get("p_value", 1.0)),
        agent_q_value=1.0 if missing_agent else float(agent.get("q_value", 1.0)),
        family_q_value=1.0,
        family_verdict="FAMILY_REVIEW",
        reasons=[],
        manifest_path=str(path),
        missing_agent_evidence=missing_agent,
    )


def _agent_candidate(validity: dict[str, Any]) -> dict[str, Any] | None:
    candidates = validity.get("candidates", [])
    if not isinstance(candidates, list):
        return None
    for candidate in candidates:
        if isinstance(candidate, dict) and candidate.get("name") == "agent_signal":
            return candidate
    return None


def _family_verdict(
    *,
    row: ExperimentFamilyRow,
    fdr_alpha: float,
    warnings: list[str],
    pre_registered_count: int,
) -> str:
    if row.run_validity_verdict == "REJECT":
        return "FAMILY_REJECT"
    if row.missing_agent_evidence:
        return "FAMILY_REVIEW"
    if row.family_q_value > fdr_alpha:
        return "FAMILY_REJECT"
    if _review_needed(row=row, warnings=warnings, pre_registered_count=pre_registered_count):
        return "FAMILY_REVIEW"
    if row.run_validity_verdict != "PROMOTE":
        return "FAMILY_REVIEW"
    return "FAMILY_PROMOTE"


def _family_reasons(
    *,
    row: ExperimentFamilyRow,
    fdr_alpha: float,
    warnings: list[str],
    pre_registered_count: int,
) -> list[str]:
    reasons: list[str] = []
    if row.family_id is None:
        reasons.append("family metadata is missing")
    if row.selection_policy != "pre_registered":
        reasons.append(f"selection policy {row.selection_policy or 'missing'} is not pre_registered")
    if row.run_validity_verdict == "REJECT":
        reasons.append("run-level validity verdict is REJECT")
    elif row.run_validity_verdict == "REVIEW":
        reasons.append("run-level validity verdict is REVIEW")
    if row.missing_agent_evidence:
        reasons.append("agent_signal p-value evidence is missing")
    elif row.family_q_value > fdr_alpha:
        reasons.append(
            f"family q-value {row.family_q_value:.4f} must be at most {fdr_alpha:.4f}"
        )
    if row.code_dirty:
        reasons.append("run was generated from a dirty git worktree")
    if pre_registered_count > 1:
        reasons.append("multiple pre-registered candidates exist in this family")
    if _mixed_provenance(warnings):
        reasons.append("family provenance differs across compared rows")
    return reasons


def _review_needed(
    *,
    row: ExperimentFamilyRow,
    warnings: list[str],
    pre_registered_count: int,
) -> bool:
    return (
        row.family_id is None
        or row.selection_policy != "pre_registered"
        or row.run_validity_verdict == "REVIEW"
        or row.code_dirty
        or pre_registered_count != 1
        or _mixed_provenance(warnings)
    )


def _warnings(rows: list[ExperimentFamilyRow]) -> list[str]:
    warnings: list[str] = []
    if any(row.family_id is None for row in rows):
        warnings.append("At least one family row is missing experiment_family.family_id.")
    if sum(row.selection_policy == "pre_registered" for row in rows) > 1:
        warnings.append("Multiple pre-registered candidates exist in this family.")
    if not any(row.selection_policy == "pre_registered" for row in rows):
        warnings.append("No pre-registered candidate exists in this family.")
    if len({row.config_sha256 for row in rows}) > 1:
        warnings.append("Compared family rows use different config hashes.")
    if len({row.code_commit for row in rows}) > 1:
        warnings.append("Compared family rows use different git commits.")
    if any(row.code_dirty for row in rows):
        warnings.append("At least one family row was generated from a dirty git worktree.")
    if len({row.source for row in rows}) > 1:
        warnings.append("Compared family rows use different data sources.")
    if len({row.dataset_id for row in rows}) > 1:
        warnings.append("Compared family rows use different snapshot dataset ids.")
    return warnings


def _mixed_provenance(warnings: list[str]) -> bool:
    return any(
        warning in warnings
        for warning in {
            "Compared family rows use different config hashes.",
            "Compared family rows use different data sources.",
            "Compared family rows use different snapshot dataset ids.",
        }
    )


def _summary(rows: list[ExperimentFamilyRow]) -> dict[str, object]:
    return {
        "unique_families": len({row.family_id for row in rows}),
        "unique_hypotheses": len({row.hypothesis_id for row in rows}),
        "unique_configs": len({row.config_sha256 for row in rows}),
        "unique_sources": len({row.source for row in rows}),
        "pre_registered_count": sum(row.selection_policy == "pre_registered" for row in rows),
        "family_promote_count": sum(row.family_verdict == "FAMILY_PROMOTE" for row in rows),
        "family_review_count": sum(row.family_verdict == "FAMILY_REVIEW" for row in rows),
        "family_reject_count": sum(row.family_verdict == "FAMILY_REJECT" for row in rows),
        "average_agent_p_value": round(mean(row.agent_p_value for row in rows), 6),
        "average_family_q_value": round(mean(row.family_q_value for row in rows), 6),
    }


def _as_dict(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        return value
    return {}


def _optional_str(value: Any) -> str | None:
    if value is None:
        return None
    return str(value)
