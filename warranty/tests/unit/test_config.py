"""Tests for API configuration and auth policy."""

from __future__ import annotations

import pytest

from warranty.config import auth_required, validate_api_config


def test_auth_required_false_on_localhost_dev(monkeypatch) -> None:
    monkeypatch.setenv("WARRANTY_ENVIRONMENT", "development")
    monkeypatch.setenv("WARRANTY_API_HOST", "127.0.0.1")
    assert auth_required() is False


def test_auth_required_true_on_lan_bind(monkeypatch) -> None:
    monkeypatch.setenv("WARRANTY_ENVIRONMENT", "development")
    monkeypatch.setenv("WARRANTY_API_HOST", "0.0.0.0")
    assert auth_required() is True


def test_auth_required_true_in_production(monkeypatch) -> None:
    monkeypatch.setenv("WARRANTY_ENVIRONMENT", "production")
    monkeypatch.setenv("WARRANTY_API_HOST", "127.0.0.1")
    assert auth_required() is True


def test_validate_passes_localhost_dev_without_key(monkeypatch) -> None:
    monkeypatch.setenv("WARRANTY_ENVIRONMENT", "development")
    monkeypatch.setenv("WARRANTY_API_HOST", "127.0.0.1")
    monkeypatch.delenv("WARRANTY_API_KEY", raising=False)
    validate_api_config()


def test_validate_fails_production_without_key(monkeypatch) -> None:
    monkeypatch.setenv("WARRANTY_ENVIRONMENT", "production")
    monkeypatch.delenv("WARRANTY_API_KEY", raising=False)
    with pytest.raises(SystemExit):
        validate_api_config()


def test_validate_fails_lan_bind_without_key(monkeypatch) -> None:
    monkeypatch.setenv("WARRANTY_ENVIRONMENT", "development")
    monkeypatch.setenv("WARRANTY_API_HOST", "0.0.0.0")
    monkeypatch.delenv("WARRANTY_API_KEY", raising=False)
    with pytest.raises(SystemExit):
        validate_api_config()
