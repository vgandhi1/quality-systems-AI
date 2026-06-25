"""LLM provider adapter — Anthropic or Ollama (same env vars as AgentForge)."""

from __future__ import annotations

import json
import logging
import os

import httpx

from warranty.config import (
    get_llm_temperature,
    get_llm_timeout,
    get_max_completion_tokens,
    get_max_context_tokens,
)

logger = logging.getLogger(__name__)


class ContextBudgetExceeded(Exception):
    """Raised when an LLM request exceeds the configured context token budget."""


def provider() -> str:
    return os.getenv("AGENTFORGE_LLM_PROVIDER", "anthropic").strip().lower()


def model() -> str:
    if provider() == "ollama":
        return os.getenv("AGENTFORGE_OLLAMA_MODEL", "qwen2.5:7b-instruct")
    return os.getenv("AGENTFORGE_MODEL", "claude-opus-4-8")


def estimate_tokens(text: str) -> int:
    """Rough token estimate (4 chars ≈ 1 token) for budget checks."""
    return max(1, len(text) // 4)


def assert_context_budget(system: str, tools: list, messages: list) -> None:
    total = estimate_tokens(system) + estimate_tokens(json.dumps(tools, default=str))
    for message in messages:
        total += estimate_tokens(json.dumps(message, default=str))
    limit = get_max_context_tokens()
    if total > limit:
        raise ContextBudgetExceeded(
            f"Estimated context tokens ({total}) exceed MAX_CONTEXT_TOKENS ({limit})"
        )


async def chat_anthropic(client, system, tools, messages) -> dict:
    assert_context_budget(system, tools, messages)
    temperature = get_llm_temperature()
    timeout = get_llm_timeout()
    logger.debug(
        "anthropic call model=%s temperature=%s timeout=%ss",
        model(),
        temperature,
        timeout,
    )
    resp = await client.messages.create(
        model=model(),
        max_tokens=get_max_completion_tokens(),
        temperature=temperature,
        system=system,
        tools=tools,
        messages=messages,
        timeout=timeout,
    )
    text, calls = "", []
    for block in resp.content:
        if block.type == "text":
            text += block.text
        elif block.type == "tool_use":
            calls.append({"id": block.id, "name": block.name, "input": block.input})
    return {"text": text, "tool_calls": calls, "assistant_msg": {"role": "assistant", "content": resp.content}}


def tool_results_anthropic(pairs) -> dict:
    return {"role": "user", "content": [
        {"type": "tool_result", "tool_use_id": cid, "content": out} for cid, out in pairs
    ]}


def _to_ollama_tools(tools) -> list:
    return [{"type": "function", "function": {
        "name": t["name"], "description": t["description"], "parameters": t["input_schema"],
    }} for t in tools]


async def chat_ollama(system, tools, messages) -> dict:
    assert_context_budget(system, tools, messages)
    host = os.getenv("AGENTFORGE_OLLAMA_HOST", "http://127.0.0.1:11434").rstrip("/")
    temperature = get_llm_temperature()
    timeout = get_llm_timeout()
    payload = {
        "model": model(),
        "messages": [{"role": "system", "content": system}] + messages,
        "tools": _to_ollama_tools(tools),
        "stream": False,
        "options": {"temperature": temperature},
    }
    logger.debug(
        "ollama call model=%s temperature=%s timeout=%ss",
        model(),
        temperature,
        timeout,
    )
    async with httpx.AsyncClient(timeout=timeout) as c:
        r = await c.post(f"{host}/api/chat", json=payload)
        r.raise_for_status()
        msg = r.json()["message"]
    calls = []
    for tc in msg.get("tool_calls") or []:
        fn = tc["function"]
        args = fn["arguments"]
        if isinstance(args, str):
            args = json.loads(args or "{}")
        calls.append({"id": fn["name"], "name": fn["name"], "input": args})
    return {"text": msg.get("content", ""), "tool_calls": calls,
            "assistant_msg": {"role": "assistant", "content": msg.get("content", ""),
                              "tool_calls": msg.get("tool_calls") or []}}


def tool_results_ollama(pairs) -> list:
    return [{"role": "tool", "tool_name": cid, "content": out} for cid, out in pairs]
