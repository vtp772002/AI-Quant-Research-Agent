from __future__ import annotations

from contextlib import contextmanager
from dataclasses import dataclass
from datetime import UTC, datetime
from hashlib import sha256
from pathlib import Path
from typing import Any
from uuid import uuid4

import hmac
import json
import threading

try:
    import fcntl
except ImportError:  # pragma: no cover - Windows falls back to the process lock.
    fcntl = None

from quant_research_agent.experiment_family import (
    compare_experiment_family,
    family_comparison_to_dict,
)


EVENT_SCHEMA = "family_promotion_event_v1"
DECISIONS = {"approved", "rejected"}
_LOCKS: dict[str, threading.RLock] = {}
_LOCKS_GUARD = threading.Lock()


@dataclass(frozen=True)
class PromotionLedgerVerification:
    valid: bool
    errors: list[str]
    event_count: int
    recommendation_count: int
    decision_count: int


def recommend_family_promotion(
    *,
    source_path: Path,
    family_id: str,
    run_id: str,
    ledger_path: Path,
    actor: str,
    role: str,
    signing_key: str,
    note: str = "",
    fdr_alpha: float = 0.10,
) -> dict[str, Any]:
    with _ledger_transaction(ledger_path):
        return _recommend_family_promotion_unlocked(
            source_path=source_path,
            family_id=family_id,
            run_id=run_id,
            ledger_path=ledger_path,
            actor=actor,
            role=role,
            signing_key=signing_key,
            note=note,
            fdr_alpha=fdr_alpha,
        )


def _recommend_family_promotion_unlocked(
    *,
    source_path: Path,
    family_id: str,
    run_id: str,
    ledger_path: Path,
    actor: str,
    role: str,
    signing_key: str,
    note: str,
    fdr_alpha: float,
) -> dict[str, Any]:
    _require_actor(actor)
    _require_signing_key(signing_key)
    if role != "researcher":
        raise PermissionError("family promotion recommendation requires researcher role")
    events = _verified_events(ledger_path, signing_key=signing_key)
    if any(
        event.get("event_type") == "recommended"
        and event.get("family_id") == family_id
        and event.get("run_id") == run_id
        for event in events
    ):
        raise ValueError(f"family promotion recommendation already exists for {family_id}/{run_id}")

    comparison = compare_experiment_family(
        source_path,
        family_id=family_id,
        fdr_alpha=fdr_alpha,
    )
    selected = [row for row in comparison.rows if row.run_id == run_id]
    if len(selected) != 1:
        raise ValueError(f"family comparison must contain exactly one requested run: {run_id}")
    row = selected[0]
    if row.family_verdict != "FAMILY_PROMOTE":
        raise ValueError(
            f"family promotion recommendation requires FAMILY_PROMOTE evidence; got {row.family_verdict}"
        )

    recommendation_id = uuid4().hex
    evidence_path = ledger_path.parent / "evidence" / f"{recommendation_id}-family-comparison.json"
    evidence_path.parent.mkdir(parents=True, exist_ok=True)
    evidence_path.write_text(
        json.dumps(family_comparison_to_dict(comparison), indent=2, sort_keys=True),
        encoding="utf-8",
    )
    evidence_sha256 = _file_sha256(evidence_path)
    event = _append_event(
        ledger_path,
        {
            "schema_version": EVENT_SCHEMA,
            "event_id": uuid4().hex,
            "event_type": "recommended",
            "recommendation_id": recommendation_id,
            "created_at": _now(),
            "family_id": row.family_id,
            "hypothesis_id": row.hypothesis_id,
            "candidate_id": row.candidate_id,
            "run_id": row.run_id,
            "actor": actor,
            "role": role,
            "note": note,
            "status": "pending",
            "evidence_path": str(evidence_path),
            "evidence_sha256": evidence_sha256,
        },
        previous_hash=str(events[-1]["event_hash"]) if events else None,
        signing_key=signing_key,
    )
    return event


