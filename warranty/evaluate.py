"""
Offline dry-run evaluation harness for warranty adjudication scenarios.

Usage:
    uv run python evaluate.py
    uv run python evaluate.py --check
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

from warranty.orchestrator import run_dry_pipeline
from warranty.validation import (
    AUTO_APPROVE_COST_LIMIT,
    AUTO_APPROVE_FRAUD_MAX,
    HUMAN_REVIEW_FRAUD_MIN,
)

ROOT = Path(__file__).parent
MODELS_DIR = ROOT / "models"
METRICS_PATH = MODELS_DIR / "metrics.json"
MANIFEST_PATH = MODELS_DIR / "manifest.json"
MAKE_SAMPLES_PATH = ROOT / "src" / "warranty" / "make_samples.py"

SCENARIOS: dict[str, dict[str, str]] = {
    "auto_approve": {
        "expected_route": "AUTO_APPROVE",
        "expected_status": "COMPLETED",
    },
    "missing_logs": {
        "expected_route": "HUMAN_REVIEW",
        "expected_status": "COMPLETED",
    },
}


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def run_scenario(scenario: str, workspace: Path) -> dict:
    expected = SCENARIOS[scenario]
    state = run_dry_pipeline(workspace, scenario)
    actual_route = state["decision"]["route"]
    actual_status = state["status"]
    passed = (
        actual_route == expected["expected_route"]
        and actual_status == expected["expected_status"]
    )
    return {
        "expected_route": expected["expected_route"],
        "expected_status": expected["expected_status"],
        "actual_route": actual_route,
        "actual_status": actual_status,
        "passed": passed,
        "claim_id": state.get("claim_id"),
        "fraud_score": state.get("fraud_assessment", {}).get("score"),
        "total_cost": state.get("intake_findings", {}).get("total_cost"),
    }


def evaluate_all() -> dict:
    results: dict[str, dict] = {}
    all_passed = True
    for name in SCENARIOS:
        with tempfile.TemporaryDirectory() as tmp:
            outcome = run_scenario(name, Path(tmp))
            results[name] = outcome
            if not outcome["passed"]:
                all_passed = False
    return {
        "evaluated_at": datetime.now(timezone.utc).isoformat(),
        "environment": "development",
        "scenarios": results,
        "all_passed": all_passed,
        "scenario_count": len(SCENARIOS),
        "passed_count": sum(1 for r in results.values() if r["passed"]),
    }


def build_manifest(metrics: dict) -> dict:
    return {
        "evaluated_at": metrics["evaluated_at"],
        "environment": metrics["environment"],
        "scenario_names": list(SCENARIOS.keys()),
        "make_samples_sha256": _sha256(MAKE_SAMPLES_PATH),
        "routing_thresholds": {
            "auto_approve_cost_limit": AUTO_APPROVE_COST_LIMIT,
            "auto_approve_fraud_max": AUTO_APPROVE_FRAUD_MAX,
            "human_review_fraud_min": HUMAN_REVIEW_FRAUD_MIN,
        },
        "all_passed": metrics["all_passed"],
        "passed_count": metrics["passed_count"],
        "scenario_count": metrics["scenario_count"],
    }


def write_artifacts(metrics: dict) -> None:
    MODELS_DIR.mkdir(parents=True, exist_ok=True)
    manifest = build_manifest(metrics)
    METRICS_PATH.write_text(json.dumps(metrics, indent=2), encoding="utf-8")
    MANIFEST_PATH.write_text(json.dumps(manifest, indent=2), encoding="utf-8")


def check_against_pinned(current: dict, pinned_path: Path = METRICS_PATH) -> list[str]:
    if not pinned_path.exists():
        return []
    pinned = json.loads(pinned_path.read_text(encoding="utf-8"))
    errors: list[str] = []
    for name in SCENARIOS:
        pinned_scenario = pinned.get("scenarios", {}).get(name, {})
        current_scenario = current.get("scenarios", {}).get(name, {})
        for key in ("expected_route", "expected_status", "actual_route", "actual_status"):
            if pinned_scenario.get(key) != current_scenario.get(key):
                errors.append(
                    f"{name}.{key}: pinned={pinned_scenario.get(key)!r} "
                    f"current={current_scenario.get(key)!r}"
                )
    if pinned.get("all_passed") is True and not current.get("all_passed"):
        errors.append("all_passed regressed from true to false")
    return errors


def print_summary(metrics: dict) -> None:
    print(f"\nWarranty dry-run evaluation — {metrics['passed_count']}/{metrics['scenario_count']} passed\n")
    print(f"{'Scenario':<18}{'route':>16}{'status':>14}{'ok':>6}")
    for name, result in metrics["scenarios"].items():
        mark = "yes" if result["passed"] else "NO"
        print(
            f"{name:<18}{result['actual_route']:>16}"
            f"{result['actual_status']:>14}{mark:>6}"
        )
    print(f"\nMetrics  -> {METRICS_PATH}")
    print(f"Manifest -> {MANIFEST_PATH}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Offline warranty scenario evaluation")
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--no-write", action="store_true")
    args = parser.parse_args()

    metrics = evaluate_all()
    regressions = check_against_pinned(metrics) if args.check else []

    print_summary(metrics)

    if not metrics["all_passed"]:
        print("\nFAIL: one or more scenarios did not meet expectations.", file=sys.stderr)
        return 1
    if regressions:
        print("\nFAIL: regression vs pinned metrics:", file=sys.stderr)
        for msg in regressions:
            print(f"  - {msg}", file=sys.stderr)
        return 1

    if not args.no_write:
        write_artifacts(metrics)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
