"""
Abstract interface and standardized return models for SpecLock graph engines.
Enables seamless drop-in swappability between in-memory NetworkX and enterprise Neo4j.
"""

from typing import Protocol, List, Optional, runtime_checkable
from pydantic import BaseModel, Field

from .schema import MachineNode, AccessoryNode


class FilterResult(BaseModel):
    """
    Standardized result emitted by Stage 1 deterministic constraint pruning.
    """
    machine_id: str = Field(..., description="Query machine identifier")
    compatible_accessories: List[AccessoryNode] = Field(
        default_factory=list,
        description="Filtered list of physically and electrically compatible accessories"
    )
    total_evaluated: int = Field(..., description="Total accessory catalog candidates evaluated")
    total_passed: int = Field(..., description="Number of accessories that met 100% of constraints")
    total_rejected: int = Field(..., description="Number of accessories dropped due to incompatibility")
    latency_ms: float = Field(..., description="Graph traversal pruning duration in milliseconds")


@runtime_checkable
class GraphEngine(Protocol):
    """
    Protocol defining the required contract for any graph backend (NetworkX, Neo4j, etc.).
    """

    def get_machine(self, machine_id: str) -> Optional[MachineNode]:
        """Retrieve machine details by ID."""
        ...

    def get_accessory(self, accessory_id: str) -> Optional[AccessoryNode]:
        """Retrieve accessory details by ID."""
        ...

    def get_all_accessories(self) -> List[AccessoryNode]:
        """Return all accessories currently present in the catalog."""
        ...

    def filter_compatible_accessories(
        self,
        machine_id: str,
        target_voltage: Optional[str] = None,
        category: Optional[str] = None,
        primary_spec_key: Optional[str] = None,
    ) -> FilterResult:
        """
        Execute deterministic constraint pruning to guarantee 0% false-positive fitment errors.
        """
        ...

