"""
Unit tests corresponding 1:1 to src/graph/builder.py:
- Bipartite graph construction via build_graph()
- Graph engine protocol compliance
- Topology metrics (node counts, edge counts, node types)
- Graph inspection helper functions (get_machine, get_accessory, get_machine_specs)
- Bipartite edge integrity (REQUIRES_SPEC and FITS_SPEC relations)
"""

from graph.base import GraphEngine
from graph.builder import (
    build_graph,
    get_graph_summary,
    get_machine,
    get_accessory,
    get_machine_specs,
    get_accessory_specs,
)
from graph.filter import InMemoryGraphEngine


def test_graph_engine_satisfies_protocol(engine: InMemoryGraphEngine):
    """Verify InMemoryGraphEngine fulfills the @runtime_checkable GraphEngine protocol."""
    assert isinstance(engine, GraphEngine)


def test_graph_topology_metrics(engine: InMemoryGraphEngine):
    """Verify total nodes, edges, and entity counts match catalog expectations."""
    summary = get_graph_summary(engine.graph)

    # 12 machines + 40 accessories + 18 specifications = 70 total nodes
    assert summary["total_nodes"] == 70
    assert summary["total_edges"] == 146
    assert summary["machine_count"] == 12
    assert summary["accessory_count"] == 40
    assert summary["specification_count"] == 18
    assert summary["requires_spec_edge_count"] == 60
    assert summary["fits_spec_edge_count"] == 86


def test_graph_inspection_helpers(engine: InMemoryGraphEngine):
    """Test get_machine, get_accessory, get_machine_specs, and get_accessory_specs."""
    # Lookup existing machine
    machine = get_machine(engine.graph, "M_BES870XL")
    assert machine is not None
    assert machine.name == "Barista Express Espresso Machine"

    # Lookup non-existent machine returns None
    missing_machine = get_machine(engine.graph, "NON_EXISTENT_ID")
    assert missing_machine is None

    # Lookup existing accessory
    accessory = get_accessory(engine.graph, "A_FUNNEL_MAG_54")
    assert accessory is not None
    assert accessory.category == "workflow_tools"

    # Lookup non-existent accessory returns None
    missing_accessory = get_accessory(engine.graph, "NON_EXISTENT_ACC")
    assert missing_accessory is None

    # Verify extracted machine specs map
    machine_specs = get_machine_specs(engine.graph, "M_BES870XL")
    assert machine_specs["collar_diameter"] == "54mm"
    assert machine_specs["voltage"] == "120V"

    # Verify extracted accessory fits map
    accessory_specs = get_accessory_specs(engine.graph, "A_FUNNEL_MAG_54")
    assert accessory_specs["collar_diameter"] == "54mm"
    assert accessory_specs["voltage"] == "universal"


def test_bipartite_edge_directions(engine: InMemoryGraphEngine):
    """Verify that machines and accessories strictly point to specification nodes."""
    graph = engine.graph

    for source_node, target_node, edge_attributes in graph.edges(data=True):
        relation = edge_attributes.get("relation")
        target_data = graph.nodes[target_node]

        # All edges must point to a specification node
        assert target_data.get("node_type") == "specification"

        # Check relation consistency
        source_type = graph.nodes[source_node].get("node_type")
        if source_type == "machine":
            assert relation == "REQUIRES_SPEC"
        elif source_type == "accessory":
            assert relation == "FITS_SPEC"


def test_load_catalog_missing_file_raises_error():
    """Verify load_catalog raises FileNotFoundError when given an invalid path."""
    from pathlib import Path
    import pytest
    from graph.builder import load_catalog

    with pytest.raises(FileNotFoundError, match="Catalog file not found"):
        load_catalog(Path("/invalid/path/catalog.json"))


def test_graph_inspection_nonexistent_specs_and_wrong_types(engine: InMemoryGraphEngine):
    """Verify empty specs returned for non-existent entities and wrong node types."""
    # Specs on non-existent IDs return empty dictionaries
    assert get_machine_specs(engine.graph, "NON_EXISTENT_MACHINE") == {}
    assert get_accessory_specs(engine.graph, "NON_EXISTENT_ACCESSORY") == {}

    # Querying a machine ID with get_accessory returns None
    assert get_accessory(engine.graph, "M_BES870XL") is None

    # Querying an accessory ID with get_machine returns None
    assert get_machine(engine.graph, "A_FUNNEL_MAG_54") is None


def test_graph_summary_and_specs_with_unknown_relations_and_nodes(engine: InMemoryGraphEngine):
    """
    Verify summary and inspection functions gracefully handle graphs with
    unrecognized node types and non-specification edge relations.
    """
    test_graph = engine.graph.copy()

    # Add an unrecognized node type
    test_graph.add_node("UNKNOWN_NODE_ID", node_type="custom_type")

    # Add unrecognized edge relations
    test_graph.add_edge("UNKNOWN_NODE_ID", "M_BES870XL", relation="UNKNOWN_RELATION")
    test_graph.add_edge("M_BES870XL", "UNKNOWN_NODE_ID", relation="UNKNOWN_RELATION")
    test_graph.add_edge("A_FUNNEL_MAG_54", "UNKNOWN_NODE_ID", relation="UNKNOWN_RELATION")

    # Verify get_graph_summary handles the custom node and edge without crashing
    summary = get_graph_summary(test_graph)
    assert summary["total_nodes"] == engine.graph.number_of_nodes() + 1
    assert summary["total_edges"] == engine.graph.number_of_edges() + 3

    # Verify specs extractors skip edges that do not match REQUIRES_SPEC or FITS_SPEC
    machine_specs = get_machine_specs(test_graph, "M_BES870XL")
    assert "UNKNOWN_NODE_ID" not in machine_specs

    accessory_specs = get_accessory_specs(test_graph, "A_FUNNEL_MAG_54")
    assert "UNKNOWN_NODE_ID" not in accessory_specs


