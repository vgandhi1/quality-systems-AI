"""Tests for policy search backends."""

from __future__ import annotations

import pytest

from warranty.policy_search import (
    KeywordPolicySearch,
    QdrantPolicySearch,
    get_policy_search_backend,
    keyword_search,
)

MANUAL = {
    "chunks": [
        {
            "id": "SB-1",
            "text": "MAF sensor covered",
            "components": ["mass_airflow_sensor"],
            "metadata": {"model_year": [2021], "vehicle_model": ["Civic"]},
        }
    ]
}


def test_keyword_search_finds_component() -> None:
    hits = keyword_search(MANUAL, "mass_airflow_sensor", 2021, "Civic")
    assert len(hits) == 1
    assert hits[0]["id"] == "SB-1"


def test_keyword_search_filters_year() -> None:
    hits = keyword_search(MANUAL, "mass_airflow_sensor", 2019, "Civic")
    assert hits == []


def test_get_backend_defaults_to_keyword() -> None:
    backend = get_policy_search_backend()
    assert isinstance(backend, KeywordPolicySearch)


def test_qdrant_stub_without_url_raises() -> None:
    backend = QdrantPolicySearch()
    with pytest.raises(NotImplementedError, match="Qdrant"):
        backend.search(MANUAL, "mass_airflow_sensor")
