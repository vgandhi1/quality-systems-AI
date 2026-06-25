"""Build QualityMind-ready RCA escalation from adjudicated claim state."""

from __future__ import annotations

from warranty.schema import DecisionRoute, RcaEscalation


def build_escalation(claim_state: dict) -> RcaEscalation | None:
    """Return an RCA escalation payload when the claim routed to HUMAN_REVIEW.

    Returns None for AUTO_APPROVE, MISSING_DATA, or incomplete state.
    """
    decision = claim_state.get("decision") or {}
    route = decision.get("route")
    if route != DecisionRoute.HUMAN_REVIEW.value:
        return None

    intake = claim_state.get("intake_findings") or {}
    policy = claim_state.get("policy_evaluation") or {}
    fraud = claim_state.get("fraud_assessment") or {}

    parts = intake.get("identified_parts") or []
    component = parts[0].replace("_", " ") if parts else "unknown component"
    codes = ", ".join(intake.get("extracted_codes") or [])
    claim_id = claim_state.get("claim_id", "UNKNOWN")
    cost = intake.get("total_cost", 0)
    fraud_score = fraud.get("score", 0)
    citation = policy.get("citation", "")

    problem_statement = (
        f"Warranty claim {claim_id} escalated for engineering review: "
        f"{component} failure (DTC {codes or 'n/a'}), "
        f"cost ${cost:,.0f}, fraud score {fraud_score}."
    )
    if citation:
        problem_statement += f" Policy: {citation[:200]}"

    return RcaEscalation(
        problem_statement=problem_statement,
        component=component,
        claim_id=claim_id,
    )
