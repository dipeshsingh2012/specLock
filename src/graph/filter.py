"""
SpecLock Deterministic Constraint Pruning Engine.
Stage 1: Filters candidates via strict bipartite graph relations guaranteeing 0% compatibility errors.
"""

from typing import Dict, List, Optional, Any, Set
from pathlib import Path
import time

from config import settings
from .schema import MachineNode, AccessoryNode
from .base import FilterResult, GraphEngine
from .builder import (
    build_graph,
    get_machine,
    get_accessory,
    get_machine_specs,
)


def is_accessory_compatible(
    accessory: AccessoryNode,
    machine_specs: Dict[str, str],
    target_voltage: Optional[str] = None,
) -> bool:
    """
    Evaluates physical and electrical compatibility constraints between an accessory
    and a machine's specifications.

    Compatibility Rules:
    1. Universal Rule: If an accessory constraint is 'universal', it fits all machines.
    2. Electrical Rule: Voltage must match the machine's voltage (or target regional checkout voltage).
    3. Physical Rule: Exact match required on collar_diameter, group_head_type, series, and steam_wand_type.
    """
    effective_voltage = target_voltage or machine_specs.get("voltage")

    for spec_type, required_val in accessory.fits.items():
        # 1. Universal fit pass-through (e.g. knock boxes, cleaning tablets, tamping mats)
        if required_val == "universal":
            continue

        # 2. Voltage / electrical verification
        if spec_type == "voltage":
            if effective_voltage and required_val != effective_voltage:
                return False
            continue

        # 3. Physical hardware constraints
        if spec_type in machine_specs:
            machine_val = machine_specs[spec_type]
            if machine_val != required_val:
                return False
        else:
            # Accessory requires a specific constraint that the machine does not have
            return False

    return True


class InMemoryGraphEngine:
    """
    High-performance in-memory implementation of the GraphEngine protocol.
    Uses inverted graph predecessor lookups to achieve sub-millisecond pruning
    even across large accessory catalogs.
    """

    def __init__(
        self,
        graph: Optional[Any] = None,
        catalog_path: Optional[Path] = None,
    ):
        self.graph = graph if graph is not None else build_graph(catalog_path=catalog_path)
        # Pre-cache accessory dictionary for O(1) attribute access
        self._accessories_by_id: Dict[str, AccessoryNode] = {
            node_id: attributes["data"]
            for node_id, attributes in self.graph.nodes(data=True)
            if attributes.get("node_type") == "accessory"
        }

    def get_machine(self, machine_id: str) -> Optional[MachineNode]:
        """Retrieves a machine node by ID."""
        return get_machine(self.graph, machine_id)

    def get_accessory(self, accessory_id: str) -> Optional[AccessoryNode]:
        """Retrieves an accessory node by ID."""
        return self._accessories_by_id.get(accessory_id)

    def get_all_accessories(self) -> List[AccessoryNode]:
        """Returns all accessories present in the graph catalog."""
        return list(self._accessories_by_id.values())

    def get_all_machines(self) -> List[MachineNode]:
        """Returns all machines present in the graph catalog."""
        return [
            attributes["data"]
            for _, attributes in self.graph.nodes(data=True)
            if attributes.get("node_type") == "machine" and "data" in attributes
        ]

    def _get_candidates_for_spec(self, spec_type: str, spec_value: Optional[str]) -> Set[str]:
        """
        Finds accessory IDs that match a given specification constraint or are universal.
        Domain-agnostic: works across collar_diameter, tray_size, mount_type, chuck_size, etc.
        """
        if not spec_value:
            return set(self._accessories_by_id.keys())

        matching_node = f"SPEC_{spec_type}_{spec_value}".upper()
        universal_node = f"SPEC_{spec_type}_UNIVERSAL".upper()

        candidate_nodes: Set[str] = set()
        if self.graph.has_node(matching_node):
            candidate_nodes.update(self.graph.predecessors(matching_node))
        if self.graph.has_node(universal_node):
            candidate_nodes.update(self.graph.predecessors(universal_node))

        # Filter strictly for accessory IDs, ignoring machine nodes connected to the spec
        accessory_candidates: Set[str] = set()
        for node_id in candidate_nodes:
            if node_id in self._accessories_by_id:
                accessory_candidates.add(node_id)

        return accessory_candidates

    def filter_compatible_accessories(
        self,
        machine_id: str,
        target_voltage: Optional[str] = None,
        category: Optional[str] = None,
        primary_spec_key: Optional[str] = None,
    ) -> FilterResult:
        """
        Stage 1 Deterministic Pruning: Traverses graph specifications and filters
        the candidate pool to guarantee zero false-positive compatibility returns.
        Works across any appliance or hardware domain.
        """
        start_time = time.perf_counter()

        machine = self.get_machine(machine_id)
        if not machine:
            raise ValueError(f"Machine with ID '{machine_id}' not found in compatibility graph.")

        machine_specs = get_machine_specs(self.graph, machine_id)

        # Resolve primary constraint key (e.g. collar_diameter, tray_size, mount_type)
        spec_key = primary_spec_key or settings.primary_spec_key
        candidate_ids = self._get_candidates_for_spec(spec_key, machine_specs.get(spec_key))

        # Filter candidate pool against all constraints
        compatible: List[AccessoryNode] = []
        for acc_id in candidate_ids:
            accessory = self._accessories_by_id.get(acc_id)
            if not accessory or (category and accessory.category != category):
                continue

            if is_accessory_compatible(accessory, machine_specs, target_voltage):
                compatible.append(accessory)

        elapsed_ms = (time.perf_counter() - start_time) * 1000.0

        return FilterResult(
            machine_id=machine_id,
            compatible_accessories=compatible,
            total_evaluated=len(candidate_ids),
            total_passed=len(compatible),
            total_rejected=len(candidate_ids) - len(compatible),
            latency_ms=round(elapsed_ms, 3),
        )


def filter_candidates(
    graph: Any,
    machine_id: str,
    target_voltage: Optional[str] = None,
    category: Optional[str] = None,
    primary_spec_key: Optional[str] = None,
) -> FilterResult:
    """
    Convenience function to run Stage 1 deterministic pruning on an existing graph instance.
    """
    engine = InMemoryGraphEngine(graph=graph)
    return engine.filter_compatible_accessories(
        machine_id=machine_id,
        target_voltage=target_voltage,
        category=category,
        primary_spec_key=primary_spec_key,
    )

