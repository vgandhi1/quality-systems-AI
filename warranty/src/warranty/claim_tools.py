"""Warranty claim tool layer — sandboxed VIN lookup, policy search, claim state."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from warranty.policy_search import get_policy_search_backend
from warranty.validation import (
    AUTO_APPROVE_COST_LIMIT,
    AUTO_APPROVE_FRAUD_MAX,
    HUMAN_REVIEW_FRAUD_MIN,
    route_claim,
    validate_fraud,
    validate_intake,
    validate_policy,
)

_SAFE_REL = re.compile(r"^[A-Za-z0-9._\-/ ]+$")

STATE_FILE = ".claim_state.json"

__all__ = [
    "AUTO_APPROVE_COST_LIMIT",
    "AUTO_APPROVE_FRAUD_MAX",
    "ClaimStore",
    "HUMAN_REVIEW_FRAUD_MIN",
    "STATE_FILE",
]


class ClaimStore:
    """Sandbox a directory and expose warranty claim operations."""

    def __init__(self, root: str | Path) -> None:
        self.root = Path(root).resolve()
        self.root.mkdir(parents=True, exist_ok=True)
        self._policy_search = get_policy_search_backend()

    def _resolve(self, relative_path: str) -> Path:
        if not relative_path or not isinstance(relative_path, str):
            raise ValueError("Invalid path")
        if not _SAFE_REL.match(relative_path):
            raise ValueError("Path must be a safe relative path under the claim root")
        p = Path(relative_path)
        if p.is_absolute() or ".." in p.parts:
            raise ValueError("Path traversal not allowed")
        full = (self.root / p).resolve()
        if full != self.root:
            try:
                full.relative_to(self.root)
            except ValueError as e:
                raise ValueError("Path escapes the claim root") from e
        return full

    def _load_json(self, path: str) -> Any:
        full = self._resolve(path)
        if not full.exists():
            return None
        return json.loads(full.read_text(encoding="utf-8"))

    def _save_json(self, path: str, data: Any) -> None:
        full = self._resolve(path)
        full.parent.mkdir(parents=True, exist_ok=True)
        full.write_text(json.dumps(data, indent=2), encoding="utf-8")

    def read_claim_form(self, path: str) -> str:
        data = self._load_json(path)
        if data is None:
            return f"[File not found: {path}]"
        return json.dumps(data, indent=2)

    def read_diagnostic_report(self, path: str) -> str:
        full = self._resolve(path)
        if not full.exists():
            return f"[File not found: {path}]"
        return full.read_text(encoding="utf-8")

    def lookup_vin(self, vin: str) -> str:
        registry = self._load_json("vin_registry.json") or {}
        record = registry.get(vin)
        if not record:
            return json.dumps({"error": f"VIN not found: {vin[:8]}..."})
        return json.dumps(record, indent=2)

    def search_policy(
        self,
        component: str,
        model_year: int | None = None,
        vehicle_model: str | None = None,
    ) -> str:
        manual = self._load_json("policy_manual.json") or {"chunks": []}
        hits = self._policy_search.search(manual, component, model_year, vehicle_model)
        if not hits:
            return json.dumps({"matches": [], "note": f"No policy chunks for component={component}"})
        return json.dumps({"matches": hits}, indent=2)

    def get_labor_matrix(self, operation: str) -> str:
        matrix = self._load_json("labor_matrix.json") or {}
        entry = matrix.get(operation)
        if not entry:
            return json.dumps({"error": f"Unknown operation: {operation}", "known": list(matrix.keys())})
        return json.dumps(entry, indent=2)

    def get_dealership_history(self, dealership_id: str) -> str:
        history = self._load_json("dealership_history.json") or {}
        entry = history.get(dealership_id)
        if not entry:
            return json.dumps({"dealership_id": dealership_id, "claims_30d": 0, "fraud_flags": 0})
        return json.dumps(entry, indent=2)

    def read_claim_state(self) -> str:
        data = self._load_json(STATE_FILE)
        if not data:
            return json.dumps({"status": "NOT_INITIALIZED"})
        return json.dumps(data, indent=2)

    def init_claim_state(self, claim_id: str, dealership_id: str, vin: str) -> str:
        vin_data = json.loads(self.lookup_vin(vin))
        state = {
            "claim_id": claim_id,
            "dealership_id": dealership_id,
            "vin_data": vin_data if "error" not in vin_data else {"vin": vin},
            "intake_findings": {},
            "policy_evaluation": {},
            "fraud_assessment": {},
            "decision": None,
            "status": "IN_PROGRESS",
            "audit_trail": ["initialized"],
        }
        self._save_json(STATE_FILE, state)
        return f"Claim state initialized: {claim_id}"

    def write_intake_findings(self, findings: dict) -> str:
        validated, err = validate_intake(findings)
        if err:
            return f"[error] invalid intake findings: {err}"
        state = self._load_json(STATE_FILE) or {}
        state["intake_findings"] = validated.model_dump()
        state.setdefault("audit_trail", []).append("intake_done")
        self._save_json(STATE_FILE, state)
        return "Intake findings recorded."

    def write_policy_evaluation(self, evaluation: dict) -> str:
        validated, err = validate_policy(evaluation)
        if err:
            return f"[error] invalid policy evaluation: {err}"
        state = self._load_json(STATE_FILE) or {}
        state["policy_evaluation"] = validated.model_dump()
        state.setdefault("audit_trail", []).append("policy_done")
        self._save_json(STATE_FILE, state)
        return "Policy evaluation recorded."

    def write_fraud_assessment(self, assessment: dict) -> str:
        validated, err = validate_fraud(assessment)
        if err:
            return f"[error] invalid fraud assessment: {err}"
        state = self._load_json(STATE_FILE) or {}
        state["fraud_assessment"] = validated.model_dump()
        state.setdefault("audit_trail", []).append("fraud_done")
        self._save_json(STATE_FILE, state)
        return "Fraud assessment recorded."

    def submit_decision(self, decision: str, notify: str = "") -> str:
        allowed = {"AUTO_APPROVE", "MISSING_DATA", "HUMAN_REVIEW"}
        if decision not in allowed:
            return f"[error] decision must be one of {sorted(allowed)}"
        state = self._load_json(STATE_FILE) or {}
        state["decision"] = {"route": decision, "notify": notify}
        state["status"] = "COMPLETED" if decision != "MISSING_DATA" else "AWAITING_DOCUMENTS"
        state.setdefault("audit_trail", []).append(f"adjudicated_{decision.lower()}")
        self._save_json(STATE_FILE, state)
        return f"Decision recorded: {decision}"

    def route_decision(self) -> str:
        state = self._load_json(STATE_FILE) or {}
        decision, err = route_claim(
            state.get("policy_evaluation", {}),
            state.get("fraud_assessment", {}),
            state.get("intake_findings", {}),
        )
        if err:
            return f"[error] cannot route claim: {err}"
        return self.submit_decision(decision.route.value, decision.notify)

    def write_decision_report(self) -> str:
        state = self._load_json(STATE_FILE) or {}
        lines = [
            f"# Warranty Claim Decision Report — {state.get('claim_id', 'UNKNOWN')}",
            "",
            f"**Status:** {state.get('status')}",
            f"**Dealership:** {state.get('dealership_id')}",
            "",
            "## Intake Findings",
            "```json",
            json.dumps(state.get("intake_findings", {}), indent=2),
            "```",
            "",
            "## Policy Evaluation",
            "```json",
            json.dumps(state.get("policy_evaluation", {}), indent=2),
            "```",
            "",
            "## Fraud Assessment",
            "```json",
            json.dumps(state.get("fraud_assessment", {}), indent=2),
            "```",
            "",
            "## Decision",
            "```json",
            json.dumps(state.get("decision", {}), indent=2),
            "```",
            "",
            f"**Audit trail:** {', '.join(state.get('audit_trail', []))}",
        ]
        report_path = "decision_report.md"
        self._resolve(report_path).write_text("\n".join(lines), encoding="utf-8")
        return f"Report written to {report_path}"
