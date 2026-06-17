from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import json


REVIEW_STATUSES = {"draft", "approved", "rejected", "ran", "archived"}


@dataclass(frozen=True)
class IdeaReviewRecord:
    idea_name: str
    status: str
    config_path: str
    source: str
    note: str
    created_at: str
    updated_at: str


def create_review_queue(
    *,
    ideas: list[dict[str, object]],
    config_paths: list[Path],
    output_dir: Path,
    source: str,
) -> Path:
    if len(ideas) != len(config_paths):
        raise ValueError("ideas and config_paths must have the same length")
    now = _now()
    records = [
        IdeaReviewRecord(
            idea_name=str(idea["name"]),
            status="draft",
            config_path=str(config_path),
            source=source,
            note="Generated idea awaiting human review.",
            created_at=now,
            updated_at=now,
        ).__dict__
        for idea, config_path in zip(ideas, config_paths)
    ]
    queue_path = output_dir / "review_queue.json"
    queue_path.parent.mkdir(parents=True, exist_ok=True)
    queue_path.write_text(
        json.dumps(
            {
                "schema_version": "idea_review_v1",
                "records": records,
            },
            indent=2,
            sort_keys=True,
        ),
        encoding="utf-8",
    )
    return queue_path


def load_review_queue(queue_path: Path) -> dict[str, Any]:
    payload = json.loads(queue_path.read_text(encoding="utf-8"))
    if payload.get("schema_version") != "idea_review_v1":
        raise ValueError("unsupported review queue schema")
    records = payload.get("records")
    if not isinstance(records, list):
        raise ValueError("review queue records must be a list")
    return payload


def update_idea_status(queue_path: Path, idea_name: str, status: str, note: str = "") -> dict[str, Any]:
    if status not in REVIEW_STATUSES:
        raise ValueError(f"status must be one of {sorted(REVIEW_STATUSES)}")
    payload = load_review_queue(queue_path)
    updated = False
    for record in payload["records"]:
        if record["idea_name"] == idea_name:
            record["status"] = status
            record["note"] = note or record.get("note", "")
            record["updated_at"] = _now()
            updated = True
            break
    if not updated:
        raise KeyError(f"idea not found in review queue: {idea_name}")
    queue_path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    return payload


def approved_config_paths(queue_path: Path) -> list[Path]:
    payload = load_review_queue(queue_path)
    return [
        Path(str(record["config_path"]))
        for record in payload["records"]
        if record["status"] == "approved"
    ]


def enforce_review_gate(queue_path: Path, config_paths: list[Path], override: bool = False) -> list[Path]:
    if override:
        return config_paths
    payload = load_review_queue(queue_path)
    status_by_path = {
        str(Path(str(record["config_path"]))): str(record["status"])
        for record in payload["records"]
    }
    blocked = [
        str(path)
        for path in config_paths
        if status_by_path.get(str(path)) != "approved"
    ]
    if blocked:
        raise PermissionError(
            "generated ideas must be approved before running; blocked configs: "
            + ", ".join(blocked)
        )
    return config_paths


def mark_configs_ran(queue_path: Path, config_paths: list[Path], note: str = "Ran approved idea.") -> dict[str, Any]:
    payload = load_review_queue(queue_path)
    targets = {str(path) for path in config_paths}
    for record in payload["records"]:
        if str(Path(str(record["config_path"]))) in targets:
            record["status"] = "ran"
            record["note"] = note
            record["updated_at"] = _now()
    queue_path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    return payload


def review_summary(queue_path: Path) -> dict[str, object]:
    payload = load_review_queue(queue_path)
    counts = {status: 0 for status in sorted(REVIEW_STATUSES)}
    for record in payload["records"]:
        counts[str(record["status"])] = counts.get(str(record["status"]), 0) + 1
    return {
        "queue_path": str(queue_path),
        "schema_version": payload["schema_version"],
        "counts": counts,
        "records": payload["records"],
    }


def _now() -> str:
    return datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
