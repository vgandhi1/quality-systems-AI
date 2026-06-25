"""Tests for LLM configuration and call discipline."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from warranty import llm


def test_default_llm_settings(monkeypatch) -> None:
    monkeypatch.delenv("WARRANTY_LLM_TEMPERATURE", raising=False)
    monkeypatch.delenv("WARRANTY_LLM_TIMEOUT_SECONDS", raising=False)
    monkeypatch.delenv("MAX_CONTEXT_TOKENS", raising=False)
    monkeypatch.delenv("MAX_COMPLETION_TOKENS", raising=False)

    from warranty.config import (
        get_llm_temperature,
        get_llm_timeout,
        get_max_completion_tokens,
        get_max_context_tokens,
    )

    assert get_llm_temperature() == 0.0
    assert get_llm_timeout() == 30.0
    assert get_max_context_tokens() == 8000
    assert get_max_completion_tokens() == 4000


def test_assert_context_budget_within_limit() -> None:
    llm.assert_context_budget("system", [], [{"role": "user", "content": "hi"}])


def test_assert_context_budget_exceeded(monkeypatch) -> None:
    monkeypatch.setenv("MAX_CONTEXT_TOKENS", "10")
    huge = "x" * 10_000
    with pytest.raises(llm.ContextBudgetExceeded):
        llm.assert_context_budget(huge, [], [])


@pytest.mark.asyncio
async def test_chat_anthropic_uses_temperature_zero(monkeypatch) -> None:
    monkeypatch.setenv("WARRANTY_LLM_TEMPERATURE", "0")
    monkeypatch.setenv("MAX_COMPLETION_TOKENS", "1024")
    monkeypatch.setenv("WARRANTY_LLM_TIMEOUT_SECONDS", "15")

    captured: dict = {}

    async def fake_create(**kwargs):
        captured.update(kwargs)
        block = MagicMock()
        block.type = "text"
        block.text = "ok"
        resp = MagicMock()
        resp.content = [block]
        return resp

    client = MagicMock()
    client.messages.create = AsyncMock(side_effect=fake_create)

    await llm.chat_anthropic(client, "system", [], [{"role": "user", "content": "go"}])

    assert captured["temperature"] == 0.0
    assert captured["max_tokens"] == 1024
    assert captured["timeout"] == 15.0


@pytest.mark.asyncio
async def test_chat_ollama_uses_temperature_and_timeout(monkeypatch) -> None:
    monkeypatch.setenv("AGENTFORGE_LLM_PROVIDER", "ollama")
    monkeypatch.setenv("WARRANTY_LLM_TEMPERATURE", "0")
    monkeypatch.setenv("WARRANTY_LLM_TIMEOUT_SECONDS", "12")

    requests: list = []

    class FakeResponse:
        def raise_for_status(self) -> None:
            return None

        def json(self) -> dict:
            return {"message": {"content": "ok", "tool_calls": []}}

    class FakeClient:
        def __init__(self, timeout: float) -> None:
            self.timeout = timeout

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args) -> None:
            return None

        async def post(self, url: str, json: dict):
            requests.append({"url": url, "json": json, "timeout": self.timeout})
            return FakeResponse()

    monkeypatch.setattr(llm.httpx, "AsyncClient", FakeClient)

    await llm.chat_ollama("system", [], [{"role": "user", "content": "go"}])

    assert requests[0]["timeout"] == 12.0
    assert requests[0]["json"]["options"]["temperature"] == 0.0