def decide_family_promotion(
    *,
    ledger_path: Path,
    recommendation_id: str,
    decision: str,
    actor: str,
    role: str,
    signing_key: str,
    note: str = "",
) -> dict[str, Any]:
    with _ledger_transaction(ledger_path):
        return _decide_family_promotion_unlocked(
            ledger_path=ledger_path,
            recommendation_id=recommendation_id,
            decision=decision,
            actor=actor,
            role=role,
            signing_key=signing_key,
            note=note,
        )


def _decide_family_promotion_unlocked(
    *,
    ledger_path: Path,
    recommendation_id: str,
    decision: str,
    actor: str,
    role: str,
    signing_key: str,
    note: str,
) -> dict[str, Any]:
    _require_actor(actor)
    _require_signing_key(signing_key)
    if role != "operator":
        raise PermissionError("family promotion decision requires operator role")
    if decision not in DECISIONS:
        raise ValueError(f"decision must be one of {sorted(DECISIONS)}")
    events = _verified_events(ledger_path, signing_key=signing_key)
    recommendation = _recommendation(events, recommendation_id)
    if any(
        event.get("event_type") == "decided"
        and event.get("recommendation_id") == recommendation_id
        for event in events
    ):
        raise ValueError(f"family promotion recommendation is already decided: {recommendation_id}")
    if actor == recommendation["actor"]:
        raise PermissionError("family promotion decision actor must differ from recommendation actor")

    event = _append_event(
        ledger_path,
        {
            "schema_version": EVENT_SCHEMA,
            "event_id": uuid4().hex,
            "event_type": "decided",
            "recommendation_id": recommendation_id,
            "created_at": _now(),
            "family_id": recommendation["family_id"],
            "hypothesis_id": recommendation["hypothesis_id"],
            "candidate_id": recommendation["candidate_id"],
            "run_id": recommendation["run_id"],
            "actor": actor,
            "role": role,
            "note": note,
            "status": decision,
            "evidence_path": recommendation["evidence_path"],
            "evidence_sha256": recommendation["evidence_sha256"],
        },
        previous_hash=str(events[-1]["event_hash"]),
        signing_key=signing_key,
    )
    return event


def verify_promotion_ledger(
    ledger_path: Path,
    *,
    signing_key: str,
) -> PromotionLedgerVerification:
    _require_signing_key(signing_key)
    try:
        events = _load_events(ledger_path)
    except ValueError as exc:
        return PromotionLedgerVerification(
            valid=False,
            errors=[str(exc)],
            event_count=0,
            recommendation_count=0,
            decision_count=0,
        )
    errors: list[str] = []
    previous_hash: str | None = None
    recommendations: dict[str, dict[str, Any]] = {}
    decisions: set[str] = set()
    family_runs: set[tuple[str, str]] = set()

    for index, event in enumerate(events):
        prefix = f"event {index}"
        if event.get("schema_version") != EVENT_SCHEMA:
            errors.append(f"{prefix} has unsupported schema")
        if event.get("previous_hash") != previous_hash:
            errors.append(f"{prefix} previous_hash mismatch")
        expected_hash = _event_hash(event)
        if event.get("event_hash") != expected_hash:
            errors.append(f"{prefix} event_hash mismatch")
        expected_hmac = _event_hmac(event, signing_key)
        if not hmac.compare_digest(str(event.get("event_hmac", "")), expected_hmac):
            errors.append(f"{prefix} event_hmac mismatch")

        event_type = event.get("event_type")
        recommendation_id = str(event.get("recommendation_id", ""))
        if not str(event.get("actor", "")).strip():
            errors.append(f"{prefix} actor must not be empty")
        if not recommendation_id:
            errors.append(f"{prefix} recommendation_id must not be empty")
        if event_type == "recommended":
            key = (str(event.get("family_id", "")), str(event.get("run_id", "")))
            if recommendation_id in recommendations:
                errors.append(f"{prefix} duplicates recommendation id {recommendation_id}")
            if key in family_runs:
                errors.append(f"{prefix} duplicates family/run recommendation {key[0]}/{key[1]}")
            if event.get("role") != "researcher":
                errors.append(f"{prefix} recommendation requires researcher role")
            if event.get("status") != "pending":
                errors.append(f"{prefix} recommendation status must be pending")
            _verify_evidence(event, prefix, errors)
            recommendations[recommendation_id] = event
            family_runs.add(key)
        elif event_type == "decided":
            recommendation = recommendations.get(recommendation_id)
            if recommendation is None:
                errors.append(f"{prefix} references missing recommendation {recommendation_id}")
            else:
                if recommendation_id in decisions:
                    errors.append(f"{prefix} duplicates decision for {recommendation_id}")
                if event.get("role") != "operator":
                    errors.append(f"{prefix} decision requires operator role")
                if event.get("actor") == recommendation.get("actor"):
                    errors.append(f"{prefix} decision actor must differ from recommendation actor")
                if event.get("status") not in DECISIONS:
                    errors.append(f"{prefix} decision status is invalid")
                for field in (
                    "family_id",
                    "hypothesis_id",
                    "candidate_id",
                    "run_id",
                    "evidence_path",
                    "evidence_sha256",
                ):
                    if event.get(field) != recommendation.get(field):
                        errors.append(f"{prefix} {field} does not match recommendation")
                decisions.add(recommendation_id)
        else:
            errors.append(f"{prefix} has unknown event_type")
        previous_hash = str(event.get("event_hash", ""))

    return PromotionLedgerVerification(
        valid=not errors,
        errors=errors,
        event_count=len(events),
        recommendation_count=len(recommendations),
        decision_count=len(decisions),
    )


