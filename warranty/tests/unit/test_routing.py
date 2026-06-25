"""Tests for authoritative routing gate thresholds."""

from __future__ import annotations

from warranty.schema import DecisionRoute
from warranty.validation import (
    AUTO_APPROVE_COST_LIMIT,
    AUTO_APPROVE_FRAUD_MAX,
    HUMAN_REVIEW_FRAUD_MIN,
    route_claim,
)


def _base_intake(cost: float = 320.0) -> dict:
    return {
        "identified_parts": ["maf"],
        "extracted_codes": ["P0101"],
        "labor_hours": 0.8,
        "total_cost": cost,
        "repair_operation": "maf_sensor_replace",
    }


def _base_policy(*, covered: bool = True, missing: list[str] | None = None) -> dict:
    if not covered:
        return {
            "is_covered": False,
            "relevant_clause_id": "NONE",
            "citation": "",
            "missing_docs": missing or [],
        }
    return {
        "is_covered": True,
        "relevant_clause_id": "SB-1",
        "citation": "Covered under emissions warranty.",
        "missing_docs": missing or [],
    }


def _base_fraud(score: int = 10) -> dict:
    return {"score": score, "justification": "Within normal variance."}


def test_missing_docs_routes_to_missing_data() -> None:
    decision, err = route_claim(
        _base_policy(missing=["battery_cell_voltage_logs"]),
        _base_fraud(),
        _base_intake(),
    )
    assert err is None
    assert decision is not None
    assert decision.route == DecisionRoute.MISSING_DATA
    assert "battery_cell_voltage_logs" in decision.notify


def test_auto_approve_within_thresholds() -> None:
    decision, err = route_claim(_base_policy(), _base_fraud(20), _base_intake(320))
    assert err is None
    assert decision is not None
    assert decision.route == DecisionRoute.AUTO_APPROVE


def test_high_fraud_forces_human_review() -> None:
    decision, err = route_claim(_base_policy(), _base_fraud(HUMAN_REVIEW_FRAUD_MIN), _base_intake())
    assert err is None
    assert decision is not None
    assert decision.route == DecisionRoute.HUMAN_REVIEW
    assert "fraud" in decision.notify.lower()


def test_high_cost_forces_human_review() -> None:
    decision, err = route_claim(
        _base_policy(),
        _base_fraud(AUTO_APPROVE_FRAUD_MAX - 1),
        _base_intake(AUTO_APPROVE_COST_LIMIT),
    )
    assert err is None
    assert decision is not None
    assert decision.route == DecisionRoute.HUMAN_REVIEW


def test_fraud_at_auto_approve_boundary() -> None:
    decision, err = route_claim(
        _base_policy(),
        _base_fraud(AUTO_APPROVE_FRAUD_MAX),
        _base_intake(AUTO_APPROVE_COST_LIMIT - 1),
    )
    assert err is None
    assert decision is not None
    assert decision.route == DecisionRoute.HUMAN_REVIEW


def test_incomplete_state_returns_error() -> None:
    decision, err = route_claim(_base_policy(), _base_fraud(), {})
    assert decision is None
    assert err is not None
    assert "intake" in err
