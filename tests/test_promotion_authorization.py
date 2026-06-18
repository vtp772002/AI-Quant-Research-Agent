from __future__ import annotations

import json
import time
from concurrent.futures import ThreadPoolExecutor
from hashlib import sha256
from pathlib import Path

import pytest


SIGNING_KEY = "test-promotion-signing-key"


def test_recommend_and_approve_family_promotion_writes_verifiable_two_person_ledger(tmp_path: Path):
    try:
        from quant_research_agent.promotion_authorization import (
            decide_family_promotion,
            list_family_promotions,
            recommend_family_promotion,
            verify_promotion_ledger,
        )
    except ModuleNotFoundError:
        pytest.fail("promotion authorization boundary is not implemented")

    runs_dir = tmp_path / "runs"
    _write_family_manifest(runs_dir / "candidate" / "manifest.json")
    ledger_path = tmp_path / "promotions" / "promotion_ledger.jsonl"

    recommendation = recommend_family_promotion(
        source_path=runs_dir,
        family_id="family-a",
        run_id="candidate-run",
        ledger_path=ledger_path,
        actor="researcher-alice",
        role="researcher",
        signing_key=SIGNING_KEY,
        note="Recommend after independent research review.",
    )
    decision = decide_family_promotion(
        ledger_path=ledger_path,
        recommendation_id=recommendation["recommendation_id"],
        decision="approved",
        actor="operator-bob",
        role="operator",
        signing_key=SIGNING_KEY,
        note="Approved for the next research stage.",
    )
    verification = verify_promotion_ledger(ledger_path, signing_key=SIGNING_KEY)
    summary = list_family_promotions(ledger_path, signing_key=SIGNING_KEY)

    assert recommendation["status"] == "pending"
    assert Path(recommendation["evidence_path"]).exists()
    assert decision["status"] == "approved"
    assert verification.valid
    assert verification.errors == []
    assert summary["counts"] == {"approved": 1, "pending": 0, "rejected": 0}
    assert summary["records"][0]["researcher_actor"] == "researcher-alice"
    assert summary["records"][0]["operator_actor"] == "operator-bob"


def test_recommend_family_promotion_rejects_non_promote_evidence(tmp_path: Path):
    from quant_research_agent.promotion_authorization import recommend_family_promotion

    manifest_path = tmp_path / "runs" / "candidate" / "manifest.json"
    _write_family_manifest(manifest_path, run_verdict="REJECT")

    with pytest.raises(ValueError, match="requires FAMILY_PROMOTE evidence"):
        recommend_family_promotion(
            source_path=manifest_path,
            family_id="family-a",
            run_id="candidate-run",
            ledger_path=tmp_path / "promotions.jsonl",
            actor="researcher-alice",
            role="researcher",
            signing_key=SIGNING_KEY,
        )


def test_promotion_roles_actor_separation_and_single_decision_fail_closed(tmp_path: Path):
    from quant_research_agent.promotion_authorization import (
        decide_family_promotion,
        recommend_family_promotion,
    )

    manifest_path = tmp_path / "runs" / "candidate" / "manifest.json"
    _write_family_manifest(manifest_path)
    ledger_path = tmp_path / "promotion_ledger.jsonl"

    with pytest.raises(PermissionError, match="requires researcher role"):
        recommend_family_promotion(
            source_path=manifest_path,
            family_id="family-a",
            run_id="candidate-run",
            ledger_path=ledger_path,
            actor="operator-bob",
            role="operator",
            signing_key=SIGNING_KEY,
        )

    recommendation = recommend_family_promotion(
        source_path=manifest_path,
        family_id="family-a",
        run_id="candidate-run",
        ledger_path=ledger_path,
        actor="researcher-alice",
        role="researcher",
        signing_key=SIGNING_KEY,
    )

    with pytest.raises(PermissionError, match="requires operator role"):
        decide_family_promotion(
            ledger_path=ledger_path,
            recommendation_id=recommendation["recommendation_id"],
            decision="approved",
            actor="researcher-carol",
            role="researcher",
            signing_key=SIGNING_KEY,
        )
    with pytest.raises(PermissionError, match="must differ"):
        decide_family_promotion(
            ledger_path=ledger_path,
            recommendation_id=recommendation["recommendation_id"],
            decision="approved",
            actor="researcher-alice",
            role="operator",
            signing_key=SIGNING_KEY,
        )

    decide_family_promotion(
        ledger_path=ledger_path,
        recommendation_id=recommendation["recommendation_id"],
        decision="rejected",
        actor="operator-bob",
        role="operator",
        signing_key=SIGNING_KEY,
    )
    with pytest.raises(ValueError, match="already decided"):
        decide_family_promotion(
            ledger_path=ledger_path,
            recommendation_id=recommendation["recommendation_id"],
            decision="approved",
            actor="operator-carol",
            role="operator",
            signing_key=SIGNING_KEY,
        )