def list_family_promotions(
    ledger_path: Path,
    *,
    signing_key: str,
) -> dict[str, object]:
    events = _verified_events(ledger_path, signing_key=signing_key)
    records: dict[str, dict[str, Any]] = {}
    for event in events:
        recommendation_id = str(event["recommendation_id"])
        if event["event_type"] == "recommended":
            records[recommendation_id] = {
                "recommendation_id": recommendation_id,
                "family_id": event["family_id"],
                "hypothesis_id": event["hypothesis_id"],
                "candidate_id": event["candidate_id"],
                "run_id": event["run_id"],
                "status": "pending",
                "researcher_actor": event["actor"],
                "operator_actor": None,
                "evidence_path": event["evidence_path"],
                "evidence_sha256": event["evidence_sha256"],
                "recommended_at": event["created_at"],
                "decided_at": None,
            }
        elif event["event_type"] == "decided":
            record = records[recommendation_id]
            record["status"] = event["status"]
            record["operator_actor"] = event["actor"]
            record["decided_at"] = event["created_at"]
    ordered = list(records.values())
    counts = {
        status: sum(record["status"] == status for record in ordered)
        for status in ("approved", "pending", "rejected")
    }
    return {
        "ledger_path": str(ledger_path),
        "counts": counts,
        "records": ordered,
    }


def promotion_ledger_verification_to_dict(
    verification: PromotionLedgerVerification,
) -> dict[str, object]:
    return {
        "valid": verification.valid,
        "errors": verification.errors,
        "event_count": verification.event_count,
        "recommendation_count": verification.recommendation_count,
        "decision_count": verification.decision_count,
    }


def _verified_events(
    ledger_path: Path,
    *,
    signing_key: str,
) -> list[dict[str, Any]]:
    if not ledger_path.exists():
        return []
    verification = verify_promotion_ledger(ledger_path, signing_key=signing_key)
    if not verification.valid:
        raise ValueError("family promotion ledger is invalid: " + "; ".join(verification.errors))
    return _load_events(ledger_path)


