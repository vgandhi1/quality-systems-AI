"""HTTP client for posting RCA escalations to QualityMind-RAG."""

from __future__ import annotations

import ipaddress
import socket
import time
from typing import Any
from urllib.parse import urlparse

import httpx

from warranty.config import QUALITYMIND_API_KEY, QUALITYMIND_BASE_URL
from warranty.schema import RcaEscalation

_ALLOWED_SCHEMES = {"http", "https"}
_RETRYABLE_STATUS = {502, 503, 504}
_SUPPORTED_ENDPOINTS = {"/quality/five-why", "/quality/draft-8d"}


class QualityMindClientError(Exception):
    """Raised when the QualityMind escalation request fails."""


def _validate_url(url_base: str) -> None:
    parsed = urlparse(url_base)
    if parsed.scheme not in _ALLOWED_SCHEMES:
        raise QualityMindClientError(
            f"QUALITYMIND_BASE_URL scheme must be http/https, got {parsed.scheme!r}"
        )
    host = parsed.hostname
    if not host:
        raise QualityMindClientError("QUALITYMIND_BASE_URL has no host")

    try:
        resolved = {info[4][0] for info in socket.getaddrinfo(host, None)}
    except socket.gaierror as exc:
        raise QualityMindClientError(f"Cannot resolve QualityMind host {host!r}") from exc

    for addr in resolved:
        try:
            ip = ipaddress.ip_address(addr)
        except ValueError:
            continue
        if ip.is_loopback:
            continue
        if ip.is_link_local or ip.is_reserved or ip.is_multicast:
            raise QualityMindClientError(
                f"QUALITYMIND_BASE_URL resolves to a disallowed address ({addr})"
            )


def _payload_for(endpoint: str, escalation: RcaEscalation) -> dict[str, Any] | None:
    if endpoint == "/quality/five-why":
        return {
            "problem_statement": escalation.problem_statement,
            "component": escalation.component,
        }
    if endpoint == "/quality/draft-8d":
        return {
            "problem_statement": escalation.problem_statement,
            "component": escalation.component,
        }
    return None


def _post_json(
    url: str,
    payload: dict[str, Any],
    headers: dict[str, str],
    timeout: float,
    retries: int,
) -> dict[str, Any]:
    timeout_cfg = httpx.Timeout(connect=5.0, read=timeout, write=timeout, pool=5.0)
    last_exc: Exception | None = None
    for attempt in range(retries + 1):
        try:
            with httpx.Client(timeout=timeout_cfg) as client:
                response = client.post(url, json=payload, headers=headers)
                if response.status_code in _RETRYABLE_STATUS and attempt < retries:
                    last_exc = QualityMindClientError(
                        f"QualityMind returned {response.status_code}"
                    )
                    time.sleep(0.5 * (attempt + 1))
                    continue
                response.raise_for_status()
                return response.json()
        except httpx.HTTPStatusError as exc:
            raise QualityMindClientError(
                f"QualityMind escalation failed with HTTP {exc.response.status_code}"
            ) from exc
        except httpx.HTTPError as exc:
            last_exc = exc
            if attempt < retries:
                time.sleep(0.5 * (attempt + 1))
                continue
            raise QualityMindClientError("QualityMind escalation request failed") from exc
    raise QualityMindClientError("QualityMind escalation request failed") from last_exc


def _resolve(base_url: str | None, api_key: str | None) -> tuple[str, dict[str, str]]:
    url_base = (base_url or QUALITYMIND_BASE_URL).rstrip("/")
    if not url_base:
        raise QualityMindClientError("QUALITYMIND_BASE_URL is not configured")
    _validate_url(url_base)
    headers: dict[str, str] = {"Content-Type": "application/json"}
    key = api_key or QUALITYMIND_API_KEY
    if key:
        headers["X-API-Key"] = key
    return url_base, headers


def execute_escalation(
    escalation: RcaEscalation,
    base_url: str | None = None,
    api_key: str | None = None,
    timeout: float = 30.0,
    retries: int = 1,
) -> dict[str, dict[str, Any]]:
    """Drive every endpoint in escalation.target_endpoints."""
    url_base, headers = _resolve(base_url, api_key)
    endpoints = list(dict.fromkeys(escalation.target_endpoints or ["/quality/five-why"]))

    results: dict[str, dict[str, Any]] = {}
    attempted = 0
    failed = 0
    for endpoint in endpoints:
        payload = _payload_for(endpoint, escalation)
        if payload is None or endpoint not in _SUPPORTED_ENDPOINTS:
            results[endpoint] = {"status": "skipped", "detail": "unsupported target endpoint"}
            continue
        attempted += 1
        try:
            response = _post_json(f"{url_base}{endpoint}", payload, headers, timeout, retries)
            results[endpoint] = {"status": "ok", "response": response}
        except QualityMindClientError as exc:
            failed += 1
            results[endpoint] = {"status": "error", "detail": str(exc)}

    if attempted and failed == attempted:
        raise QualityMindClientError("All QualityMind escalation endpoints failed")
    return results