def test_verify_promotion_ledger_detects_event_and_evidence_tampering(tmp_path: Path):
    from quant_research_agent.promotion_authorization import (
        recommend_family_promotion,
        verify_promotion_ledger,
    )

    manifest_path = tmp_path / "runs" / "candidate" / "manifest.json"
    _write_family_manifest(manifest_path)
    ledger_path = tmp_path / "promotion_ledger.jsonl"
    recommendation = recommend_family_promotion(
        source_path=manifest_path,
        family_id="family-a",
        run_id="candidate-run",
        ledger_path=ledger_path,
        actor="researcher-alice",
        role="researcher",
        signing_key=SIGNING_KEY,
    )

    evidence_path = Path(recommendation["evidence_path"])
    evidence = json.loads(evidence_path.read_text(encoding="utf-8"))
    evidence["rows"][0]["family_verdict"] = "FAMILY_REJECT"
    evidence_path.write_text(json.dumps(evidence, sort_keys=True), encoding="utf-8")

    evidence_verification = verify_promotion_ledger(
        ledger_path,
        signing_key=SIGNING_KEY,
    )

    assert not evidence_verification.valid
    assert any("evidence sha256 mismatch" in error for error in evidence_verification.errors)

    event = json.loads(ledger_path.read_text(encoding="utf-8"))
    event["actor"] = "tampered-actor"
    ledger_path.write_text(json.dumps(event, sort_keys=True) + "\n", encoding="utf-8")

    event_verification = verify_promotion_ledger(
        ledger_path,
        signing_key=SIGNING_KEY,
    )

    assert not event_verification.valid
    assert any("event_hash mismatch" in error for error in event_verification.errors)


def test_verify_promotion_ledger_returns_invalid_result_for_malformed_json(tmp_path: Path):
    from quant_research_agent.promotion_authorization import verify_promotion_ledger

    ledger_path = tmp_path / "promotion_ledger.jsonl"
    ledger_path.write_text("{not-json}\n", encoding="utf-8")

    verification = verify_promotion_ledger(ledger_path, signing_key=SIGNING_KEY)

    assert not verification.valid
    assert verification.event_count == 0
    assert verification.errors == ["promotion ledger line 1 is invalid JSON"]


def test_verify_promotion_ledger_rejects_rehashed_business_invariant_forgery(tmp_path: Path):
    from quant_research_agent.promotion_authorization import (
        recommend_family_promotion,
        verify_promotion_ledger,
    )

    manifest_path = tmp_path / "runs" / "candidate" / "manifest.json"
    _write_family_manifest(manifest_path)
    ledger_path = tmp_path / "promotion_ledger.jsonl"
    recommend_family_promotion(
        source_path=manifest_path,
        family_id="family-a",
        run_id="candidate-run",
        ledger_path=ledger_path,
        actor="researcher-alice",
        role="researcher",
        signing_key=SIGNING_KEY,
    )
    event = json.loads(ledger_path.read_text(encoding="utf-8"))
    event["actor"] = " "
    event["hypothesis_id"] = "forged-hypothesis"
    event["candidate_id"] = "forged-candidate"
    event["event_hash"] = _event_hash(event)
    ledger_path.write_text(json.dumps(event, sort_keys=True) + "\n", encoding="utf-8")

    verification = verify_promotion_ledger(ledger_path, signing_key=SIGNING_KEY)

    assert not verification.valid
    assert any("actor must not be empty" in error for error in verification.errors)
    assert any("evidence hypothesis_id mismatch" in error for error in verification.errors)
    assert any("evidence candidate_id mismatch" in error for error in verification.errors)


def test_verify_promotion_ledger_rejects_rehashed_event_without_valid_hmac(tmp_path: Path):
    from quant_research_agent.promotion_authorization import (
        decide_family_promotion,
        recommend_family_promotion,
        verify_promotion_ledger,
    )

    signing_key = "test-ledger-signing-key"
    manifest_path = tmp_path / "runs" / "candidate" / "manifest.json"
    _write_family_manifest(manifest_path)
    ledger_path = tmp_path / "promotion_ledger.jsonl"
    recommendation = recommend_family_promotion(
        source_path=manifest_path,
        family_id="family-a",
        run_id="candidate-run",
        ledger_path=ledger_path,
        actor="researcher-alice",
        role="researcher",
        signing_key=signing_key,
    )
    decide_family_promotion(
        ledger_path=ledger_path,
        recommendation_id=recommendation["recommendation_id"],
        decision="approved",
        actor="operator-bob",
        role="operator",
        signing_key=signing_key,
    )
    events = [
        json.loads(line)
        for line in ledger_path.read_text(encoding="utf-8").splitlines()
    ]
    events[1]["status"] = "rejected"
    events[1]["event_hash"] = _event_hash(events[1])
    ledger_path.write_text(
        "\n".join(json.dumps(event, sort_keys=True) for event in events) + "\n",
        encoding="utf-8",
    )

    verification = verify_promotion_ledger(ledger_path, signing_key=signing_key)

    assert not verification.valid
    assert any("event_hmac mismatch" in error for error in verification.errors)


