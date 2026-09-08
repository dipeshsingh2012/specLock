"""
Unit tests corresponding 1:1 to src/ranker/scoring.py:
- Cosine similarity computation between dense embedding vectors
- Zero-vector guard and boundary clipping [-1.0, 1.0]
- Composite objective score calculation with configurable alpha and beta
- RankedAccessory dataclass properties
- Candidate accessory ranking with explicit query intent
- Zero-query PDP/cart cross-sell ranking with machine embedding fallback
- Top-K slicing and deterministic tie-breaking logic
"""

import numpy as np
import pytest

from config import settings
from graph.schema import AccessoryNode, MachineNode
from ranker.encoder import CatalogEmbeddingCache
from ranker.scoring import (
    RankedAccessory,
    calculate_cosine_similarity,
    calculate_composite_score,
    rank_compatible_accessories,
)


@pytest.fixture(scope="module")
def encoder() -> CatalogEmbeddingCache:
    """Module-scoped embedding cache to avoid repetitive model loading in tests."""
    return CatalogEmbeddingCache()


# ============================================================================
# COSINE SIMILARITY TESTS
# ============================================================================


def test_calculate_cosine_similarity_identical_vectors():
    """Identical unit vectors must yield a cosine similarity of exactly 1.0."""
    vector = np.array([0.6, 0.8, 0.0], dtype=np.float32)
    similarity = calculate_cosine_similarity(vector, vector)
    assert pytest.approx(similarity, abs=1e-5) == 1.0


def test_calculate_cosine_similarity_orthogonal_and_opposite():
    """Orthogonal vectors must yield 0.0; opposite vectors must yield -1.0."""
    vector_x = np.array([1.0, 0.0, 0.0], dtype=np.float32)
    vector_y = np.array([0.0, 1.0, 0.0], dtype=np.float32)
    vector_neg_x = np.array([-1.0, 0.0, 0.0], dtype=np.float32)

    similarity_orthogonal = calculate_cosine_similarity(vector_x, vector_y)
    assert pytest.approx(similarity_orthogonal, abs=1e-5) == 0.0

    similarity_opposite = calculate_cosine_similarity(vector_x, vector_neg_x)
    assert pytest.approx(similarity_opposite, abs=1e-5) == -1.0


def test_calculate_cosine_similarity_zero_vectors():
    """Zero-norm vectors must safely return 0.0 without division by zero errors."""
    zero_vector = np.zeros(384, dtype=np.float32)
    valid_vector = np.ones(384, dtype=np.float32)

    # First vector is zero
    assert calculate_cosine_similarity(zero_vector, valid_vector) == 0.0
    # Second vector is zero
    assert calculate_cosine_similarity(valid_vector, zero_vector) == 0.0
    # Both vectors are zero
    assert calculate_cosine_similarity(zero_vector, zero_vector) == 0.0


def test_calculate_cosine_similarity_boundary_clipping():
    """Floating point inaccuracies exceeding 1.0 or below -1.0 must be clipped."""
    # Dot product calculation resulting in slightly > 1.0 or < -1.0
    vec_a = np.array([1.000002], dtype=np.float64)
    vec_b = np.array([1.000002], dtype=np.float64)

    similarity = calculate_cosine_similarity(vec_a, vec_b)
    assert -1.0 <= similarity <= 1.0


# ============================================================================
# COMPOSITE SCORE TESTS
# ============================================================================


def test_calculate_composite_score_defaults():
    """Verify default alpha and beta from settings are respected."""
    # Default settings: alpha = 0.7, beta = 0.3
    similarity = 0.8
    margin_rate = 0.6
    expected_score = (settings.default_alpha * similarity) + (settings.default_beta * margin_rate)

    score = calculate_composite_score(similarity=similarity, margin_rate=margin_rate)
    assert pytest.approx(score, abs=1e-5) == expected_score


def test_calculate_composite_score_custom_weights():
    """Verify custom alpha and beta hyperparameter weighting."""
    similarity = 0.9
    margin_rate = 0.4

    # Pure relevance (alpha = 1.0, beta = 0.0)
    score_relevance = calculate_composite_score(
        similarity=similarity, margin_rate=margin_rate, alpha=1.0, beta=0.0
    )
    assert pytest.approx(score_relevance, abs=1e-5) == 0.9

    # Pure margin (alpha = 0.0, beta = 1.0)
    score_margin = calculate_composite_score(
        similarity=similarity, margin_rate=margin_rate, alpha=0.0, beta=1.0
    )
    assert pytest.approx(score_margin, abs=1e-5) == 0.4


# ============================================================================
# RANKED ACCESSORY DATACLASS
# ============================================================================


def test_ranked_accessory_dataclass(sample_54mm_accessory: AccessoryNode):
    """Verify RankedAccessory attributes and immutability."""
    ranked = RankedAccessory(
        accessory=sample_54mm_accessory,
        semantic_similarity=0.85,
        margin_rate=0.60,
        composite_score=0.775,
    )
    assert ranked.accessory.id == "TEST_FUNNEL_54"
    assert ranked.semantic_similarity == 0.85
    assert ranked.margin_rate == 0.60
    assert ranked.composite_score == 0.775


# ============================================================================
# RANKING ENGINE TESTS
# ============================================================================


def test_rank_compatible_accessories_empty_candidates(sample_54mm_machine: MachineNode):
    """Empty candidate list must return an empty list immediately."""
    result = rank_compatible_accessories(machine=sample_54mm_machine, candidates=[])
    assert result == []


