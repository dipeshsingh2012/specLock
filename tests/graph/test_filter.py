"""
Unit and integration tests corresponding 1:1 to src/graph/filter.py:
- Pure compatibility rules (is_accessory_compatible)
- Stage 1 deterministic graph pruning (InMemoryGraphEngine)
- Invariant: 0% False-Positive Fitment Guarantee (54mm vs 58mm)
- Universal pass-through & electrical/voltage isolation
- Inverted index predecessor candidate lookups
- Domain-agnostic primary spec key generalization
- Category filtering & convenience filter_candidates helper
- Sub-millisecond latency SLA enforcement (<2.0ms)
- Error handling on unregistered machine identifiers
"""

import pytest
from graph.schema import AccessoryNode, MachineNode
from graph.base import FilterResult
from graph.filter import (
    InMemoryGraphEngine,
    is_accessory_compatible,
    filter_candidates,
)


# ============================================================================
# 1. PURE COMPATIBILITY RULES (is_accessory_compatible)
# ============================================================================

def test_pure_compatibility_dimensional_matching(sample_54mm_accessory, sample_58mm_accessory):
    """Test pure function logic on physical diameter and electrical matching."""
    specs_54mm = {
        "collar_diameter": "54mm",
        "voltage": "120V",
    }
    specs_58mm = {
        "collar_diameter": "58mm",
        "voltage": "120V",
    }

    # 54mm accessory on 54mm machine -> COMPATIBLE
    assert is_accessory_compatible(sample_54mm_accessory, specs_54mm) is True

    # 58mm accessory on 54mm machine -> INCOMPATIBLE (HARD REJECT)
    assert is_accessory_compatible(sample_58mm_accessory, specs_54mm) is False

    # 54mm accessory on 58mm machine -> INCOMPATIBLE (HARD REJECT)
    assert is_accessory_compatible(sample_54mm_accessory, specs_58mm) is False

    # 58mm accessory on 58mm machine -> COMPATIBLE
    assert is_accessory_compatible(sample_58mm_accessory, specs_58mm) is True


def test_pure_compatibility_voltage_isolation():
    """Test electrical voltage matching and target voltage overrides."""
    electric_warmer_120v = AccessoryNode(
        id="A_ELEC_120",
        name="120V Cup Warmer Plate",
        sku="ACC-120V",
        category="maintenance",
        price=29.95,
        margin_rate=0.55,
        fits={"voltage": "120V"},
        description="Electric warming plate designed specifically for 120V power.",
    )

    specs_120v = {"voltage": "120V"}
    specs_240v = {"voltage": "240V"}

    # Matches when machine voltage is 120V
    assert is_accessory_compatible(electric_warmer_120v, specs_120v) is True

    # Rejects when machine voltage is 240V
    assert is_accessory_compatible(electric_warmer_120v, specs_240v) is False

    # Matches when user explicitly specifies a 120V target voltage override
    assert is_accessory_compatible(electric_warmer_120v, specs_240v, target_voltage="120V") is True


def test_pure_compatibility_series_constraint():
    """Test that series-specific accessories reject non-matching series."""
    barista_hopper = AccessoryNode(
        id="A_HOPPER",
        name="Barista Single Dose Bellows Hopper",
        sku="ACC-HOP",
        category="workflow_tools",
        price=34.95,
        margin_rate=0.60,
        fits={
            "series": "Barista",
            "voltage": "universal",
        },
        description="Low-retention silicone bellows hopper tailored for the Barista series.",
    )

    barista_specs = {
        "series": "Barista",
        "collar_diameter": "54mm",
    }
    dual_boiler_specs = {
        "series": "Commercial_Dual",
        "collar_diameter": "58mm",
    }

    # Matches on Barista machine
    assert is_accessory_compatible(barista_hopper, barista_specs) is True

    # Rejects on Commercial_Dual series machine
    assert is_accessory_compatible(barista_hopper, dual_boiler_specs) is False


