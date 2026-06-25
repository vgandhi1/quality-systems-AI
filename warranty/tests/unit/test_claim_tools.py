"""Tests for ClaimStore sandbox and write-path validation."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from warranty.claim_tools import ClaimStore
from warranty.make_samples import make_auto_approve_claim, make_samples


@pytest.fixture
def workspace(tmp_path: Path) -> Path:
    make_samples(tmp_path)
    make_auto_approve_claim(tmp_path)
    return tmp_path


@pytest.fixture
def store(workspace: Path) -> ClaimStore:
    return ClaimStore(workspace)


def test_read_claim_form(store: ClaimStore) -> None:
    data = json.loads(store.read_claim_form("claim.json"))
    assert data["claim_id"] == "WAR-99001"


def test_path_traversal_rejected(store: ClaimStore) -> None:
    with pytest.raises(ValueError, match="traversal|escapes|Invalid"):
        store._resolve("../../../etc/passwd")


def test_unsafe_characters_rejected(store: ClaimStore) -> None:
    with pytest.raises(ValueError):
        store._resolve("file;rm")


def test_lookup_vin_found(store: ClaimStore) -> None:
    record = json.loads(store.lookup_vin("19XFC2F59ME123456"))
    assert record["vehicle_model"] == "Civic"


def test_lookup_vin_redacts_missing(store: ClaimStore) -> None:
    result = json.loads(store.lookup_vin("ZZZZZZZZZZZZZZZZZ"))
    assert "error" in result
    assert "ZZZZZZZZ" in result["error"]
    assert "ZZZZZZZZZZZZZZZZZ" not in result["error"]


def test_write_intake_rejects_empty_codes(store: ClaimStore) -> None:
    store.init_claim_state("WAR-1", "DLR-4458", "19XFC2F59ME123456")
    result = store.write_intake_findings(
        {
            "identified_parts": ["mass_airflow_sensor"],
            "extracted_codes": [],
            "labor_hours": 0.8,
            "total_cost": 320,
        }
    )
    assert result.startswith("[error]")


def test_write_intake_rejects_zero_labor(store: ClaimStore) -> None:
    store.init_claim_state("WAR-1", "DLR-4458", "19XFC2F59ME123456")
    result = store.write_intake_findings(
        {
            "identified_parts": ["mass_airflow_sensor"],
            "extracted_codes": ["P0101"],
            "labor_hours": 0,
            "total_cost": 320,
        }
    )
    assert result.startswith("[error]")


def test_write_policy_requires_citation_when_covered(store: ClaimStore) -> None:
    store.init_claim_state("WAR-1", "DLR-4458", "19XFC2F59ME123456")
    result = store.write_policy_evaluation(
        {
            "is_covered": True,
            "relevant_clause_id": "NONE",
            "citation": "",
            "missing_docs": [],
        }
    )
    assert result.startswith("[error]")


def test_write_fraud_rejects_out_of_range_score(store: ClaimStore) -> None:
    store.init_claim_state("WAR-1", "DLR-4458", "19XFC2F59ME123456")
    result = store.write_fraud_assessment({"score": 150, "justification": "test"})
    assert result.startswith("[error]")


def test_valid_writes_persist(store: ClaimStore) -> None:
    store.init_claim_state("WAR-1", "DLR-4458", "19XFC2F59ME123456")
    assert store.write_intake_findings(
        {
            "identified_parts": ["mass_airflow_sensor"],
            "extracted_codes": ["P0101"],
            "labor_hours": 0.8,
            "total_cost": 320,
            "repair_operation": "maf_sensor_replace",
        }
    ) == "Intake findings recorded."
    state = json.loads(store.read_claim_state())
    assert state["intake_findings"]["extracted_codes"] == ["P0101"]
