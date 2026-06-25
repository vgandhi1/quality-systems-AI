"""Policy search backends — keyword (POC) and Qdrant stub (production target)."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from warranty.config import POLICY_SEARCH_BACKEND, QDRANT_URL


def keyword_search(
    manual: dict[str, Any],
    component: str,
    model_year: int | None = None,
    vehicle_model: str | None = None,
) -> list[dict]:
    """Metadata-filtered keyword search over policy_manual.json chunks."""
    query = component.lower()
    hits: list[dict] = []
    for chunk in manual.get("chunks", []):
        meta = chunk.get("metadata", {})
        if model_year and model_year not in meta.get("model_year", []):
            continue
        if vehicle_model and vehicle_model not in meta.get("vehicle_model", []):
            continue
        text = (chunk.get("text", "") + " " + chunk.get("id", "")).lower()
        if query in text or any(query in p.lower() for p in chunk.get("components", [])):
            hits.append(chunk)
    return hits


class PolicySearchBackend(ABC):
    @abstractmethod
    def search(
        self,
        manual: dict[str, Any],
        component: str,
        model_year: int | None = None,
        vehicle_model: str | None = None,
    ) -> list[dict]:
        ...


class KeywordPolicySearch(PolicySearchBackend):
    def search(
        self,
        manual: dict[str, Any],
        component: str,
        model_year: int | None = None,
        vehicle_model: str | None = None,
    ) -> list[dict]:
        return keyword_search(manual, component, model_year, vehicle_model)


class QdrantPolicySearch(PolicySearchBackend):
    """Stub for vector RAG — requires WARRANTY_QDRANT_URL and a deployed collection."""

    def search(
        self,
        manual: dict[str, Any],
        component: str,
        model_year: int | None = None,
        vehicle_model: str | None = None,
    ) -> list[dict]:
        if not QDRANT_URL:
            raise NotImplementedError(
                "Qdrant policy search is not configured. Set WARRANTY_QDRANT_URL "
                "or use WARRANTY_POLICY_BACKEND=keyword."
            )
        # Dev stub: fall back to keyword until Qdrant integration is implemented.
        return keyword_search(manual, component, model_year, vehicle_model)


def get_policy_search_backend() -> PolicySearchBackend:
    if POLICY_SEARCH_BACKEND == "qdrant":
        return QdrantPolicySearch()
    return KeywordPolicySearch()
