"""
Shared pytest fixtures and configuration for SpecLock test suite.
Provides reusable domain fixtures: catalog data, machine instances,
accessory instances, and pre-built GraphEngine instances.
"""

import sys
from pathlib import Path
import pytest

# Ensure src/ is on sys.path for test discovery across all test modules
PROJECT_ROOT = Path(__file__).resolve().parent.parent
SRC_PATH = PROJECT_ROOT / "src"
if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

from config import settings
from graph.schema import SpecNode, MachineNode, AccessoryNode, CatalogData
from graph.builder import build_graph, load_catalog
from graph.filter import InMemoryGraphEngine


# ============================================================================
# ENGINE & CATALOG FIXTURES
# ============================================================================

@pytest.fixture(scope="session")
def engine() -> InMemoryGraphEngine:
    """Session-scoped InMemoryGraphEngine initialized with the default catalog."""
    graph = build_graph()
    return InMemoryGraphEngine(graph=graph)


@pytest.fixture(scope="session")
def catalog_data() -> CatalogData:
    """Session-scoped loaded catalog data."""
    return load_catalog()


# ============================================================================
# SAMPLE MACHINE FIXTURES
# ============================================================================

@pytest.fixture
def sample_54mm_machine() -> MachineNode:
    """Fixture representing a standard 54mm 120V consumer machine."""
    return MachineNode(
        id="M_TEST_54",
        name="Test 54mm Machine",
        sku="TEST-M54",
        series="Barista",
        price=699.95,
        specs={
            "collar_diameter": "54mm",
            "voltage": "120V",
            "steam_wand": "standard",
        },
        description="A standard 54mm consumer test machine.",
    )


@pytest.fixture
def sample_58mm_machine() -> MachineNode:
    """Fixture representing a standard 58mm 120V commercial machine."""
    return MachineNode(
        id="M_TEST_58",
        name="Test 58mm Machine",
        sku="TEST-M58",
        series="Dual Boiler",
        price=1599.95,
        specs={
            "collar_diameter": "58mm",
            "voltage": "120V",
            "steam_wand": "commercial",
        },
        description="A standard 58mm prosumer test machine.",
    )


# ============================================================================
# SAMPLE ACCESSORY FIXTURES
# ============================================================================

@pytest.fixture
def sample_54mm_accessory() -> AccessoryNode:
    """Fixture representing an accessory that strictly fits 54mm collars."""
    return AccessoryNode(
        id="TEST_FUNNEL_54",
        name="Test 54mm Funnel",
        sku="TEST-FN-54",
        category="workflow_tools",
        price=25.00,
        margin_rate=0.60,
        fits={
            "collar_diameter": "54mm",
            "voltage": "universal",
        },
        description="A precision 54mm dosing funnel.",
    )


@pytest.fixture
def sample_58mm_accessory() -> AccessoryNode:
    """Fixture representing an accessory that strictly fits 58mm collars."""
    return AccessoryNode(
        id="TEST_PORTA_58",
        name="Test 58mm Portafilter",
        sku="TEST-PF-58",
        category="portafilters",
        price=75.00,
        margin_rate=0.50,
        fits={
            "collar_diameter": "58mm",
            "voltage": "universal",
        },
        description="A standard 58mm bottomless portafilter.",
    )


@pytest.fixture
def sample_universal_accessory() -> AccessoryNode:
    """Fixture representing an accessory that universally fits all machines."""
    return AccessoryNode(
        id="TEST_KNOCK_BOX",
        name="Universal Knock Box",
        sku="TEST-KB-UNI",
        category="maintenance",
        price=35.00,
        margin_rate=0.65,
        fits={
            "collar_diameter": "universal",
            "voltage": "universal",
        },
        description="A universal desktop knock box for espresso pucks.",
    )

