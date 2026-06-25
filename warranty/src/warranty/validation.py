"""Structural validators and authoritative routing gate for warranty agents."""

from __future__ import annotations

from pydantic import ValidationError

from warranty.schema import (
    ClaimDecision,
    DecisionRoute,
    FraudAssessment,
    IntakeFindings,
    PolicyEvaluation,
)

AUTO_APPROVE_COST_LIMIT = 1500
AUTO_APPROVE_FRAUD_MAX = 30
HUMAN_REVIEW_FRAUD_MIN = 70


def _format_error(exc: ValidationError) -> str:
    return "; ".join(f"{'.'.join(str(p) for p in e['loc'])}: {e['msg']}" for e in exc.errors())


def validate_intake(data: dict) -> tuple[IntakeFindings | None, str | None]:
    try:
        return IntakeFindings.model_validate(data), None
    except ValidationError as exc:
        return None, _format_error(exc)


def validate_policy(data: dict) -> tuple[PolicyEvaluation | None, str | None]:
    try:
        return PolicyEvaluation.model_validate(data), None
    except ValidationError as exc:
        return None, _format_error(exc)


def validate_fraud(data: dict) -> tuple[FraudAssessment | None, str | None]:
    try:
        return FraudAssessment.model_validate(data), None
    except ValidationError as exc:
        return None, _format_error(exc)


def route_claim(
    policy: dict,
    fraud: dict,
    intake: dict,
) -> tuple[ClaimDecision | None, str | None]:
    """Authoritative routing gate — mirrors adjudicator rules in personas.py."""
    policy_v, policy_err = validate_policy(policy)
    if policy_err:
        return None, f"policy: {policy_err}"
    fraud_v, fraud_err = validate_fraud(fraud)
    if fraud_err:
        return None, f"fraud: {fraud_err}"
    intake_v, intake_err = validate_intake(intake)
    if intake_err:
        return None, f"intake: {intake_err}"

    missing = policy_v.missing_docs
    if missing:
        return ClaimDecision(
            route=DecisionRoute.MISSING_DATA,
            notify=f"Please upload: {', '.join(missing)}",
        ), None

    if fraud_v.score >= HUMAN_REVIEW_FRAUD_MIN:
        return ClaimDecision(
            route=DecisionRoute.HUMAN_REVIEW,
            notify="Elevated fraud risk",
        ), None

    if (
        policy_v.is_covered
        and fraud_v.score < AUTO_APPROVE_FRAUD_MAX
        and intake_v.total_cost < AUTO_APPROVE_COST_LIMIT
    ):
        return ClaimDecision(
            route=DecisionRoute.AUTO_APPROVE,
            notify="Payment authorized",
        ), None

    return ClaimDecision(
        route=DecisionRoute.HUMAN_REVIEW,
        notify="Cost or confidence threshold exceeded",
    ), None
