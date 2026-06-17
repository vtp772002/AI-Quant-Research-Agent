from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import json
import uuid


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


@dataclass(frozen=True)
class IdeaReviewAuditEvent:
    event_id: str
    event_type: str
    queue_path: str
    idea_name: str
    config_path: str
    source: str
    from_status: str | None
    to_status: str
    actor: str
    note: str
    created_at: str


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
    audit_path = audit_path_for_queue(queue_path)
    queue_path.parent.mkdir(parents=True, exist_ok=True)
    queue_path.write_text(
        json.dumps(
            {
                "schema_version": "idea_review_v1",
                "audit_path": str(audit_path),
                "records": records,
            },
            indent=2,
            sort_keys=True,
        ),
        encoding="utf-8",
    )
    audit_path.write_text("", encoding="utf-8")
    for record in records:
        _append_audit_event(
            queue_path,
            event_type="created",
            record=record,
            from_status=None,
            to_status=str(record["status"]),
            actor="system",
            note=str(record["note"]),
        )
    return queue_path


def audit_path_for_queue(queue_path: Path) -> Path:
    return queue_path.with_name("review_audit.jsonl")


def load_review_queue(queue_path: Path) -> dict[str, Any]:
    payload = json.loads(queue_path.read_text(encoding="utf-8"))
    if payload.get("schema_version") != "idea_review_v1":
        raise ValueError("unsupported review queue schema")
    records = payload.get("records")
    if not isinstance(records, list):
        raise ValueError("review queue records must be a list")
    payload.setdefault("audit_path", str(audit_path_for_queue(queue_path)))
    return payload


def update_idea_status(queue_path: Path, idea_name: str, status: str, note: str = "", actor: str = "operator") -> dict[str, Any]:
    if status not in REVIEW_STATUSES:
        raise ValueError(f"status must be one of {sorted(REVIEW_STATUSES)}")
    payload = load_review_queue(queue_path)
    updated = False
    for record in payload["records"]:
        if record["idea_name"] == idea_name:
            previous_status = str(record["status"])
            record["status"] = status
            record["note"] = note or record.get("note", "")
            record["updated_at"] = _now()
            _append_audit_event(
                queue_path,
                event_type="status_changed",
                record=record,
                from_status=previous_status,
                to_status=status,
                actor=actor,
                note=str(record["note"]),
            )
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


def mark_configs_ran(queue_path: Path, config_paths: list[Path], note: str = "Ran approved idea.", actor: str = "system") -> dict[str, Any]:
    payload = load_review_queue(queue_path)
    targets = {str(path) for path in config_paths}
    for record in payload["records"]:
        if str(Path(str(record["config_path"]))) in targets:
            previous_status = str(record["status"])
            record["status"] = "ran"
            record["note"] = note
            record["updated_at"] = _now()
            _append_audit_event(
                queue_path,
                event_type="ran",
                record=record,
                from_status=previous_status,
                to_status="ran",
                actor=actor,
                note=note,
            )
    queue_path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    return payload


def review_audit_events(queue_path: Path) -> list[dict[str, Any]]:
    audit_path = Path(str(load_review_queue(queue_path)["audit_path"]))
    if not audit_path.exists():
        return []
    events = []
    for line in audit_path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            events.append(json.loads(line))
    return events


def review_summary(queue_path: Path) -> dict[str, object]:
    payload = load_review_queue(queue_path)
    counts = {status: 0 for status in sorted(REVIEW_STATUSES)}
    for record in payload["records"]:
        counts[str(record["status"])] = counts.get(str(record["status"]), 0) + 1
    return {
        "queue_path": str(queue_path),
        "audit_path": str(payload["audit_path"]),
        "schema_version": payload["schema_version"],
        "counts": counts,
        "records": payload["records"],
    }


def _append_audit_event(
    queue_path: Path,
    *,
    event_type: str,
    record: dict[str, Any],
    from_status: str | None,
    to_status: str,
    actor: str,
    note: str,
) -> None:
    event = IdeaReviewAuditEvent(
        event_id=str(uuid.uuid4()),
        event_type=event_type,
        queue_path=str(queue_path),
        idea_name=str(record["idea_name"]),
        config_path=str(record["config_path"]),
        source=str(record["source"]),
        from_status=from_status,
        to_status=to_status,
        actor=actor,
        note=note,
        created_at=_now(),
    )
    audit_path = audit_path_for_queue(queue_path)
    audit_path.parent.mkdir(parents=True, exist_ok=True)
    with audit_path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(event.__dict__, sort_keys=True) + "\n")


def _now() -> str:
    return datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
