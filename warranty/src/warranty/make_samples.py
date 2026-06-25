"""Generate sample warranty claim fixtures for the POC."""

from __future__ import annotations

import json
from pathlib import Path


def make_samples(workspace: Path) -> None:
    workspace.mkdir(parents=True, exist_ok=True)

    vin_registry = {
        "1HGCM82633A004352": {
            "vin": "1HGCM82633A004352",
            "warranty_active": True,
            "mileage": 42050,
            "model_year": 2023,
            "vehicle_model": "Accord",
        },
        "19XFC2F59ME123456": {
            "vin": "19XFC2F59ME123456",
            "warranty_active": True,
            "mileage": 28500,
            "model_year": 2021,
            "vehicle_model": "Civic",
        },
    }
    (workspace / "vin_registry.json").write_text(json.dumps(vin_registry, indent=2), encoding="utf-8")

    policy_manual = {
        "chunks": [
            {
                "id": "SB-2023-HYB-01",
                "text": "Hybrid battery replacement covered under 8yr/100k miles powertrain warranty.",
                "components": ["hybrid_battery_module", "hybrid_battery"],
                "required_docs": ["battery_cell_voltage_logs"],
                "metadata": {
                    "model_year": [2022, 2023, 2024],
                    "vehicle_model": ["Accord", "Civic"],
                    "component_category": "Powertrain",
                    "document_type": "Service_Bulletin",
                },
            },
            {
                "id": "doc_884_sec4.2",
                "text": "Transmission control module (TCM) replacement covered when DTC P0700 present with fluid leak evidence.",
                "components": ["transmission_pan", "gasket", "tcm"],
                "required_docs": [],
                "metadata": {
                    "model_year": [2020, 2021, 2022, 2023],
                    "vehicle_model": ["Accord", "Civic"],
                    "component_category": "Powertrain",
                    "document_type": "Service_Manual",
                },
            },
            {
                "id": "SB-2021-SENS-02",
                "text": "Mass airflow sensor replacement covered under emissions warranty; standard labor 0.8 hours.",
                "components": ["mass_airflow_sensor"],
                "required_docs": [],
                "metadata": {
                    "model_year": [2020, 2021, 2022],
                    "vehicle_model": ["Civic"],
                    "component_category": "Emissions",
                    "document_type": "Service_Bulletin",
                },
            },
        ]
    }
    (workspace / "policy_manual.json").write_text(json.dumps(policy_manual, indent=2), encoding="utf-8")

    labor_matrix = {
        "hybrid_battery_replace": {"standard_hours": 6.0, "operation": "Hybrid battery module R&R"},
        "tcm_replace": {"standard_hours": 4.5, "operation": "TCM replacement"},
        "maf_sensor_replace": {"standard_hours": 0.8, "operation": "MAF sensor replacement"},
    }
    (workspace / "labor_matrix.json").write_text(json.dumps(labor_matrix, indent=2), encoding="utf-8")

    dealership_history = {
        "DLR-4458": {"dealership_id": "DLR-4458", "claims_30d": 42, "fraud_flags": 0, "avg_labor_variance_h": 0.3},
        "DLR-9901": {"dealership_id": "DLR-9901", "claims_30d": 180, "fraud_flags": 3, "avg_labor_variance_h": 2.1},
    }
    (workspace / "dealership_history.json").write_text(
        json.dumps(dealership_history, indent=2), encoding="utf-8"
    )


def make_auto_approve_claim(workspace: Path) -> None:
    claim = {
        "claim_id": "WAR-99001",
        "dealership_id": "DLR-4458",
        "vin": "19XFC2F59ME123456",
        "customer_ref": "CUST-REDacted",
        "parts": [{"name": "mass_airflow_sensor", "cost": 185}],
        "labor_hours": 0.8,
        "total_cost": 320,
        "repair_operation": "maf_sensor_replace",
    }
    (workspace / "claim.json").write_text(json.dumps(claim, indent=2), encoding="utf-8")
    (workspace / "diagnostic.txt").write_text(
        "OBD-II SCAN REPORT\n"
        "VIN: 19XFC2F59ME123456\n"
        "DTC: P0101 — Mass or Volume Air Flow Circuit Range/Performance\n"
        "Freeze frame: MAF g/s below expected at idle.\n"
        "Technician notes: MAF sensor contaminated; replacement recommended.\n",
        encoding="utf-8",
    )


def make_missing_logs_claim(workspace: Path) -> None:
    claim = {
        "claim_id": "WAR-10452",
        "dealership_id": "DLR-4458",
        "vin": "1HGCM82633A004352",
        "customer_ref": "CUST-REDacted",
        "parts": [{"name": "hybrid_battery_module", "cost": 3800}],
        "labor_hours": 6.5,
        "total_cost": 4500,
        "repair_operation": "hybrid_battery_replace",
    }
    (workspace / "claim.json").write_text(json.dumps(claim, indent=2), encoding="utf-8")
    (workspace / "diagnostic.txt").write_text(
        "OBD-II SCAN REPORT\n"
        "VIN: 1HGCM82633A004352\n"
        "DTC: P0A7F — Hybrid battery pack deterioration\n"
        "SOC imbalance detected across modules 3 and 7.\n"
        "Technician notes: Hybrid battery requires replacement; cell voltage logs pending upload.\n",
        encoding="utf-8",
    )


def make_voltage_logs(workspace: Path) -> None:
    (workspace / "voltage_logs.txt").write_text(
        "HYBRID BATTERY CELL VOLTAGE LOG\n"
        "Module 3: 3.42V (below threshold 3.50V)\n"
        "Module 7: 3.38V (below threshold 3.50V)\n"
        "Pack imbalance confirmed — replacement justified.\n",
        encoding="utf-8",
    )