def test_pure_compatibility_universal_passthrough(sample_universal_accessory):
    """Test that universal accessories match any machine specification set."""
    specs_54mm = {"collar_diameter": "54mm", "voltage": "120V"}
    specs_58mm = {"collar_diameter": "58mm", "voltage": "240V"}
    specs_custom = {"tray_size": "large", "battery_platform": "20V"}

    assert is_accessory_compatible(sample_universal_accessory, specs_54mm) is True
    assert is_accessory_compatible(sample_universal_accessory, specs_58mm) is True
    assert is_accessory_compatible(sample_universal_accessory, specs_custom) is True


# ============================================================================
# 2. STAGE 1 ZERO-ERROR FITMENT INVARIANTS (54mm vs 58mm)
# ============================================================================

def test_54mm_machines_strictly_zero_58mm_accessories(engine: InMemoryGraphEngine):
    """
    CRITICAL INVARIANT:
    Assert that for all 54mm machines (Barista Express, Pro, Touch, Bambino Plus, Infuser),
    ZERO 58mm accessories are ever recommended.
    """
    machines_54mm = [
        "M_BES870XL",      # Barista Express (US 120V)
        "M_BES870_UK",     # Barista Express (UK 240V)
        "M_BES878BSS",     # Barista Pro
        "M_BES880BSS",     # Barista Touch
        "M_BES876BSS",     # Barista Express Impress
        "M_BES500BSS",     # Bambino Plus
        "M_BES450BSS",     # Bambino
        "M_BES840XL",      # Infuser
    ]

    forbidden_58mm_skus = {
        "ACC-BP-58-WNT",   # 58mm Bottomless Portafilter Walnut
        "ACC-BP-58-SS",    # 58mm Stainless Portafilter
        "ACC-DF-58-MAG",   # 58mm Magnetic Dosing Collar
        "ACC-TMP-585-CAL", # 58.5mm Calibrated Tamper
        "ACC-DIST-585-DL", # 58.5mm Palm Distributor
        "ACC-BSK-VST-58",  # 58mm VST Precision Basket
        "ACC-PCK-585-150", # 58.5mm Puck Screen
        "ACC-GSK-SIL-58",  # 58mm Silicone Steam Ring
        "ACC-DC-58-SS",    # 58mm Dosing Cup
        "ACC-BLD-58-SS",   # 58mm Blind Basket
    }

    for machine_id in machines_54mm:
        result: FilterResult = engine.filter_compatible_accessories(machine_id)
        recommended_skus = {accessory.sku for accessory in result.compatible_accessories}

        # 1. Direct SKU intersection check
        leaked_skus = recommended_skus.intersection(forbidden_58mm_skus)
        assert len(leaked_skus) == 0, (
            f"Fitment Error! Machine {machine_id} recommended incompatible 58mm SKUs: {leaked_skus}"
        )

        # 2. Spec constraint verification: No item may declare collar_diameter == '58mm'
        for accessory in result.compatible_accessories:
            assert accessory.fits.get("collar_diameter") != "58mm", (
                f"Fitment Error! Accessory {accessory.id} ({accessory.name}) with diameter 58mm leaked to {machine_id}"
            )


