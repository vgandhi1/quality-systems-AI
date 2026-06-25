"""Tests for the offline evaluate harness."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from evaluate import SCENARIOS, build_manifest, check_against_pinned, evaluate_all, run_scenario
from warranty.config import MANIFEST_PATH, METRICS_PATH


def test_scenario_registry_has_expected_keys() -> None:
    assert "auto_approve" in SCENARIOS
    assert "missing_logs" in SCENARIOS


def test_run_scenario_auto_approve(tmp_path: Path) -> None:
    result = run_scenario("auto_approve", tmp_path)
    assert result["passed"] is True
    assert result["actual_route"] == "AUTO_APPROVE"
    assert result["actual_status"] == "COMPLETED"


def test_run_scenario_missing_logs(tmp_path: Path) -> None:
    result = run_scenario("missing_logs", tmp_path)
    assert result["passed"] is True
    assert result["actual_route"] == "HUMAN_REVIEW"


def test_evaluate_all_passes() -> None:
    metrics = evaluate_all()
    assert metrics["all_passed"] is True
    assert metrics["passed_count"] == len(SCENARIOS)


def test_build_manifest_includes_thresholds() -> None:
    metrics = evaluate_all()
    manifest = build_manifest(metrics)
    assert "routing_thresholds" in manifest
    assert manifest["routing_thresholds"]["auto_approve_cost_limit"] == 1500


def test_check_against_pinned_detects_regression(tmp_path: Path) -> None:
    pinned = {
        "all_passed": True,
        "scenarios": {
            "auto_approve": {
                "expected_route": "AUTO_APPROVE",
                "expected_status": "COMPLETED",
                "actual_route": "AUTO_APPROVE",
                "actual_status": "COMPLETED",
            }
        },
    }
    pinned_path = tmp_path / "metrics.json"
    pinned_path.write_text(json.dumps(pinned), encoding="utf-8")
    current = evaluate_all()
    current["scenarios"]["auto_approve"]["actual_route"] = "HUMAN_REVIEW"
    errors = check_against_pinned(current, pinned_path)
    assert any("auto_approve.actual_route" in e for e in errors)


@pytest.mark.skipif(not METRICS_PATH.exists(), reason="pinned metrics not generated yet")
def test_pinned_metrics_on_disk() -> None:
    metrics = json.loads(METRICS_PATH.read_text(encoding="utf-8"))
    assert metrics["all_passed"] is True
    assert METRICS_PATH.exists()
    assert MANIFEST_PATH.exists()
