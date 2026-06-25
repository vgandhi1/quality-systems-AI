"""Shared pytest fixtures for warranty test suites."""

from __future__ import annotations

import pytest

pytest.importorskip("fastapi")

from fastapi.testclient import TestClient

from warranty.api import create_app


@pytest.fixture
def client(monkeypatch) -> TestClient:
    monkeypatch.setenv("WARRANTY_ENVIRONMENT", "development")
    monkeypatch.setenv("WARRANTY_API_HOST", "127.0.0.1")
    monkeypatch.delenv("WARRANTY_API_KEY", raising=False)
    monkeypatch.delenv("WARRANTY_CORS_ORIGINS", raising=False)
    return TestClient(create_app())
