"""Integration tests for the agent tool loop — mocked LLM, no live API calls."""

from __future__ import annotations

import asyncio

import pytest

from warranty import llm
from warranty.orchestrator import _format_tool_output, _tool_loop
from warranty.personas import ADJUDICATOR_TOOLS, SYSTEM_PROMPTS
from warranty.prompt_safety import CONTEXT_BOUNDARY


@pytest.mark.asyncio
async def test_tool_loop_mocked_anthropic_captures_decision(monkeypatch) -> None:
    monkeypatch.setattr(llm, "provider", lambda: "anthropic")
    call_count = 0

    async def fake_anthropic(_client, system, tools, messages):
        nonlocal call_count
        call_count += 1
        assert CONTEXT_BOUNDARY in system
        if call_count == 1:
            return {
                "text": "",
                "tool_calls": [{"id": "t1", "name": "read_claim_state", "input": {}}],
                "assistant_msg": {"role": "assistant", "content": []},
            }
        if call_count == 2:
            return {
                "text": "routing complete",
                "tool_calls": [{
                    "id": "t2",
                    "name": "submit_decision",
                    "input": {"decision": "HUMAN_REVIEW", "notify": "manual review"},
                }],
                "assistant_msg": {"role": "assistant", "content": []},
            }
        return {
            "text": "done",
            "tool_calls": [],
            "assistant_msg": {"role": "assistant", "content": []},
        }

    monkeypatch.setattr(llm, "chat_anthropic", fake_anthropic)

    handlers = {
        "read_claim_state": lambda _i: '{"claim_id": "WAR-1"}',
        "submit_decision": lambda i: f"stored {i['decision']}",
    }

    result = await _tool_loop(
        None,
        SYSTEM_PROMPTS["adjudicator"],
        "Read claim state and submit the routing decision.",
        ADJUDICATOR_TOOLS,
        handlers,
        max_steps=4,
    )

    assert result["decision"]["decision"] == "HUMAN_REVIEW"
    assert call_count >= 2


def test_format_tool_output_wraps_document_reads() -> None:
    wrapped = _format_tool_output("read_diagnostic_report", "DTC: P0101")
    assert wrapped.startswith("<context>")
    assert "P0101" in wrapped


def test_format_tool_output_passes_through_writes() -> None:
    raw = _format_tool_output("write_intake_findings", "ok")
    assert raw == "ok"


def test_tool_loop_sync_entrypoint(monkeypatch) -> None:
    """Run mocked loop without pytest-asyncio for environments that skip it."""
    monkeypatch.setattr(llm, "provider", lambda: "anthropic")

    async def fake_anthropic(_client, _system, _tools, _messages):
        return {
            "text": "done",
            "tool_calls": [{
                "id": "t1",
                "name": "submit_decision",
                "input": {"decision": "AUTO_APPROVE"},
            }],
            "assistant_msg": {"role": "assistant", "content": []},
        }

    monkeypatch.setattr(llm, "chat_anthropic", fake_anthropic)
    handlers = {"submit_decision": lambda i: "ok"}

    result = asyncio.run(
        _tool_loop(
            None,
            SYSTEM_PROMPTS["adjudicator"],
            "submit",
            ADJUDICATOR_TOOLS,
            handlers,
            max_steps=2,
        )
    )
    assert result["decision"]["decision"] == "AUTO_APPROVE"