def _load_events(ledger_path: Path) -> list[dict[str, Any]]:
    if not ledger_path.exists():
        raise FileNotFoundError(ledger_path)
    events: list[dict[str, Any]] = []
    for index, line in enumerate(ledger_path.read_text(encoding="utf-8").splitlines()):
        if not line.strip():
            continue
        try:
            payload = json.loads(line)
        except json.JSONDecodeError as exc:
            raise ValueError(f"promotion ledger line {index + 1} is invalid JSON") from exc
        if not isinstance(payload, dict):
            raise ValueError(f"promotion ledger line {index + 1} must be an object")
        events.append(payload)
    return events


def _recommendation(events: list[dict[str, Any]], recommendation_id: str) -> dict[str, Any]:
    for event in events:
        if event.get("event_type") == "recommended" and event.get("recommendation_id") == recommendation_id:
            return event
    raise KeyError(f"family promotion recommendation not found: {recommendation_id}")


def _append_event(
    ledger_path: Path,
    event: dict[str, Any],
    *,
    previous_hash: str | None,
    signing_key: str,
) -> dict[str, Any]:
    payload = {**event, "previous_hash": previous_hash}
    payload["event_hash"] = _event_hash(payload)
    payload["event_hmac"] = _event_hmac(payload, signing_key)
    ledger_path.parent.mkdir(parents=True, exist_ok=True)
    with ledger_path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(payload, sort_keys=True) + "\n")
    return payload


def _event_hash(event: dict[str, Any]) -> str:
    payload = {
        key: value
        for key, value in event.items()
        if key not in {"event_hash", "event_hmac"}
    }
    return sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()


def _event_hmac(event: dict[str, Any], signing_key: str) -> str:
    payload = {key: value for key, value in event.items() if key != "event_hmac"}
    return hmac.new(
        signing_key.encode("utf-8"),
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8"),
        sha256,
    ).hexdigest()


def _verify_evidence(event: dict[str, Any], prefix: str, errors: list[str]) -> None:
    evidence_path = Path(str(event.get("evidence_path", "")))
    if not evidence_path.exists():
        errors.append(f"{prefix} evidence file is missing")
        return
    if _file_sha256(evidence_path) != event.get("evidence_sha256"):
        errors.append(f"{prefix} evidence sha256 mismatch")
        return
    try:
        evidence = json.loads(evidence_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        errors.append(f"{prefix} evidence is invalid JSON")
        return
    rows = evidence.get("rows") if isinstance(evidence, dict) else None
    selected = [
        row
        for row in rows or []
        if isinstance(row, dict) and row.get("run_id") == event.get("run_id")
    ]
    if len(selected) != 1 or selected[0].get("family_verdict") != "FAMILY_PROMOTE":
        errors.append(f"{prefix} evidence does not contain the selected FAMILY_PROMOTE row")
        return
    for field in ("family_id", "hypothesis_id", "candidate_id", "run_id"):
        if selected[0].get(field) != event.get(field):
            errors.append(f"{prefix} evidence {field} mismatch")


def _file_sha256(path: Path) -> str:
    return sha256(path.read_bytes()).hexdigest()


def _require_actor(actor: str) -> None:
    if not actor.strip():
        raise ValueError("promotion actor must not be empty")


def _require_signing_key(signing_key: str) -> None:
    if len(signing_key) < 16:
        raise ValueError("promotion ledger signing key must contain at least 16 characters")


@contextmanager
def _ledger_transaction(ledger_path: Path):
    lock_key = str(ledger_path.expanduser().resolve())
    with _LOCKS_GUARD:
        process_lock = _LOCKS.setdefault(lock_key, threading.RLock())
    with process_lock:
        lock_path = ledger_path.with_name(ledger_path.name + ".lock")
        lock_path.parent.mkdir(parents=True, exist_ok=True)
        with lock_path.open("a+", encoding="utf-8") as lock_file:
            if fcntl is not None:
                fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX)
            try:
                yield
            finally:
                if fcntl is not None:
                    fcntl.flock(lock_file.fileno(), fcntl.LOCK_UN)


def _now() -> str:
    return datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
