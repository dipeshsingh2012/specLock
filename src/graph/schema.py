"""
Data schemas and graph node definitions for SpecLock.
"""

from typing import Dict, List, Optional
from pydantic import BaseModel, Field


class SpecNode(BaseModel):
    """
    Represents a hardware specification node in the bipartite graph.
    Example: spec_type='collar_diameter', spec_value='54mm'
    """
    spec_type: str = Field(..., description="Specification category, e.g. collar_diameter, voltage, series")
    spec_value: str = Field(..., description="Specification value, e.g. 54mm, 58mm, 120V, universal")

    @property
    def node_id(self) -> str:
        return f"SPEC_{self.spec_type}_{self.spec_value}".upper()


class MachineNode(BaseModel):
    """
    Represents an appliance/machine node in the graph.
    """
    id: str = Field(..., description="Unique machine identifier, e.g. M_BES870XL")
    name: str = Field(..., description="Display title of the appliance")
    sku: str = Field(..., description="Manufacturer SKU")
    series: str = Field(..., description="Product series family, e.g. Barista, Bambino, Commercial_Dual")
    price: float = Field(..., ge=0.0, description="Retail price in USD")
    specs: Dict[str, str] = Field(
        default_factory=dict,
        description="Physical and electrical constraints, e.g. {'collar_diameter': '54mm', 'voltage': '120V'}"
    )
    description: Optional[str] = Field(default="", description="Product marketing and technical description")

    @property
    def node_id(self) -> str:
        return self.id


class AccessoryNode(BaseModel):
    """
    Represents an accessory node with fitment rules and economic margin rates.
    """
    id: str = Field(..., description="Unique accessory identifier, e.g. A_FUNNEL_MAG_54")
    name: str = Field(..., description="Display title of the accessory")
    sku: str = Field(..., description="Accessory SKU")
    category: str = Field(..., description="Category, e.g. portafilters, tampers, workflow_tools, maintenance")
    price: float = Field(..., ge=0.0, description="Retail selling price in USD")
    margin_rate: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Gross margin percentage (COGS vs Retail), e.g. 0.62 = 62% profit margin"
    )
    fits: Dict[str, str] = Field(
        default_factory=dict,
        description="Compatibility requirements, e.g. {'collar_diameter': '54mm', 'voltage': 'universal'}"
    )
    description: str = Field(..., description="Detailed textual description used for Stage 2 semantic embeddings")

    @property
    def node_id(self) -> str:
        return self.id


class CatalogData(BaseModel):
    """
    Root schema for validating the full catalog JSON feed.
    """
    catalog_version: str = "1.0.0"
    brand: str = "Breville"
    machines: List[MachineNode] = Field(default_factory=list)
    accessories: List[AccessoryNode] = Field(default_factory=list)

