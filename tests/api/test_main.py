"""
Unit and integration tests corresponding 1:1 to src/api/main.py:
- GET /: Root service metadata and documentation pointer
- Lifespan context manager startup and shutdown lifecycle
- OpenAPI specification metadata validation
"""

import pytest
from fastapi.testclient import TestClient
from api.main import app, lifespan
from graph.filter import InMemoryGraphEngine


def test_root_endpoint(client: TestClient):
    """Verify GET / returns service metadata and documentation pointers."""
    response = client.get("/")
    assert response.status_code == 200

    data = response.json()
    assert data["service"] == "SpecLock"
    assert data["version"] == "0.1.0"
    assert data["docs_url"] == "/docs"
    assert data["openapi_url"] == "/openapi.json"


def test_root_health_endpoint(client: TestClient):
    """Verify root-level GET /health returns operational diagnostics."""
    response = client.get("/health")
    assert response.status_code == 200

    data = response.json()
    assert data["status"] == "ok"
    assert data["brand"] == "Breville"
    assert data["total_machines"] == 12
    assert data["total_accessories"] == 40
    assert data["total_specifications"] == 18


def test_swagger_ui_endpoint(client: TestClient):
    """Verify Swagger UI interactive documentation (/docs) returns HTTP 200."""
    response = client.get("/docs")
    assert response.status_code == 200
    assert "swagger-ui" in response.text.lower() or "swagger" in response.text.lower()


def test_redoc_endpoint(client: TestClient):
    """Verify ReDoc interactive documentation (/redoc) returns HTTP 200."""
    response = client.get("/redoc")
    assert response.status_code == 200
    assert "redoc" in response.text.lower()


def test_openapi_schema(client: TestClient):
    """Verify OpenAPI JSON schema includes metadata, operation IDs, tags, and status responses."""
    response = client.get("/openapi.json")
    assert response.status_code == 200

    schema = response.json()
    # 1. Info & metadata
    assert schema["info"]["title"] == "SpecLock Recommendation Engine"
    assert schema["info"]["version"] == "0.1.0"
    assert "contact" in schema["info"]
    assert schema["info"]["contact"]["name"] == "Dipesh Singh"
    assert "license" in schema["info"]
    assert schema["info"]["license"]["name"] == "MIT"

    # 2. Servers & tags
    assert len(schema["servers"]) > 0
    assert schema["servers"][0]["url"] == "/"
    tag_names = [t["name"] for t in schema.get("tags", [])]
    assert "recommendations" in tag_names
    assert "system" in tag_names

    # 3. Paths & operation IDs
    assert "/health" in schema["paths"]
    assert "/api/v1/recommend/compatible" in schema["paths"]
    assert "/" in schema["paths"]

    rec_op = schema["paths"]["/api/v1/recommend/compatible"]["get"]
    assert rec_op["operationId"] == "getCompatibleRecommendations"
    assert "200" in rec_op["responses"]
    assert "404" in rec_op["responses"]
    assert "503" in rec_op["responses"]

    health_op = schema["paths"]["/health"]["get"]
    assert health_op["operationId"] == "getSystemHealth"
    assert "200" in health_op["responses"]
    assert "503" in health_op["responses"]

    root_op = schema["paths"]["/"]["get"]
    assert root_op["operationId"] == "getRootInfo"

    # 4. Component schemas
    schemas = schema["components"]["schemas"]
    assert "ErrorResponse" in schemas
    assert "HealthResponse" in schemas
    assert "AccessoryItem" in schemas
    assert "RecommendationResponse" in schemas



@pytest.mark.anyio
async def test_lifespan_initialization():
    """Verify lifespan context manager attaches InMemoryGraphEngine and CatalogEmbeddingCache to app.state."""
    from ranker.encoder import CatalogEmbeddingCache

    test_app = app
    async with lifespan(test_app):
        assert hasattr(test_app.state, "graph_engine")
        assert isinstance(test_app.state.graph_engine, InMemoryGraphEngine)
        assert hasattr(test_app.state, "encoder")
        assert isinstance(test_app.state.encoder, CatalogEmbeddingCache)
        assert test_app.state.encoder.accessory_cache_size > 0
        assert test_app.state.encoder.machine_cache_size > 0


def test_cors_headers(client: TestClient):
    """Verify CORS middleware injects Allow-Origin headers for Swagger UI requests."""
    response = client.get("/", headers={"Origin": "http://127.0.0.1:8000"})
    assert response.status_code == 200
    assert response.headers.get("access-control-allow-origin") == "http://127.0.0.1:8000"


