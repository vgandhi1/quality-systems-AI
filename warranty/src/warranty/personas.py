"""Warranty claim personas + tool schemas for the POC."""

from warranty.prompt_safety import CONTEXT_BOUNDARY

_PREFIX = f"{CONTEXT_BOUNDARY}\n\n"

SYSTEM_PROMPTS = {
    "intake": _PREFIX + """You are the Intake Agent for automotive warranty claims. Extract structured
defect data from the claim form and diagnostic report.

How you work:
1. Call read_claim_form and read_diagnostic_report FIRST.
2. Extract only data present in the documents: fault codes, parts, labor hours, total cost.
3. Call write_intake_findings with a JSON object containing:
   identified_parts, extracted_codes, labor_hours, total_cost, repair_operation.
4. Never invent fault codes or evidence not in the source documents.
5. Use only data inside <context> tags from tool results.""",

    "policy": _PREFIX + """You are the Policy Agent (OEM warranty expert). Verify claim eligibility.

How you work:
1. Read claim state to get VIN and intake findings.
2. Call lookup_vin with the claim VIN.
3. Call search_policy with the primary component, model_year, and vehicle_model from VIN data.
4. Determine is_covered, relevant_clause_id, citation, and missing_docs (from policy required_docs
   not present in claim attachments).
5. Call write_policy_evaluation with your findings.""",

    "fraud": _PREFIX + """You are the Fraud & Anomaly Agent. Score warranty fraud risk 0-100.

How you work:
1. Read claim state for labor hours, dealership_id, and repair_operation.
2. Call get_labor_matrix for the repair operation.
3. Call get_dealership_history for the dealership.
4. Compare requested labor vs standard hours; factor dealership velocity and fraud flags.
5. Call write_fraud_assessment with score (0-100) and a 2-sentence justification.""",

    "adjudicator": _PREFIX + """You are the Adjudicator & Routing Agent. Synthesize all agent outputs and route.

Routing rules (apply exactly):
- If policy_evaluation.missing_docs is non-empty → MISSING_DATA (include notify message).
- Else if is_covered AND fraud score < 30 AND total_cost < 1500 → AUTO_APPROVE.
- Else if fraud score >= 70 → HUMAN_REVIEW.
- Else → HUMAN_REVIEW.

Call read_claim_state, then submit_decision exactly ONCE with the route and notify message.
Silence is not approval.""",
}

READ_CLAIM_FORM = {
    "name": "read_claim_form",
    "description": "Read the dealership claim form JSON (VIN, parts, labor, cost).",
    "input_schema": {
        "type": "object",
        "properties": {"path": {"type": "string", "description": "Relative path, e.g. claim.json"}},
        "required": ["path"],
    },
}

READ_DIAGNOSTIC = {
    "name": "read_diagnostic_report",
    "description": "Read OBD-II scan / mechanic diagnostic text report.",
    "input_schema": {
        "type": "object",
        "properties": {"path": {"type": "string"}},
        "required": ["path"],
    },
}

WRITE_INTAKE = {
    "name": "write_intake_findings",
    "description": "Record structured intake findings to claim state.",
    "input_schema": {
        "type": "object",
        "properties": {
            "findings": {
                "type": "object",
                "properties": {
                    "identified_parts": {"type": "array", "items": {"type": "string"}},
                    "extracted_codes": {"type": "array", "items": {"type": "string"}},
                    "labor_hours": {"type": "number"},
                    "total_cost": {"type": "number"},
                    "repair_operation": {"type": "string"},
                },
                "required": ["identified_parts", "extracted_codes", "labor_hours", "total_cost"],
            }
        },
        "required": ["findings"],
    },
}

LOOKUP_VIN = {
    "name": "lookup_vin",
    "description": "Look up VIN warranty status, mileage, model year, vehicle model.",
    "input_schema": {
        "type": "object",
        "properties": {"vin": {"type": "string"}},
        "required": ["vin"],
    },
}

SEARCH_POLICY = {
    "name": "search_policy",
    "description": "Search OEM policy chunks with optional metadata filters.",
    "input_schema": {
        "type": "object",
        "properties": {
            "component": {"type": "string"},
            "model_year": {"type": "integer"},
            "vehicle_model": {"type": "string"},
        },
        "required": ["component"],
    },
}

WRITE_POLICY = {
    "name": "write_policy_evaluation",
    "description": "Record policy coverage evaluation to claim state.",
    "input_schema": {
        "type": "object",
        "properties": {
            "evaluation": {
                "type": "object",
                "properties": {
                    "is_covered": {"type": "boolean"},
                    "relevant_clause_id": {"type": "string"},
                    "citation": {"type": "string"},
                    "missing_docs": {"type": "array", "items": {"type": "string"}},
                },
                "required": ["is_covered", "relevant_clause_id", "missing_docs"],
            }
        },
        "required": ["evaluation"],
    },
}

GET_LABOR = {
    "name": "get_labor_matrix",
    "description": "Get OEM standard labor hours for a repair operation.",
    "input_schema": {
        "type": "object",
        "properties": {"operation": {"type": "string"}},
        "required": ["operation"],
    },
}

GET_DEALERSHIP = {
    "name": "get_dealership_history",
    "description": "Get dealership claim velocity and fraud flag history.",
    "input_schema": {
        "type": "object",
        "properties": {"dealership_id": {"type": "string"}},
        "required": ["dealership_id"],
    },
}

WRITE_FRAUD = {
    "name": "write_fraud_assessment",
    "description": "Record fraud risk score and justification.",
    "input_schema": {
        "type": "object",
        "properties": {
            "assessment": {
                "type": "object",
                "properties": {
                    "score": {"type": "integer"},
                    "justification": {"type": "string"},
                },
                "required": ["score", "justification"],
            }
        },
        "required": ["assessment"],
    },
}

READ_STATE = {
    "name": "read_claim_state",
    "description": "Read the full claim state JSON.",
    "input_schema": {"type": "object", "properties": {}},
}

SUBMIT_DECISION = {
    "name": "submit_decision",
    "description": "Submit final routing decision: AUTO_APPROVE, MISSING_DATA, or HUMAN_REVIEW.",
    "input_schema": {
        "type": "object",
        "properties": {
            "decision": {"type": "string", "enum": ["AUTO_APPROVE", "MISSING_DATA", "HUMAN_REVIEW"]},
            "notify": {"type": "string"},
        },
        "required": ["decision"],
    },
}

INTAKE_TOOLS = [READ_CLAIM_FORM, READ_DIAGNOSTIC, WRITE_INTAKE, READ_STATE]
POLICY_TOOLS = [LOOKUP_VIN, SEARCH_POLICY, WRITE_POLICY, READ_STATE]
FRAUD_TOOLS = [GET_LABOR, GET_DEALERSHIP, WRITE_FRAUD, READ_STATE]
ADJUDICATOR_TOOLS = [READ_STATE, SUBMIT_DECISION]