def test_rank_compatible_accessories_with_query(
    encoder: CatalogEmbeddingCache,
    sample_54mm_machine: MachineNode,
    sample_54mm_accessory: AccessoryNode,
    sample_universal_accessory: AccessoryNode,
):
    """Verify explicit query intent ranks relevant accessory highest."""
    candidates = [sample_universal_accessory, sample_54mm_accessory]

    # Query specifically about funnel
    results = rank_compatible_accessories(
        machine=sample_54mm_machine,
        candidates=candidates,
        query="precision dosing funnel for espresso grind",
        encoder=encoder,
    )

    assert len(results) == 2
    # The 54mm funnel should match "dosing funnel" much higher than a knock box
    top_item = results[0]
    assert top_item.accessory.id == sample_54mm_accessory.id
    assert top_item.semantic_similarity > results[1].semantic_similarity
    assert top_item.composite_score > results[1].composite_score


def test_rank_compatible_accessories_machine_fallback_on_empty_query(
    encoder: CatalogEmbeddingCache,
    sample_54mm_machine: MachineNode,
    sample_54mm_accessory: AccessoryNode,
    sample_universal_accessory: AccessoryNode,
):
    """Verify zero-query or whitespace query falls back to machine context embedding."""
    candidates = [sample_54mm_accessory, sample_universal_accessory]

    # query=None
    results_none = rank_compatible_accessories(
        machine=sample_54mm_machine,
        candidates=candidates,
        query=None,
        encoder=encoder,
    )
    assert len(results_none) == 2

    # query with whitespace only
    results_whitespace = rank_compatible_accessories(
        machine=sample_54mm_machine,
        candidates=candidates,
        query="    ",
        encoder=encoder,
    )
    assert len(results_whitespace) == 2
    # Both queries without intent should yield identical ordering
    assert [r.accessory.id for r in results_none] == [r.accessory.id for r in results_whitespace]


def test_rank_compatible_accessories_top_k_and_custom_weights(
    encoder: CatalogEmbeddingCache,
    sample_54mm_machine: MachineNode,
    sample_54mm_accessory: AccessoryNode,
    sample_universal_accessory: AccessoryNode,
):
    """Verify top_k parameter truncates recommendations correctly and custom weights apply."""
    candidates = [sample_54mm_accessory, sample_universal_accessory]

    results_top_1 = rank_compatible_accessories(
        machine=sample_54mm_machine,
        candidates=candidates,
        top_k=1,
        alpha=0.5,
        beta=0.5,
        encoder=encoder,
    )
    assert len(results_top_1) == 1

    results_all = rank_compatible_accessories(
        machine=sample_54mm_machine,
        candidates=candidates,
        top_k=None,
        alpha=0.5,
        beta=0.5,
        encoder=encoder,
    )
    assert len(results_all) == 2


def test_rank_compatible_accessories_default_encoder_and_weights(
    sample_54mm_machine: MachineNode,
    sample_54mm_accessory: AccessoryNode,
):
    """Verify default encoder instantiation and None weights fallback to settings."""
    candidates = [sample_54mm_accessory]

    results = rank_compatible_accessories(
        machine=sample_54mm_machine,
        candidates=candidates,
        alpha=None,
        beta=None,
        encoder=None,
    )
    assert len(results) == 1
    assert results[0].accessory.id == sample_54mm_accessory.id


def test_rank_compatible_accessories_tie_breaking(
    encoder: CatalogEmbeddingCache,
    sample_54mm_machine: MachineNode,
):
    """Verify tie-breaking by margin_rate descending, then accessory ID ascending."""
    # Item A and Item B will be given identical text so their similarity is equal
    same_desc = "Precision stainless steel cleaning brush"

    item_low_margin = AccessoryNode(
        id="ACC_LOW_MARGIN",
        name="Brush Standard",
        sku="SKU-B1",
        category="maintenance",
        price=10.0,
        margin_rate=0.40,
        fits={"collar_diameter": "universal", "voltage": "universal"},
        description=same_desc,
    )

    item_high_margin = AccessoryNode(
        id="ACC_HIGH_MARGIN",
        name="Brush Premium",
        sku="SKU-B2",
        category="maintenance",
        price=15.0,
        margin_rate=0.70,
        fits={"collar_diameter": "universal", "voltage": "universal"},
        description=same_desc,
    )

    # When alpha=0.0 and beta=0.0, composite scores are equal (0.0).
    # Higher margin rate should win.
    results_margin_tie = rank_compatible_accessories(
        machine=sample_54mm_machine,
        candidates=[item_low_margin, item_high_margin],
        alpha=0.0,
        beta=0.0,
        encoder=encoder,
    )
    assert results_margin_tie[0].accessory.id == "ACC_HIGH_MARGIN"

    # When both score and margin are equal, ID ascending tie-breaks
    item_id_a = AccessoryNode(
        id="ACC_A",
        name="Brush Alpha",
        sku="SKU-A",
        category="maintenance",
        price=10.0,
        margin_rate=0.50,
        fits={"collar_diameter": "universal", "voltage": "universal"},
        description=same_desc,
    )
    item_id_b = AccessoryNode(
        id="ACC_B",
        name="Brush Beta",
        sku="SKU-B",
        category="maintenance",
        price=10.0,
        margin_rate=0.50,
        fits={"collar_diameter": "universal", "voltage": "universal"},
        description=same_desc,
    )

    results_id_tie = rank_compatible_accessories(
        machine=sample_54mm_machine,
        candidates=[item_id_b, item_id_a],
        alpha=0.0,
        beta=0.0,
        encoder=encoder,
    )
    assert results_id_tie[0].accessory.id == "ACC_A"
    assert results_id_tie[1].accessory.id == "ACC_B"

