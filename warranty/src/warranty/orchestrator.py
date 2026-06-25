"""Warranty claims orchestrator: Intake → Policy → Fraud → Adjudicator."""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import tempfile
from pathlib import Path

from warranty import llm
from warranty.claim_tools import ClaimStore
from warranty.config import WORKSPACE_DIR
from warranty.make_samples import (
    make_auto_approve_claim,
    make_missing_logs_claim,
    make_samples,
    make_voltage_logs,
)
from warranty.personas import (
    ADJUDICATOR_TOOLS,
    FRAUD_TOOLS,
    INTAKE_TOOLS,
    POLICY_TOOLS,
    SYSTEM_PROMPTS,
)
from warranty.prompt_safety import wrap_context, wrap_user_task

logger = logging.getLogger(__name__)

MAX_TOOL_STEPS = 12

TOOLS_WITH_CONTEXT_WRAP = frozenset({
    "read_claim_form",
    "read_diagnostic_report",
    "read_claim_state",
    "lookup_vin",
    "search_policy",
    "get_labor_matrix",
    "get_dealership_history",
})


def _format_tool_output(tool_name: str, output: str) -> str:
    if tool_name in TOOLS_WITH_CONTEXT_WRAP:
        return wrap_context(output)
    return str(output)


def _build_handlers(store: ClaimStore) -> dict:
    return {
        "read_claim_form": lambda i: store.read_claim_form(i["path"]),
        "read_diagnostic_report": lambda i: store.read_diagnostic_report(i["path"]),
        "write_intake_findings": lambda i: store.write_intake_findings(i["findings"]),
        "lookup_vin": lambda i: store.lookup_vin(i["vin"]),
        "search_policy": lambda i: store.search_policy(
            i["component"], i.get("model_year"), i.get("vehicle_model")
        ),
        "write_policy_evaluation": lambda i: store.write_policy_evaluation(i["evaluation"]),
        "get_labor_matrix": lambda i: store.get_labor_matrix(i["operation"]),
        "get_dealership_history": lambda i: store.get_dealership_history(i["dealership_id"]),
        "write_fraud_assessment": lambda i: store.write_fraud_assessment(i["assessment"]),
        "read_claim_state": lambda _i: store.read_claim_state(),
        "submit_decision": lambda i: store.submit_decision(i["decision"], i.get("notify", "")),
    }


def _setup_scenario(workspace: Path, scenario: str) -> None:
    make_samples(workspace)
    if scenario == "auto_approve":
        make_auto_approve_claim(workspace)
    else:
        make_missing_logs_claim(workspace)


def _extract_dtc_codes(diagnostic: str) -> list[str]:
    codes: list[str] = []
    for line in diagnostic.splitlines():
        if "DTC:" in line or line[:4].startswith("P0"):
            token = line.split("—")[0].split(":")[-1].strip().split()[0]
            if token.startswith("P"):
                codes.append(token)
    return codes


def run_dry_pipeline(workspace: Path, scenario: str) -> dict:
    """Run the deterministic pipeline and return the final claim state dict."""
    _setup_scenario(workspace, scenario)
    store = ClaimStore(workspace)

    claim = json.loads(store.read_claim_form("claim.json"))
    store.init_claim_state(claim["claim_id"], claim["dealership_id"], claim["vin"])

    parts = [p["name"] for p in claim.get("parts", [])]
    diag = store.read_diagnostic_report("diagnostic.txt")
    intake = {
        "identified_parts": parts,
        "extracted_codes": _extract_dtc_codes(diag) or ["P0101"],
        "labor_hours": claim["labor_hours"],
        "total_cost": claim["total_cost"],
        "repair_operation": claim.get("repair_operation", "unknown"),
    }
    store.write_intake_findings(intake)

    vin_data = json.loads(store.lookup_vin(claim["vin"]))
    policy_hits = json.loads(
        store.search_policy(
            parts[0] if parts else "unknown",
            vin_data.get("model_year"),
            vin_data.get("vehicle_model"),
        )
    )
    matches = policy_hits.get("matches", [])
    clause = matches[0] if matches else {}
    required = clause.get("required_docs", [])
    attachments = {"diagnostic.txt"}
    if scenario == "missing_logs_resumed":
        attachments.add("voltage_logs.txt")
    missing = [
        doc
        for doc in required
        if not any(doc.replace("_", "") in name.replace("_", "") for name in attachments)
    ]
    evaluation = {
        "is_covered": bool(matches),
        "relevant_clause_id": clause.get("id", "NONE"),
        "citation": clause.get("text", ""),
        "missing_docs": missing,
    }
    store.write_policy_evaluation(evaluation)

    op = claim.get("repair_operation", "unknown")
    matrix = json.loads(store.get_labor_matrix(op))
    history = json.loads(store.get_dealership_history(claim["dealership_id"]))
    std_hours = matrix.get("standard_hours", claim["labor_hours"])
    variance = abs(claim["labor_hours"] - std_hours)
    score = min(100, int(variance * 15 + history.get("fraud_flags", 0) * 10))
    justification = (
        f"Labor variance {variance:.1f}h vs matrix ({std_hours}h standard). "
        f"Dealership {history.get('claims_30d', 0)} claims/30d, "
        f"{history.get('fraud_flags', 0)} fraud flags."
    )
    store.write_fraud_assessment({"score": score, "justification": justification})

    if scenario == "missing_logs":
        store.route_decision()
        make_voltage_logs(workspace)
        state = json.loads(store.read_claim_state())
        state["policy_evaluation"]["missing_docs"] = []
        state["status"] = "IN_PROGRESS"
        state["decision"] = None
        state["audit_trail"].append("documents_received")
        (workspace / ".claim_state.json").write_text(json.dumps(state, indent=2), encoding="utf-8")
        store.route_decision()
    else:
        store.route_decision()

    store.write_decision_report()
    return json.loads(store.read_claim_state())


