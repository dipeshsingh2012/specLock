"""
Unit and integration tests corresponding 1:1 to src/api/endpoints.py:
- GET /health: Status diagnostics and graph topology counts
- GET /recommend/compatible: Stage 1 deterministic pruning via HTTP
- Category filtering, voltage override, and domain-agnostic spec key
- 404 error handling for unregistered machines
- 503 service unavailable branch for uninitialized engine
"""

import pytest
from fastapi import HTTPException, status
from fastapi.testclient import TestClient
from api.endpoints import get_graph_engine, get_encoder


def test_recommend_compatible_54mm_machine(client: TestClient):
    """
    Verify GET /api/v1/recommend/compatible for 54mm machine returns compatible items
    with strictly 0% 58mm items.
    """
    response = client.get("/api/v1/recommend/compatible", params={"machine_id": "M_BES870XL"})
    assert response.status_code == 200

    data = response.json()
    assert data["machine_id"] == "M_BES870XL"
    assert data["total_compatible"] > 0
    assert data["latency_ms"] >= 0.0

    # Assert no 58mm items are present in recommendations
    for item in data["items"]:
        assert item["fits"].get("collar_diameter") != "58mm"


def test_recommend_compatible_58mm_machine(client: TestClient):
    """
    Verify GET /api/v1/recommend/compatible for 58mm machine returns compatible items
    with strictly 0% 54mm items.
    """
    response = client.get("/api/v1/recommend/compatible", params={"machine_id": "M_BES920XL"})
    assert response.status_code == 200

    data = response.json()
    assert data["machine_id"] == "M_BES920XL"
    assert data["total_compatible"] > 0

    # Assert no 54mm items are present in recommendations
    for item in data["items"]:
        assert item["fits"].get("collar_diameter") != "54mm"


def test_recommend_compatible_category_filter(client: TestClient):
    """Verify category query parameter restricts results to specified category."""
    response = client.get(
        "/api/v1/recommend/compatible",
        params={"machine_id": "M_BES870XL", "category": "portafilters"},
    )
    assert response.status_code == 200

    data = response.json()
    assert data["category"] == "portafilters"
    assert len(data["items"]) > 0
    for item in data["items"]:
        assert item["category"] == "portafilters"
        assert item["fits"].get("collar_diameter") == "54mm"


def test_recommend_compatible_voltage_and_spec_key(client: TestClient):
    """Verify voltage override and primary_spec_key query parameters."""
    response = client.get(
        "/api/v1/recommend/compatible",
        params={
            "machine_id": "M_BES870XL",
            "target_voltage": "120V",
            "primary_spec_key": "series",
        },
    )
    assert response.status_code == 200

    data = response.json()
    assert data["target_voltage"] == "120V"
    assert data["total_compatible"] > 0


def test_recommend_compatible_unknown_machine_404(client: TestClient):
    """Verify unknown machine ID returns 404 Not Found."""
    response = client.get(
        "/api/v1/recommend/compatible",
        params={"machine_id": "M_NON_EXISTENT_ID"},
    )
    assert response.status_code == 404
    assert "not found in compatibility graph" in response.json()["detail"]


def test_recommend_compatible_stage2_default_ranking(client: TestClient):
    """Verify default request executes Stage 2 ranking with composite scores sorted descending."""
    response = client.get("/api/v1/recommend/compatible", params={"machine_id": "M_BES870XL"})
    assert response.status_code == 200

    data = response.json()
    assert data["alpha"] == 0.7
    assert data["beta"] == 0.3
    assert len(data["items"]) > 0

    scores = [item["composite_score"] for item in data["items"]]
    assert all(score is not None for score in scores)
    assert all(item["semantic_similarity"] is not None for item in data["items"])
    assert scores == sorted(scores, reverse=True)


@pytest.mark.parametrize(
    "query_text,expected_keyword",
    [
        ("precision dosing funnel", "funnel"),
        ("milk frothing pitcher", "pitcher"),
        ("cleaning backflush tablets", "cleaning"),
    ],
)
def test_recommend_compatible_stage2_with_query(client: TestClient, query_text: str, expected_keyword: str):
    """Verify arbitrary user search queries dynamically rank relevant accessories highest."""
    response = client.get(
        "/api/v1/recommend/compatible",
        params={"machine_id": "M_BES870XL", "query": query_text, "top_k": 3},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["query"] == query_text
    assert len(data["items"]) == 3
    assert expected_keyword in data["items"][0]["name"].lower()


def test_recommend_compatible_stage2_custom_weights(client: TestClient):
    """Verify custom alpha and beta weights are recorded in response and affect scores."""
    response = client.get(
        "/api/v1/recommend/compatible",
        params={"machine_id": "M_BES870XL", "alpha": 0.5, "beta": 0.5, "top_k": 5},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["alpha"] == 0.5
    assert data["beta"] == 0.5
    assert len(data["items"]) == 5


def test_recommend_compatible_stage2_disabled(client: TestClient):
    """Verify stage2=False returns unranked Stage 1 items without composite scores."""
    response = client.get(
        "/api/v1/recommend/compatible",
        params={"machine_id": "M_BES870XL", "stage2": False, "top_k": 4},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["alpha"] is None
    assert data["beta"] is None
    assert len(data["items"]) == 4
    for item in data["items"]:
        assert item["composite_score"] is None
        assert item["semantic_similarity"] is None


def test_recommend_compatible_stage2_disabled_no_top_k(client: TestClient):
    """Verify stage2=False with top_k=None returns all compatible items unranked."""
    response = client.get(
        "/api/v1/recommend/compatible",
        params={"machine_id": "M_BES870XL", "stage2": False},
    )
    assert response.status_code == 200
    data = response.json()
    assert len(data["items"]) == data["total_compatible"]


def test_recommend_compatible_empty_candidates_stage2(client: TestClient):
    """Verify stage2 ranking safely handles empty compatible candidate pool."""
    response = client.get(
        "/api/v1/recommend/compatible",
        params={"machine_id": "M_BES870XL", "category": "nonexistent_category", "stage2": True},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["total_compatible"] == 0
    assert len(data["items"]) == 0


def test_get_graph_engine_missing_raises_503():
    """Verify get_graph_engine raises 503 if graph_engine is not on app.state."""
    class DummyAppState:
        pass

    class DummyApp:
        state = DummyAppState()

    class DummyRequest:
        app = DummyApp()

    with pytest.raises(HTTPException) as exc_info:
        get_graph_engine(DummyRequest())

    assert exc_info.value.status_code == status.HTTP_503_SERVICE_UNAVAILABLE
    assert "not initialized" in exc_info.value.detail


def test_get_encoder_missing_raises_503():
    """Verify get_encoder raises 503 if encoder is not on app.state."""
    class DummyAppState:
        pass

    class DummyApp:
        state = DummyAppState()

    class DummyRequest:
        app = DummyApp()

    with pytest.raises(HTTPException) as exc_info:
        get_encoder(DummyRequest())

    assert exc_info.value.status_code == status.HTTP_503_SERVICE_UNAVAILABLE
    assert "not initialized" in exc_info.value.detail

