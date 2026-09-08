"""
Pydantic v2 schemas for the SpecLock HTTP API:
- HealthResponse: System diagnostics and catalog inventory metrics
- AccessoryItem: Serialized representation of a compatible accessory
- RecommendationResponse: Pruned recommendations with fitment metadata
- ErrorResponse: Standardized HTTP error payload for client feedback
"""

from typing import Dict, List, Optional
from pydantic import BaseModel, Field, ConfigDict


class ErrorResponse(BaseModel):
    """Standardized error payload returned across API endpoints."""

    detail: str = Field(..., description="Descriptive explanation of the error condition")

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "detail": "Machine with ID 'M_NON_EXISTENT' not found in compatibility graph."
                }
            ]
        }
    )


class HealthResponse(BaseModel):
    """Health check and catalog topology diagnostics."""

    status: str = Field(default="ok", description="Service health status")
    brand: str = Field(..., description="Target hardware ecosystem brand")
    total_machines: int = Field(ge=0, description="Total machines loaded in graph")
    total_accessories: int = Field(ge=0, description="Total accessories loaded in graph")
    total_specifications: int = Field(ge=0, description="Total specification nodes in graph")

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "status": "ok",
                    "brand": "Breville",
                    "total_machines": 12,
                    "total_accessories": 40,
                    "total_specifications": 18,
                }
            ]
        }
    )


class AccessoryItem(BaseModel):
    """Serialized projection of a compatible accessory returned to clients."""

    id: str = Field(..., description="Unique accessory identifier")
    name: str = Field(..., description="Accessory product display name")
    sku: str = Field(..., description="Manufacturer SKU")
    category: str = Field(..., description="Product category taxonomy")
    price: float = Field(ge=0.0, description="MSRP price in USD")
    margin_rate: float = Field(ge=0.0, le=1.0, description="Gross margin rate percentage")
    fits: Dict[str, str] = Field(..., description="Physical and electrical fitment parameters")
    description: str = Field(..., description="Product marketing summary")
    semantic_similarity: Optional[float] = Field(
        default=None,
        ge=-1.0,
        le=1.0,
        description="Stage 2 cosine similarity score between query/context and accessory",
    )
    composite_score: Optional[float] = Field(
        default=None,
        description="Stage 2 final composite ranking score: alpha * similarity + beta * margin_rate",
    )

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "id": "A_FUNNEL_MAG_54",
                    "name": "54mm Magnetic Dosing Funnel",
                    "sku": "ACC-DF-54-MAG",
                    "category": "workflow_tools",
                    "price": 24.95,
                    "margin_rate": 0.62,
                    "fits": {
                        "collar_diameter": "54mm",
                        "voltage": "universal",
                    },
                    "description": "Anodized aluminum magnetic dosing collar designed exclusively for 54mm Breville portafilters.",
                    "semantic_similarity": 0.6125,
                    "composite_score": 0.6148,
                }
            ]
        }
    )


class RecommendationResponse(BaseModel):
    """Compatibility recommendations payload with Stage 1 fitment and Stage 2 ranking."""

    machine_id: str = Field(..., description="Target machine queried")
    target_voltage: Optional[str] = Field(default=None, description="Regional checkout voltage applied")
    category: Optional[str] = Field(default=None, description="Category filter applied, if any")
    query: Optional[str] = Field(
        default=None,
        description="User search intent query applied during Stage 2 ranking",
    )
    alpha: Optional[float] = Field(
        default=None,
        ge=0.0,
        le=1.0,
        description="Stage 2 semantic relevance weight applied",
    )
    beta: Optional[float] = Field(
        default=None,
        ge=0.0,
        le=1.0,
        description="Stage 2 profit margin weight applied",
    )
    total_compatible: int = Field(ge=0, description="Count of accessories passing all constraints")
    total_evaluated: int = Field(ge=0, description="Total candidate accessories evaluated in Stage 1")
    total_rejected: int = Field(ge=0, description="Count of incompatible accessories pruned")
    latency_ms: float = Field(ge=0.0, description="Stage 1 traversal latency in milliseconds")
    items: List[AccessoryItem] = Field(default_factory=list, description="List of compatible accessories")

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "machine_id": "M_BES870XL",
                    "target_voltage": None,
                    "category": None,
                    "query": None,
                    "alpha": 0.7,
                    "beta": 0.3,
                    "total_compatible": 28,
                    "total_evaluated": 29,
                    "total_rejected": 1,
                    "latency_ms": 0.068,
                    "items": [
                        {
                            "id": "A_FUNNEL_PRESS_54",
                            "name": "54mm Grinder Trigger Dosing Funnel",
                            "sku": "ACC-DF-54-TRIG",
                            "category": "workflow_tools",
                            "price": 29.95,
                            "margin_rate": 0.58,
                            "fits": {
                                "collar_diameter": "54mm",
                                "voltage": "universal",
                            },
                            "description": "Hands-free dosing funnel that activates the integrated grinder cradle on Barista Express and Barista Pro 54mm machines.",
                            "semantic_similarity": 0.6125,
                            "composite_score": 0.6028,
                        }
                    ],
                }
            ]
        }
    )

