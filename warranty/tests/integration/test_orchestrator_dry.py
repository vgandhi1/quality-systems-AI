"""End-to-end dry-run pipeline tests (no live LLM)."""

from __future__ import annotations

from pathlib import Path

import pytest

from warranty.orchestrator import run_dry_pipeline


@pytest.mark.parametrize(
    ("scenario", "expected_route", "expected_status"),
    [
        ("auto_approve", "AUTO_APPROVE", "COMPLETED"),
        ("missing_logs", "HUMAN_REVIEW", "COMPLETED"),
    ],
)
def test_dry_pipeline_scenarios(
    tmp_path: Path,
    scenario: str,
    expected_route: str,
    expected_status: str,
) -> None:
    state = run_dry_pipeline(tmp_path, scenario)
    assert state["decision"]["route"] == expected_route
    assert state["status"] == expected_status


def test_auto_approve_has_audit_trail(tmp_path: Path) -> None:
    state = run_dry_pipeline(tmp_path, "auto_approve")
    assert "intake_done" in state["audit_trail"]
    assert "policy_done" in state["audit_trail"]
    assert "fraud_done" in state["audit_trail"]
    assert "adjudicated_auto_approve" in state["audit_trail"]


def test_missing_logs_pauses_then_resumes(tmp_path: Path) -> None:
    state = run_dry_pipeline(tmp_path, "missing_logs")
    assert "documents_received" in state["audit_trail"]
    assert state["policy_evaluation"]["missing_docs"] == []