def run_dry_pipeline_isolated(scenario: str) -> dict:
    """Run dry pipeline in a temp workspace (for API and evaluate harness)."""
    with tempfile.TemporaryDirectory() as tmp:
        return run_dry_pipeline(Path(tmp), scenario)


def dry_run(scenario: str, workspace: Path | None = None) -> None:
    root = workspace or WORKSPACE_DIR
    state = run_dry_pipeline(root, scenario)
    logger.info("=== WARRANTY POC DRY-RUN (scenario=%s) ===", scenario)
    store = ClaimStore(root)
    logger.info("--- Claim form ---\n%s", store.read_claim_form("claim.json"))
    logger.info("--- Diagnostic ---\n%s", store.read_diagnostic_report("diagnostic.txt"))
    logger.info("--- Final claim state ---\n%s", json.dumps(state, indent=2))


async def _tool_loop(client, system, user, tools, handlers, max_steps=MAX_TOOL_STEPS) -> dict:
    is_ollama = llm.provider() == "ollama"
    messages = [{"role": "user", "content": wrap_user_task(user)}]
    captured: dict = {}
    final_text = ""
    for _ in range(max_steps):
        if is_ollama:
            turn = await llm.chat_ollama(system, tools, messages)
        else:
            turn = await llm.chat_anthropic(client, system, tools, messages)
        messages.append(turn["assistant_msg"])
        final_text += turn["text"]
        pairs = []
        for call in turn["tool_calls"]:
            if call["name"] == "submit_decision":
                captured = call["input"]
                out = handlers["submit_decision"](call["input"])
            else:
                handler = handlers.get(call["name"])
                try:
                    out = handler(call["input"]) if handler else f"[unknown tool {call['name']}]"
                except Exception as e:
                    out = f"[tool {call['name']} error: {e}]"
            logger.info(
                "tool %s(%s) -> %s",
                call["name"],
                json.dumps(call["input"])[:80],
                str(out)[:100],
            )
            pairs.append((call["id"], _format_tool_output(call["name"], str(out))))
        if not pairs:
            break
        if is_ollama:
            messages.extend(llm.tool_results_ollama(pairs))
        else:
            messages.append(llm.tool_results_anthropic(pairs))
    return {"final_text": final_text, "decision": captured}


async def live_run(scenario: str, root: Path | None) -> None:
    workspace = root or WORKSPACE_DIR
    _setup_scenario(workspace, scenario)
    store = ClaimStore(workspace)
    handlers = _build_handlers(store)

    claim = json.loads(store.read_claim_form("claim.json"))
    store.init_claim_state(claim["claim_id"], claim["dealership_id"], claim["vin"])

    client = None
    if llm.provider() != "ollama":
        from anthropic import AsyncAnthropic

        client = AsyncAnthropic()

    logger.info(
        "live run provider=%s model=%s scenario=%s",
        llm.provider(),
        llm.model(),
        scenario,
    )

    for label, prompt, tools in [
        ("Intake", "Process claim.json and diagnostic.txt. Extract findings and write them.", INTAKE_TOOLS),
        ("Policy", "Evaluate warranty coverage for this claim. Check VIN and search policy.", POLICY_TOOLS),
        ("Fraud", "Score fraud risk for this claim based on labor matrix and dealership history.", FRAUD_TOOLS),
    ]:
        logger.info("=== %s Agent ===", label)
        await _tool_loop(client, SYSTEM_PROMPTS[label.lower()], prompt, tools, handlers)

    logger.info("=== Adjudicator Agent ===")
    result = await _tool_loop(
        client,
        SYSTEM_PROMPTS["adjudicator"],
        "Read claim state and submit the routing decision.",
        ADJUDICATOR_TOOLS,
        handlers,
    )
    llm_decision = result["decision"].get("decision")
    gate_result = store.route_decision()
    logger.info("LLM suggested=%s; authoritative gate=%s", llm_decision, gate_result)

    state = json.loads(store.read_claim_state())
    decision = state.get("decision", {})
    logger.info("Verdict: %s — %s", decision.get("route", "UNKNOWN"), decision.get("notify", ""))
    logger.info(store.write_decision_report())
    logger.info("--- Final claim state ---\n%s", store.read_claim_state())


def _configure_logging() -> None:
    logging.basicConfig(level=logging.INFO, format="%(message)s")


def main() -> None:
    try:
        from dotenv import load_dotenv

        load_dotenv()
    except ImportError:
        pass
    _configure_logging()
    ap = argparse.ArgumentParser(description="Warranty claims agentic POC")
    ap.add_argument("--dry-run", action="store_true", help="Deterministic pipeline, no LLM")
    ap.add_argument(
        "--scenario",
        choices=["auto_approve", "missing_logs", "missing_logs_resumed"],
        default="auto_approve",
        help="Fixture scenario",
    )
    ap.add_argument("--root", help="Workspace root (default: WARRANTY_WORKSPACE or ./workspace)")
    args = ap.parse_args()
    root = Path(args.root) if args.root else None
    if args.dry_run:
        dry_run(args.scenario, root)
    else:
        asyncio.run(live_run(args.scenario, root))


if __name__ == "__main__":
    main()
