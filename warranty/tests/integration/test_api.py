"""Tests for FastAPI adjudication service."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

pytest.importorskip("fastapi")

from warranty.api import create_app


def test_root_redirects_to_docs(client: TestClient) -> None:
    response = client.get("/", follow_redirects=False)
    assert response.status_code in (302, 307)
    assert response.headers["location"] == "/docs"


def test_health(client: TestClient) -> None:
    response = client.get("/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["auth_required"] is False


def test_adjudicate_dry_run_auto_approve(client: TestClient) -> None:
    response = client.post("/adjudicate/dry-run", json={"scenario": "auto_approve"})
    assert response.status_code == 200
    body = response.json()
    assert body["claim_state"]["decision"]["route"] == "AUTO_APPROVE"
    assert body["escalation"] is None


def test_adjudicate_dry_run_missing_logs_escalates(client: TestClient) -> None:
    response = client.post("/adjudicate/dry-run", json={"scenario": "missing_logs"})
    assert response.status_code == 200
    body = response.json()
    assert body["claim_state"]["decision"]["route"] == "HUMAN_REVIEW"
    assert body["escalation"] is not None
    assert body["escalation"]["claim_id"] == "WAR-10452"


def test_escalate_handoff_rejects_auto_approve(client: TestClient) -> None:
    response = client.post(
        "/escalate/handoff",
        json={"decision": {"route": "AUTO_APPROVE"}, "claim_id": "WAR-1"},
    )
    assert response.status_code == 400


def test_lan_bind_requires_api_key(monkeypatch) -> None:
    monkeypatch.setenv("WARRANTY_ENVIRONMENT", "development")
    monkeypatch.setenv("WARRANTY_API_HOST", "0.0.0.0")
    monkeypatch.setenv("WARRANTY_API_KEY", "test-secret-key")
    lan_client = TestClient(create_app())

    denied = lan_client.post("/adjudicate/dry-run", json={"scenario": "auto_approve"})
    assert denied.status_code == 401

    allowed = lan_client.post(
        "/adjudicate/dry-run",
        json={"scenario": "auto_approve"},
        headers={"X-API-Key": "test-secret-key"},
    )
    assert allowed.status_code == 200


def test_optional_key_enforced_when_set_on_localhost(monkeypatch) -> None:
    monkeypatch.setenv("WARRANTY_ENVIRONMENT", "development")
    monkeypatch.setenv("WARRANTY_API_HOST", "127.0.0.1")
    monkeypatch.setenv("WARRANTY_API_KEY", "dev-key")
    keyed_client = TestClient(create_app())

    denied = keyed_client.post("/adjudicate/dry-run", json={"scenario": "auto_approve"})
    assert denied.status_code == 401

    allowed = keyed_client.post(
        "/adjudicate/dry-run",
        json={"scenario": "auto_approve"},
        headers={"X-API-Key": "dev-key"},
    )
    assert allowed.status_code == 200


def test_cors_allows_configured_origin(monkeypatch) -> None:
    monkeypatch.setenv("WARRANTY_ENVIRONMENT", "development")
    monkeypatch.setenv("WARRANTY_API_HOST", "127.0.0.1")
    monkeypatch.setenv("WARRANTY_CORS_ORIGINS", "http://192.168.1.10:3000")
    cors_client = TestClient(create_app())

    response = cors_client.options(
        "/health",
        headers={
            "Origin": "http://192.168.1.10:3000",
            "Access-Control-Request-Method": "GET",
        },
    )
    assert response.headers.get("access-control-allow-origin") == "http://192.168.1.10:3000"
