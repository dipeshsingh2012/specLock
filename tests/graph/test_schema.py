"""
Unit tests corresponding 1:1 to src/graph/schema.py:
- SpecNode: node_id generation and normalization
- MachineNode: price non-negativity and required fields
- AccessoryNode: margin_rate bounds [0.0, 1.0] and fitment map
- CatalogData: end-to-end Pydantic validation of catalog dataset
"""

import pytest
from pydantic import ValidationError

from graph.schema import SpecNode, MachineNode, AccessoryNode, CatalogData


def test_spec_node_id_property():
    """Verify SpecNode automatically generates uppercase, normalized node_id strings."""
    diameter_spec = SpecNode(spec_type="collar_diameter", spec_value="54mm")
    assert diameter_spec.node_id == "SPEC_COLLAR_DIAMETER_54MM"

    voltage_spec = SpecNode(spec_type="voltage", spec_value="120V")
    assert voltage_spec.node_id == "SPEC_VOLTAGE_120V"

    universal_spec = SpecNode(spec_type="collar_diameter", spec_value="universal")
    assert universal_spec.node_id == "SPEC_COLLAR_DIAMETER_UNIVERSAL"


def test_machine_node_validation():
    """Verify MachineNode enforces valid price and required fields."""
    valid_machine = MachineNode(
        id="M_TEST",
        name="Test Machine",
        sku="TEST-SKU",
        series="Barista",
        price=599.95,
        specs={"collar_diameter": "54mm", "voltage": "120V"},
    )
    assert valid_machine.node_id == "M_TEST"
    assert valid_machine.price == 599.95
    assert valid_machine.specs["collar_diameter"] == "54mm"

    # Negative price must raise a validation error
    with pytest.raises(ValidationError):
        MachineNode(
            id="M_INVALID_PRICE",
            name="Invalid Price Machine",
            sku="INV-01",
            series="Test",
            price=-10.0,
            specs={"collar_diameter": "54mm"},
        )


def test_accessory_node_validation():
    """Verify AccessoryNode enforces 0.0 <= margin_rate <= 1.0 and valid pricing."""
    valid_accessory = AccessoryNode(
        id="A_TEST",
        name="Test Accessory",
        sku="ACC-SKU",
        category="maintenance",
        price=19.95,
        margin_rate=0.70,
        fits={"collar_diameter": "universal"},
        description="A universal test accessory.",
    )
    assert valid_accessory.node_id == "A_TEST"
    assert valid_accessory.margin_rate == 0.70

    # Margin rate exceeding 1.0 must fail validation
    with pytest.raises(ValidationError):
        AccessoryNode(
            id="A_HIGH_MARGIN",
            name="Invalid Margin Accessory",
            sku="ACC-BAD-1",
            category="maintenance",
            price=19.95,
            margin_rate=1.50,
            fits={"collar_diameter": "universal"},
            description="Bad margin high",
        )

    # Negative margin rate must fail validation
    with pytest.raises(ValidationError):
        AccessoryNode(
            id="A_NEGATIVE_MARGIN",
            name="Negative Margin Accessory",
            sku="ACC-BAD-2",
            category="maintenance",
            price=19.95,
            margin_rate=-0.10,
            fits={"collar_diameter": "universal"},
            description="Bad margin low",
        )


def test_catalog_data_loader(catalog_data: CatalogData):
    """Verify CatalogData correctly parses and validates the real catalog JSON."""
    assert len(catalog_data.machines) >= 10
    assert len(catalog_data.accessories) >= 30

    # Verify every machine has a collar diameter and voltage specification
    for machine in catalog_data.machines:
        assert "collar_diameter" in machine.specs
        assert "voltage" in machine.specs
        assert machine.price >= 0.0

    # Verify every accessory has margin rate within valid bounds
    for accessory in catalog_data.accessories:
        assert 0.0 <= accessory.margin_rate <= 1.0
        assert accessory.price >= 0.0