def test_58mm_machines_strictly_zero_54mm_accessories(engine: InMemoryGraphEngine):
    """
    CRITICAL INVARIANT:
    Assert that for all 58mm commercial machines (Dual Boiler, Oracle, Oracle Touch),
    ZERO 54mm accessories are ever recommended.
    """
    machines_58mm = [
        "M_BES920XL",      # Dual Boiler (US 120V)
        "M_BES920_UK",     # Dual Boiler (UK 240V)
        "M_BES980XL",      # Oracle
        "M_BES990BSS",     # Oracle Touch
    ]

    forbidden_54mm_skus = {
        "ACC-DF-54-MAG",   # 54mm Magnetic Dosing Funnel
        "ACC-DF-54-TRIG",  # 54mm Grinder Trigger Funnel
        "ACC-BP-54-WNT",   # 54mm Walnut Bottomless Portafilter
        "ACC-BP-54-SS",    # 54mm Stainless Naked Portafilter
        "ACC-TMP-533-CAL", # 53.3mm Precision Tamper
        "ACC-DIST-533-DL", # 53.3mm Palm Tamper
        "ACC-BSK-IMS-54",  # 54mm IMS Basket
        "ACC-BSK-DW-54",   # 54mm Dual Wall Basket
        "ACC-PCK-535-150", # 53.5mm Puck Screen
        "ACC-SS-NANO-54",  # 54mm Nanotech Shower Screen
        "ACC-GSK-SIL-54",  # 54mm Silicone Gasket
        "ACC-DC-54-SS",    # 54mm Dosing Cup
        "ACC-BLD-54-RUB",  # 54mm Rubber Blind Disc
    }

    for machine_id in machines_58mm:
        result: FilterResult = engine.filter_compatible_accessories(machine_id)
        recommended_skus = {accessory.sku for accessory in result.compatible_accessories}

        # 1. Direct SKU intersection check
        leaked_skus = recommended_skus.intersection(forbidden_54mm_skus)
        assert len(leaked_skus) == 0, (
            f"Fitment Error! Machine {machine_id} recommended incompatible 54mm SKUs: {leaked_skus}"
        )

        # 2. Spec constraint verification: No item may declare collar_diameter == '54mm'
        for accessory in result.compatible_accessories:
            assert accessory.fits.get("collar_diameter") != "54mm", (
                f"Fitment Error! Accessory {accessory.id} ({accessory.name}) with diameter 54mm leaked to {machine_id}"
            )


# ============================================================================
# 3. UNIVERSAL ACCESSORIES & INVERTED CANDIDATE LOOKUPS
# ============================================================================

def test_universal_accessories_pass_all_machines(engine: InMemoryGraphEngine):
    """
    Assert that universal accessories (knock boxes, cleaning tablets, scales, towels)
    are present in recommendation pools for BOTH 54mm and 58mm machines.
    """
    universal_skus = [
        "ACC-KB-MINI-SS",    # Mini Knock Box
        "ACC-SCL-ESPR",      # Precision Espresso Scale
        "ACC-CLN-TAB-40",    # Cleaning Tablets
        "ACC-DSC-PWD-4",     # Descaler Powder
        "ACC-WDT-035",       # Needle WDT Tool
        "ACC-TWL-BAR-3",     # Barista Towels
    ]

    result_54 = engine.filter_compatible_accessories("M_BES870XL")
    result_58 = engine.filter_compatible_accessories("M_BES920XL")

    skus_54 = {accessory.sku for accessory in result_54.compatible_accessories}
    skus_58 = {accessory.sku for accessory in result_58.compatible_accessories}

    for sku in universal_skus:
        assert sku in skus_54, f"Universal SKU {sku} missing from 54mm recommendations"
        assert sku in skus_58, f"Universal SKU {sku} missing from 58mm recommendations"


def test_inverted_index_candidate_pruning(engine: InMemoryGraphEngine):
    """Test that _get_candidates_for_spec returns exact match + universal subsets."""
    candidates_54 = engine._get_candidates_for_spec("collar_diameter", "54mm")
    assert len(candidates_54) > 0

    candidates_58 = engine._get_candidates_for_spec("collar_diameter", "58mm")
    assert len(candidates_58) > 0

    # Ensure intersection between strictly dimensional 54mm and 58mm items is empty
    dimensional_54 = set()
    for acc_id in candidates_54:
        accessory = engine.get_accessory(acc_id)
        if accessory and accessory.fits.get("collar_diameter") == "54mm":
            dimensional_54.add(acc_id)

    dimensional_58 = set()
    for acc_id in candidates_58:
        accessory = engine.get_accessory(acc_id)
        if accessory and accessory.fits.get("collar_diameter") == "58mm":
            dimensional_58.add(acc_id)

    assert len(dimensional_54.intersection(dimensional_58)) == 0


def test_domain_agnostic_spec_generalization(engine: InMemoryGraphEngine):
    """
    Test that the graph engine supports arbitrary primary spec keys
    (e.g., passing primary_spec_key='series' or an arbitrary dimension).
    """
    result = engine.filter_compatible_accessories(
        "M_BES870XL",
        primary_spec_key="series",
    )
    assert result.total_passed > 0

    # All Barista-specific accessories must pass
    for accessory in result.compatible_accessories:
        if "series" in accessory.fits and accessory.fits["series"] != "universal":
            assert accessory.fits["series"] == "Barista"


