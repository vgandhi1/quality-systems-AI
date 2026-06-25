"""Pydantic contracts for warranty claim agent inputs and structured outputs."""

from __future__ import annotations

from enum import Enum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class DecisionRoute(str, Enum):
    AUTO_APPROVE = "AUTO_APPROVE"
    MISSING_DATA = "MISSING_DATA"
    HUMAN_REVIEW = "HUMAN_REVIEW"


class IntakeFindings(BaseModel):
    """Structured defect data extracted by the Intake Agent."""

    identified_parts: list[str]
    extracted_codes: list[str] = Field(..., min_length=1)
    labor_hours: float = Field(..., gt=0)
    total_cost: float = Field(..., ge=0)
    repair_operation: str = "unknown"


class PolicyEvaluation(BaseModel):
    """Coverage decision from the Policy Agent."""

    is_covered: bool
    relevant_clause_id: str
    citation: str = ""
    missing_docs: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def covered_requires_citation(self) -> PolicyEvaluation:
        if self.is_covered:
            if not self.relevant_clause_id or self.relevant_clause_id == "NONE":
                raise ValueError("covered claims require a valid relevant_clause_id")
            if not self.citation.strip():
                raise ValueError("covered claims require a policy citation")
        return self


class FraudAssessment(BaseModel):
    """Fraud risk score from the Fraud Agent."""

    score: int = Field(..., ge=0, le=100)
    justification: str = Field(..., min_length=1)


class ClaimDecision(BaseModel):
    """Final routing decision from the Adjudicator gate."""

    route: DecisionRoute
    notify: str = ""


class ClaimState(BaseModel):
    """Durable claim state persisted between agent stages."""

    claim_id: str
    dealership_id: str
    vin_data: dict = Field(default_factory=dict)
    intake_findings: dict = Field(default_factory=dict)
    policy_evaluation: dict = Field(default_factory=dict)
    fraud_assessment: dict = Field(default_factory=dict)
    decision: dict | None = None
    status: str = "IN_PROGRESS"
    audit_trail: list[str] = Field(default_factory=list)


class RcaEscalation(BaseModel):
    """QualityMind-RAG-ready payload when adjudicator routes to HUMAN_REVIEW.

    Cross-project contract (warranty → QualityMind). Not the CLaimLens RcaHandoff
    schema — no anomaly_label or batch Pareto fields.
    """

    model_config = ConfigDict(extra="forbid")

    problem_statement: str
    component: str
    claim_id: str
    decision_route: Literal["HUMAN_REVIEW"] = "HUMAN_REVIEW"
    target_endpoints: list[str] = Field(
        default_factory=lambda: ["/quality/five-why", "/quality/draft-8d"]
    )


class RcaEscalationResponse(RcaEscalation):
    """Escalation payload optionally enriched with a live QualityMind response."""

    qualitymind_response: dict | None = None


class DryRunRequest(BaseModel):
    """API request to run a deterministic adjudication scenario."""

    scenario: Literal["auto_approve", "missing_logs", "missing_logs_resumed"] = "auto_approve"


class AdjudicateResponse(BaseModel):
    """API response with final claim state and optional RCA escalation."""

    claim_state: dict
    escalation: RcaEscalation | None = None