def test_concurrent_family_promotion_decisions_serialize_read_check_append(
    monkeypatch,
    tmp_path: Path,
):
    import quant_research_agent.promotion_authorization as authorization

    manifest_path = tmp_path / "runs" / "candidate" / "manifest.json"
    _write_family_manifest(manifest_path)
    ledger_path = tmp_path / "promotion_ledger.jsonl"
    recommendation = authorization.recommend_family_promotion(
        source_path=manifest_path,
        family_id="family-a",
        run_id="candidate-run",
        ledger_path=ledger_path,
        actor="researcher-alice",
        role="researcher",
        signing_key=SIGNING_KEY,
    )
    original_append = authorization._append_event

    def delayed_append(*args, **kwargs):
        time.sleep(0.05)
        return original_append(*args, **kwargs)

    monkeypatch.setattr(authorization, "_append_event", delayed_append)

    def decide(actor: str) -> str:
        try:
            authorization.decide_family_promotion(
                ledger_path=ledger_path,
                recommendation_id=recommendation["recommendation_id"],
                decision="approved",
                actor=actor,
                role="operator",
                signing_key=SIGNING_KEY,
            )
        except ValueError:
            return "rejected"
        return "approved"

    with ThreadPoolExecutor(max_workers=2) as executor:
        results = list(executor.map(decide, ["operator-bob", "operator-carol"]))

    verification = authorization.verify_promotion_ledger(
        ledger_path,
        signing_key=SIGNING_KEY,
    )

    assert sorted(results) == ["approved", "rejected"]
    assert verification.valid
    assert verification.decision_count == 1


def test_family_promotion_cli_recommend_list_decide_and_verify(
    monkeypatch,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
):
    from quant_research_agent.main import main

    monkeypatch.setenv("AIQRA_PROMOTION_LEDGER_HMAC_KEY", SIGNING_KEY)
    runs_dir = tmp_path / "runs"
    _write_family_manifest(runs_dir / "candidate" / "manifest.json")
    ledger_path = tmp_path / "promotions" / "promotion_ledger.jsonl"

    recommend_code = main(
        [
            "--recommend-family-promotion",
            str(runs_dir),
            "--promotion-family-id",
            "family-a",
            "--promotion-run-id",
            "candidate-run",
            "--promotion-ledger",
            str(ledger_path),
            "--promotion-actor",
            "researcher-alice",
            "--promotion-role",
            "researcher",
            "--promotion-note",
            "Recommend through CLI.",
        ]
    )
    recommendation = json.loads(capsys.readouterr().out)
    list_code = main(["--list-family-promotions", str(ledger_path)])
    listed = json.loads(capsys.readouterr().out)
    decide_code = main(
        [
            "--decide-family-promotion",
            recommendation["recommendation_id"],
            "--promotion-ledger",
            str(ledger_path),
            "--promotion-decision",
            "approved",
            "--promotion-actor",
            "operator-bob",
            "--promotion-role",
            "operator",
        ]
    )
    decision = json.loads(capsys.readouterr().out)
    verify_code = main(["--verify-promotion-ledger", str(ledger_path)])
    verification = json.loads(capsys.readouterr().out)

    assert recommend_code == list_code == decide_code == verify_code == 0
    assert recommendation["status"] == "pending"
    assert listed["counts"]["pending"] == 1
    assert decision["status"] == "approved"
    assert verification["valid"] is True
    assert verification["decision_count"] == 1


def _write_family_manifest(
    path: Path,
    *,
    run_id: str = "candidate-run",
    family_id: str = "family-a",
    candidate_id: str = "candidate-a",
    selection_policy: str = "pre_registered",
    run_verdict: str = "PROMOTE",
    p_value: float = 0.01,
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(
            {
                "run_id": run_id,
                "generated_at": "2026-06-18T00:00:00Z",
                "experiment": "promotion_test",
                "config": {"sha256": "config-a"},
                "code": {"commit": "deadbeef", "dirty": False},
                "data": {"source": "synthetic", "snapshot_dataset_id": None},
                "experiment_family": {
                    "family_id": family_id,
                    "hypothesis_id": "hypothesis-a",
                    "candidate_id": candidate_id,
                    "selection_policy": selection_policy,
                },
                "metrics": {
                    "holdout": {
                        "ic_mean": 0.05,
                        "sharpe": 1.25,
                        "total_return": 0.10,
                    },
                    "research_validity": {
                        "verdict": run_verdict,
                        "candidates": [
                            {
                                "name": "agent_signal",
                                "holdout_ic_mean": 0.05,
                                "holdout_sharpe": 1.25,
                                "holdout_total_return": 0.10,
                                "p_value": p_value,
                                "q_value": p_value,
                            }
                        ],
                    },
                },
            },
            indent=2,
            sort_keys=True,
        ),
        encoding="utf-8",
    )


def _event_hash(event: dict[str, object]) -> str:
    payload = {
        key: value
        for key, value in event.items()
        if key not in {"event_hash", "event_hmac"}
    }
    return sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