# ============================================================================
# 4. PERFORMANCE, CATEGORY FILTERING & ERROR HANDLING
# ============================================================================

def test_category_filtering(engine: InMemoryGraphEngine):
    """Assert category filtering correctly subsets candidates without fitment leakage."""
    result = engine.filter_compatible_accessories("M_BES870XL", category="portafilters")
    assert result.total_passed > 0

    for accessory in result.compatible_accessories:
        assert accessory.category == "portafilters"
        assert accessory.fits.get("collar_diameter") == "54mm"


def test_convenience_filter_candidates_function(engine: InMemoryGraphEngine):
    """Assert standalone filter_candidates() function produces identical result."""
    result_engine = engine.filter_compatible_accessories("M_BES870XL")
    result_convenience = filter_candidates(engine.graph, "M_BES870XL")

    assert result_engine.total_passed == result_convenience.total_passed
    engine_ids = [acc.id for acc in result_engine.compatible_accessories]
    convenience_ids = [acc.id for acc in result_convenience.compatible_accessories]
    assert engine_ids == convenience_ids


def test_sub_millisecond_pruning_performance(engine: InMemoryGraphEngine):
    """Assert Stage 1 deterministic graph pruning executes in under 2ms."""
    result = engine.filter_compatible_accessories("M_BES870XL")
    assert result.latency_ms < 2.0, f"Pruning exceeded performance threshold: {result.latency_ms}ms"


def test_unknown_machine_raises_error(engine: InMemoryGraphEngine):
    """Assert querying an unregistered machine ID raises a descriptive ValueError."""
    with pytest.raises(ValueError, match="not found in compatibility graph"):
        engine.filter_compatible_accessories("M_NON_EXISTENT_ID")


def test_get_all_accessories(engine: InMemoryGraphEngine):
    """Verify get_all_accessories returns the complete catalog of accessories."""
    all_accessories = engine.get_all_accessories()
    assert len(all_accessories) == 40
    assert all(isinstance(acc, AccessoryNode) for acc in all_accessories)


def test_get_all_machines(engine: InMemoryGraphEngine):
    """Verify get_all_machines returns the complete catalog of machines."""
    all_machines = engine.get_all_machines()
    assert len(all_machines) == 12
    assert all(isinstance(machine, MachineNode) for machine in all_machines)


def test_candidates_for_unconstrained_and_nonexistent_specs(engine: InMemoryGraphEngine):
    """
    Verify candidate lookups when:
    1. Spec value is None/empty (returns all accessories)
    2. Spec node or universal node does not exist in the graph (returns empty set)
    """
    # 1. Spec value None returns all accessory IDs
    all_candidates = engine._get_candidates_for_spec("collar_diameter", None)
    assert len(all_candidates) == 40

    # 2. Spec value empty string returns all accessory IDs
    all_candidates_empty = engine._get_candidates_for_spec("collar_diameter", "")
    assert len(all_candidates_empty) == 40

    # 3. Unrecognized spec type and value has no nodes in the graph
    empty_candidates = engine._get_candidates_for_spec("non_existent_spec", "non_existent_value")
    assert len(empty_candidates) == 0


def test_pure_compatibility_missing_machine_spec_and_voltage_branches(sample_54mm_accessory):
    """
    Verify pure compatibility handles:
    1. Accessory requiring a constraint not present in machine specs (hard reject)
    2. Accessory with voltage requirement evaluated against machine without voltage spec
    """
    # Machine is missing collar_diameter required by accessory -> reject
    machine_missing_collar = {"voltage": "120V"}
    assert is_accessory_compatible(sample_54mm_accessory, machine_missing_collar) is False

    # Accessory with voltage requirement, but machine has no voltage and no target_voltage
    acc_voltage = AccessoryNode(
        id="A_VOLT_TEST",
        name="Voltage Test Acc",
        sku="V-TEST",
        category="maintenance",
        price=10.0,
        margin_rate=0.5,
        fits={"voltage": "120V"},
        description="Voltage test",
    )
    assert is_accessory_compatible(acc_voltage, machine_specs={}) is True


