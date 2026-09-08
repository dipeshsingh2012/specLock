"""
SpecLock Graph Builder: Constructs the bipartite knowledge graph via NetworkX.
"""

from pathlib import Path
from typing import Dict, List, Optional, Any, Set
import json
import networkx as nx

from config import settings
from .schema import MachineNode, AccessoryNode, SpecNode, CatalogData


def load_catalog(catalog_path: Optional[Path] = None) -> CatalogData:
    """
    Loads and validates the catalog JSON feed into strongly-typed Pydantic models.
    """
    path = catalog_path or settings.raw_catalog_path
    if not path.exists():
        raise FileNotFoundError(f"Catalog file not found at: {path}")

    with open(path, "r", encoding="utf-8") as f:
        raw_data = json.load(f)

    return CatalogData(**raw_data)


def build_graph(
    catalog_path: Optional[Path] = None,
    catalog_data: Optional[CatalogData] = None,
) -> nx.DiGraph:
    """
    Constructs an in-memory bipartite directed graph connecting Machines and
    Accessories through Specification constraint nodes.

    Edge Formulation:
    - (Machine)-[:REQUIRES_SPEC]->(Specification)
    - (Accessory)-[:FITS_SPEC]->(Specification)
    """
    catalog = catalog_data or load_catalog(catalog_path)
    G = nx.DiGraph(
        name="SpecLock_Compatibility_Graph",
        brand=catalog.brand,
    )

    # 1. Ingest Machine Nodes and their specification requirement edges
    for machine in catalog.machines:
        G.add_node(
            machine.node_id,
            node_type="machine",
            name=machine.name,
            sku=machine.sku,
            series=machine.series,
            price=machine.price,
            specs=machine.specs,
            description=machine.description,
            data=machine,
        )

        for spec_type, spec_val in machine.specs.items():
            spec_node = SpecNode(spec_type=spec_type, spec_value=spec_val)
            if not G.has_node(spec_node.node_id):
                G.add_node(
                    spec_node.node_id,
                    node_type="specification",
                    spec_type=spec_type,
                    spec_value=spec_val,
                )
            G.add_edge(machine.node_id, spec_node.node_id, relation="REQUIRES_SPEC")

    # 2. Ingest Accessory Nodes and their fitment edges
    for accessory in catalog.accessories:
        G.add_node(
            accessory.node_id,
            node_type="accessory",
            name=accessory.name,
            sku=accessory.sku,
            category=accessory.category,
            price=accessory.price,
            margin_rate=accessory.margin_rate,
            fits=accessory.fits,
            description=accessory.description,
            data=accessory,
        )

        for spec_type, spec_val in accessory.fits.items():
            spec_node = SpecNode(spec_type=spec_type, spec_value=spec_val)
            if not G.has_node(spec_node.node_id):
                G.add_node(
                    spec_node.node_id,
                    node_type="specification",
                    spec_type=spec_type,
                    spec_value=spec_val,
                )
            G.add_edge(accessory.node_id, spec_node.node_id, relation="FITS_SPEC")

    return G


def get_graph_summary(graph: nx.DiGraph) -> Dict[str, Any]:
    """
    Returns counts of graph nodes and edges grouped by category.
    """
    # 1. Count nodes by type using explicit, readable variables
    machine_count = 0
    accessory_count = 0
    specification_count = 0

    for node_id, attributes in graph.nodes(data=True):
        node_type = attributes.get("node_type")
        if node_type == "machine":
            machine_count += 1
        elif node_type == "accessory":
            accessory_count += 1
        elif node_type == "specification":
            specification_count += 1

    # 2. Count directed relationships by type
    requires_spec_count = 0
    fits_spec_count = 0

    for source_node, target_node, edge_attributes in graph.edges(data=True):
        relation = edge_attributes.get("relation")
        if relation == "REQUIRES_SPEC":
            requires_spec_count += 1
        elif relation == "FITS_SPEC":
            fits_spec_count += 1

    return {
        "brand": graph.graph.get("brand", "Generic"),
        "total_nodes": graph.number_of_nodes(),
        "total_edges": graph.number_of_edges(),
        "machine_count": machine_count,
        "accessory_count": accessory_count,
        "specification_count": specification_count,
        "requires_spec_edge_count": requires_spec_count,
        "fits_spec_edge_count": fits_spec_count,
    }


def get_machine(graph: nx.DiGraph, machine_id: str) -> Optional[MachineNode]:
    """
    Retrieves the typed MachineNode for a given machine_id if present.
    """
    if graph.has_node(machine_id) and graph.nodes[machine_id].get("node_type") == "machine":
        return graph.nodes[machine_id].get("data")
    return None


def get_accessory(graph: nx.DiGraph, accessory_id: str) -> Optional[AccessoryNode]:
    """
    Retrieves the typed AccessoryNode for a given accessory_id if present.
    """
    if graph.has_node(accessory_id) and graph.nodes[accessory_id].get("node_type") == "accessory":
        return graph.nodes[accessory_id].get("data")
    return None


def get_machine_specs(graph: nx.DiGraph, machine_id: str) -> Dict[str, str]:
    """
    Returns all required specifications for a machine by inspecting outgoing edges.
    """
    if not graph.has_node(machine_id):
        return {}

    specs: Dict[str, str] = {}
    for _, spec_node_id, edge_data in graph.out_edges(machine_id, data=True):
        if edge_data.get("relation") == "REQUIRES_SPEC":
            node_data = graph.nodes[spec_node_id]
            specs[node_data["spec_type"]] = node_data["spec_value"]
    return specs


def get_accessory_specs(graph: nx.DiGraph, accessory_id: str) -> Dict[str, str]:
    """
    Returns all fitment specifications for an accessory by inspecting outgoing edges.
    """
    if not graph.has_node(accessory_id):
        return {}

    specs: Dict[str, str] = {}
    for _, spec_node_id, edge_data in graph.out_edges(accessory_id, data=True):
        if edge_data.get("relation") == "FITS_SPEC":
            node_data = graph.nodes[spec_node_id]
            specs[node_data["spec_type"]] = node_data["spec_value"]
    return specs

