"""Contract tests: RcaEscalation (warranty) vs CLaimLens RcaHandoff boundaries."""

from __future__ import annotations

import json

import pytest
from pydantic import ValidationError

from warranty.handoff import build_escalation
from warranty.schema import RcaEscalation

# Fields that belong to CLaimLens batch narrative handoff — must never appear on RcaEscalation.
_CLAIMLENS_HANDOFF_FIELDS = frozenset({"anomaly_label", "claim_count", "share", "batch_id"})

_QUALITYMIND_CONSUMER_REQUIRED = frozenset({
    "problem_statement",
    "component",
    "claim_id",
    "decision_route",
    "target_endpoints",
})


def test_rca_escalation_json_schema_matches_qualitymind_contract() -> None:
    payload = RcaEscalation(
        problem_statement="Hybrid battery thermal event on claim WAR-10452.",
        component="hybrid battery module",
        claim_id="WAR-10452",
    )
    data = payload.model_dump()
    assert set(data.keys()) == _QUALITYMIND_CONSUMER_REQUIRED
    assert data["decision_route"] == "HUMAN_REVIEW"
    assert "/quality/five-why" in data["target_endpoints"]
    assert "/quality/draft-8d" in data["target_endpoints"]


def test_rca_escalation_rejects_claimlens_fields() -> None:
    with pytest.raises(ValidationError):
        RcaEscalation.model_validate({
            "problem_statement": "batch overcycle",
            "component": "brake rotor",
            "claim_id": "WAR-1",
            "anomaly_label": "overcycle",
            "claim_count": 42,
            "share": 0.18,
        })


def test_serialized_payload_has_no_claimlens_keys() -> None:
    escalation = build_escalation({
        "claim_id": "WAR-10452",
        "intake_findings": {
            "identified_parts": ["hybrid_battery_module"],
            "extracted_codes": ["P0A7F"],
            "total_cost": 4500,
        },
        "policy_evaluation": {"citation": "Hybrid battery covered."},
        "fraud_assessment": {"score": 12, "justification": "ok"},
        "decision": {"route": "HUMAN_REVIEW"},
    })
    assert escalation is not None
    raw = json.loads(escalation.model_dump_json())
    assert not _CLAIMLENS_HANDOFF_FIELDS.intersection(raw.keys())


def test_decision_route_is_literal_human_review_only() -> None:
    with pytest.raises(ValidationError):
        RcaEscalation(
            problem_statement="x",
            component="y",
            claim_id="WAR-1",
            decision_route="AUTO_APPROVE",  # type: ignore[arg-type]
        )


def test_round_trip_json_stable_for_http_consumer() -> None:
    original = RcaEscalation(
        problem_statement="Claim WAR-99001 escalated.",
        component="mass air flow sensor",
        claim_id="WAR-99001",
    )
    restored = RcaEscalation.model_validate_json(original.model_dump_json())
    assert restored == original
