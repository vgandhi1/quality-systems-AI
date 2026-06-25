"""Tests for Pydantic schema and validation helpers."""

from __future__ import annotations

import pytest

from warranty.schema import DecisionRoute, FraudAssessment, IntakeFindings, PolicyEvaluation
from warranty.validation import validate_fraud, validate_intake, validate_policy


def test_intake_valid() -> None:
    model, err = validate_intake(
        {
            "identified_parts": ["maf"],
            "extracted_codes": ["P0101"],
            "labor_hours": 0.8,
            "total_cost": 320,
        }
    )
    assert err is None
    assert isinstance(model, IntakeFindings)


def test_intake_rejects_missing_codes() -> None:
    _, err = validate_intake(
        {
            "identified_parts": ["maf"],
            "extracted_codes": [],
            "labor_hours": 0.8,
            "total_cost": 320,
        }
    )
    assert err is not None


def test_policy_covered_requires_citation() -> None:
    with pytest.raises(ValueError, match="citation"):
        PolicyEvaluation(
            is_covered=True,
            relevant_clause_id="SB-1",
            citation="",
            missing_docs=[],
        )


def test_policy_not_covered_allows_empty_citation() -> None:
    model, err = validate_policy(
        {
            "is_covered": False,
            "relevant_clause_id": "NONE",
            "citation": "",
            "missing_docs": [],
        }
    )
    assert err is None
    assert model is not None
    assert model.is_covered is False


def test_fraud_score_bounds() -> None:
    _, err = validate_fraud({"score": -1, "justification": "bad"})
    assert err is not None
    model, err = validate_fraud({"score": 50, "justification": "ok"})
    assert err is None
    assert isinstance(model, FraudAssessment)


def test_decision_route_enum() -> None:
    assert DecisionRoute.AUTO_APPROVE.value == "AUTO_APPROVE"
