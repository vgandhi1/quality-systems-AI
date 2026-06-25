"""Tests for RCA escalation handoff builder."""

from __future__ import annotations

from warranty.handoff import build_escalation


def test_escalation_for_human_review() -> None:
    state = {
        "claim_id": "WAR-10452",
        "intake_findings": {
            "identified_parts": ["hybrid_battery_module"],
            "extracted_codes": ["P0A7F"],
            "total_cost": 4500,
        },
        "policy_evaluation": {"citation": "Hybrid battery covered."},
        "fraud_assessment": {"score": 12, "justification": "ok"},
        "decision": {"route": "HUMAN_REVIEW", "notify": "Cost threshold"},
    }
    escalation = build_escalation(state)
    assert escalation is not None
    assert escalation.claim_id == "WAR-10452"
    assert "hybrid battery module" in escalation.component
    assert "/quality/five-why" in escalation.target_endpoints


def test_no_escalation_for_auto_approve() -> None:
    state = {
        "claim_id": "WAR-1",
        "decision": {"route": "AUTO_APPROVE"},
        "intake_findings": {},
    }
    assert build_escalation(state) is None
