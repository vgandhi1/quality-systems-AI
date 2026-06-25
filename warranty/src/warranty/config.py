"""Environment-driven configuration for the warranty adjudication POC."""

from __future__ import annotations

import os
import sys
from pathlib import Path

# src/warranty/config.py -> warranty project root
PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_WORKSPACE = PROJECT_ROOT / "workspace"
MODELS_DIR = PROJECT_ROOT / "models"

LOCALHOST_HOSTS = frozenset({"127.0.0.1", "localhost"})


def get_environment() -> str:
    return os.environ.get("WARRANTY_ENVIRONMENT", "development").strip().lower()


def get_api_key() -> str | None:
    value = os.environ.get("WARRANTY_API_KEY")
    return value if value else None


def get_api_host() -> str:
    return os.environ.get("WARRANTY_API_HOST", "127.0.0.1").strip()


def get_api_port() -> int:
    return int(os.environ.get("WARRANTY_API_PORT", "8080"))


def get_cors_origins() -> list[str]:
    raw = os.environ.get("WARRANTY_CORS_ORIGINS", "").strip()
    if not raw:
        return []
    return [origin.strip() for origin in raw.split(",") if origin.strip()]


def auth_required() -> bool:
    """True when protected routes must present X-API-Key."""
    if get_environment() == "production":
        return True
    return get_api_host() not in LOCALHOST_HOSTS


def get_llm_temperature() -> float:
    return float(os.environ.get("WARRANTY_LLM_TEMPERATURE", "0"))


def get_llm_timeout() -> float:
    return float(os.environ.get("WARRANTY_LLM_TIMEOUT_SECONDS", "30"))


def get_max_context_tokens() -> int:
    return int(os.environ.get("MAX_CONTEXT_TOKENS", "8000"))


def get_max_completion_tokens() -> int:
    return int(os.environ.get("MAX_COMPLETION_TOKENS", "4000"))


def get_max_input_tokens() -> int:
    return int(os.environ.get("MAX_INPUT_TOKENS", "8000"))


def validate_api_config() -> None:
    """Fail fast on unsafe LAN/production configuration."""
    env = get_environment()
    host = get_api_host()
    api_key = get_api_key()

    if env == "production" and not api_key:
        print(
            "ERROR: WARRANTY_API_KEY is required when WARRANTY_ENVIRONMENT=production",
            file=sys.stderr,
        )
        raise SystemExit(1)

    if host not in LOCALHOST_HOSTS and not api_key:
        print(
            "ERROR: WARRANTY_API_KEY is required when WARRANTY_API_HOST is not localhost "
            f"(current: {host}). See DEV-LAN-ACCESS.md.",
            file=sys.stderr,
        )
        raise SystemExit(1)


# Module-level aliases for callers that import constants at load time.
ENVIRONMENT = get_environment()
API_KEY = get_api_key()
API_HOST = get_api_host()
API_PORT = get_api_port()
WORKSPACE_DIR = Path(os.environ.get("WARRANTY_WORKSPACE", str(DEFAULT_WORKSPACE)))

QUALITYMIND_BASE_URL = os.environ.get("QUALITYMIND_BASE_URL", "").rstrip("/")
QUALITYMIND_API_KEY = os.environ.get("QUALITYMIND_API_KEY", "")

POLICY_SEARCH_BACKEND = os.environ.get("WARRANTY_POLICY_BACKEND", "keyword").strip().lower()
QDRANT_URL = os.environ.get("WARRANTY_QDRANT_URL", "").rstrip("/")

METRICS_PATH = MODELS_DIR / "metrics.json"
MANIFEST_PATH = MODELS_DIR / "manifest.json"
