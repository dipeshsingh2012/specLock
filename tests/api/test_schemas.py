"""
Unit tests corresponding 1:1 to src/api/schemas.py:
- HealthResponse model defaults and validations
- AccessoryItem model constraints and bounds
- RecommendationResponse payload structure and statistics
- ErrorResponse model validation and OpenAPI examples
"""

import pytest
from pydantic import ValidationError
from api.schemas import HealthResponse, AccessoryItem, RecommendationResponse, ErrorResponse


def test_health_response_schema():
    """Verify HealthResponse model sets expected defaults and validates node counts."""
    health = HealthResponse(
        brand="Breville",
        total_machines=12,
        total_accessories=40,
        total_specifications=18,
    )
    assert health.status == "ok"
    assert health.brand == "Breville"
    assert health.total_machines == 12
    assert health.total_accessories == 40
    assert health.total_specifications == 18

    # Verify custom brand for general appliances (e.g. Bosch)
    custom_health = HealthResponse(
        brand="Bosch",
        total_machines=5,
        total_accessories=15,
        total_specifications=8,
    )
    assert custom_health.brand == "Bosch"

    # Negative count must raise ValidationError
    with pytest.raises(ValidationError):
        HealthResponse(
            brand="Breville",
            total_machines=-1,
            total_accessories=40,
            total_specifications=18,
        )


def test_accessory_item_schema():
    """Verify AccessoryItem enforces margin bounds and price constraints."""
    item = AccessoryItem(
        id="A_TEST",
        name="Test Accessory",
        sku="ACC-TEST",
        category="workflow_tools",
        price=29.95,
        margin_rate=0.65,
        fits={"collar_diameter": "54mm"},
        description="High precision accessory.",
    )
    assert item.id == "A_TEST"
    assert item.price == 29.95
    assert item.margin_rate == 0.65

    # Margin rate > 1.0 must fail
    with pytest.raises(ValidationError):
        AccessoryItem(
            id="A_BAD",
            name="Bad Accessory",
            sku="BAD-SKU",
            category="workflow_tools",
            price=29.95,
            margin_rate=1.20,
            fits={"collar_diameter": "54mm"},
            description="Invalid margin",
        )

    # Negative price must fail
    with pytest.raises(ValidationError):
        AccessoryItem(
            id="A_BAD_PRICE",
            name="Bad Price",
            sku="BAD-PRICE",
            category="workflow_tools",
            price=-5.0,
            margin_rate=0.50,
            fits={},
            description="Negative price",
        )


def test_recommendation_response_schema():
    """Verify RecommendationResponse validates counts, latency, and item collections."""
    item = AccessoryItem(
        id="A_KNOCK_BOX",
        name="Mini Knock Box",
        sku="ACC-KB",
        category="maintenance",
        price=30.00,
        margin_rate=0.70,
        fits={"collar_diameter": "universal"},
        description="Universal knock box",
    )

    response = RecommendationResponse(
        machine_id="M_BES870XL",
        target_voltage="120V",
        category="maintenance",
        total_compatible=1,
        total_evaluated=10,
        total_rejected=9,
        latency_ms=0.45,
        items=[item],
    )

    assert response.machine_id == "M_BES870XL"
    assert response.target_voltage == "120V"
    assert response.category == "maintenance"
    assert response.total_compatible == 1
    assert response.total_evaluated == 10
    assert response.total_rejected == 9
    assert response.latency_ms == 0.45
    assert len(response.items) == 1
    assert response.items[0].sku == "ACC-KB"

    # Negative latency must fail validation
    with pytest.raises(ValidationError):
        RecommendationResponse(
            machine_id="M_BES870XL",
            total_compatible=0,
            total_evaluated=0,
            total_rejected=0,
            latency_ms=-1.0,
        )


def test_accessory_item_stage2_scoring_bounds():
    """Verify AccessoryItem accepts and bounds Stage 2 score fields."""
    item = AccessoryItem(
        id="A_TEST_SCORED",
        name="Scored Item",
        sku="ACC-SCORE",
        category="workflow_tools",
        price=35.0,
        margin_rate=0.55,
        fits={"collar_diameter": "54mm"},
        description="High precision item.",
        semantic_similarity=0.87,
        composite_score=0.774,
    )
    assert item.semantic_similarity == 0.87
    assert item.composite_score == 0.774

    # Similarity > 1.0 must fail validation
    with pytest.raises(ValidationError):
        AccessoryItem(
            id="A_ERR_SIM",
            name="Error Sim",
            sku="ACC-ERR-SIM",
            category="workflow_tools",
            price=35.0,
            margin_rate=0.55,
            fits={},
            description="Bad similarity",
            semantic_similarity=1.1,
        )

    # Similarity < -1.0 must fail validation
    with pytest.raises(ValidationError):
        AccessoryItem(
            id="A_ERR_SIM2",
            name="Error Sim 2",
            sku="ACC-ERR-SIM2",
            category="workflow_tools",
            price=35.0,
            margin_rate=0.55,
            fits={},
            description="Bad similarity",
            semantic_similarity=-1.5,
        )


def test_recommendation_response_stage2_metadata():
    """Verify RecommendationResponse includes Stage 2 query and weight metadata."""
    response = RecommendationResponse(
        machine_id="M_BES870XL",
        query="precision dosing funnel",
        alpha=0.75,
        beta=0.25,
        total_compatible=3,
        total_evaluated=15,
        total_rejected=12,
        latency_ms=1.2,
    )
    assert response.query == "precision dosing funnel"
    assert response.alpha == 0.75
    assert response.beta == 0.25

    # Out-of-bounds alpha or beta must raise ValidationError
    with pytest.raises(ValidationError):
        RecommendationResponse(
            machine_id="M_BES870XL",
            alpha=-0.1,
            total_compatible=0,
            total_evaluated=0,
            total_rejected=0,
            latency_ms=0.5,
        )

    with pytest.raises(ValidationError):
        RecommendationResponse(
            machine_id="M_BES870XL",
            beta=1.5,
            total_compatible=0,
            total_evaluated=0,
            total_rejected=0,
            latency_ms=0.5,
        )


def test_error_response_schema():
    """Verify ErrorResponse model validates detail field and exposes OpenAPI schema examples."""
    error = ErrorResponse(detail="Resource not found")
    assert error.detail == "Resource not found"

    with pytest.raises(ValidationError):
        ErrorResponse()  # type: ignore[call-arg]

    schema = ErrorResponse.model_json_schema()
    assert "examples" in schema
    assert schema["examples"][0]["detail"] == "Machine with ID 'M_NON_EXISTENT' not found in compatibility graph."


def test_schemas_have_openapi_examples():
    """Verify all public schemas expose OpenAPI JSON schema examples."""
    for model in (HealthResponse, AccessoryItem, RecommendationResponse, ErrorResponse):
        schema = model.model_json_schema()
        assert "examples" in schema, f"Missing OpenAPI examples in {model.__name__}"
        assert len(schema["examples"]) > 0

