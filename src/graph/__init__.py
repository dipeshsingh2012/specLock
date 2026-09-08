"""
SpecLock Graph Engine: Deterministic Bipartite Graph Pruning.
"""

from .base import (
    FilterResult,
    GraphEngine,
)
from .schema import (
    MachineNode,
    AccessoryNode,
    SpecNode,
    CatalogData,
)
from .builder import (
    build_graph,
    load_catalog,
    get_graph_summary,
    get_machine,
    get_accessory,
    get_machine_specs,
    get_accessory_specs,
)
from .filter import (
    InMemoryGraphEngine,
    filter_candidates,
    is_accessory_compatible,
)

__all__ = [
    "FilterResult",
    "GraphEngine",
    "InMemoryGraphEngine",
    "filter_candidates",
    "is_accessory_compatible",
    "MachineNode",
    "AccessoryNode",
    "SpecNode",
    "CatalogData",
    "build_graph",
    "load_catalog",
    "get_graph_summary",
    "get_machine",
    "get_accessory",
    "get_machine_specs",
    "get_accessory_specs",
]

