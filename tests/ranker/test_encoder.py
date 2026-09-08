"""
Unit tests corresponding 1:1 to src/ranker/encoder.py:
- CatalogEmbeddingCache initialization and model loading
- Dense text embedding dimensions (384-d) and L2 normalization
- In-memory caching for accessories and machines
- Empty and whitespace string handling
- Precompute catalog batch embeddings
"""

import numpy as np
import pytest
from graph.schema import AccessoryNode, MachineNode
from ranker.encoder import CatalogEmbeddingCache


@pytest.fixture(scope="module")
def encoder() -> CatalogEmbeddingCache:
    """Module-scoped embedding cache to avoid repetitive model loading in tests."""
    return CatalogEmbeddingCache()


def test_encoder_initialization(encoder: CatalogEmbeddingCache):
    """Verify CatalogEmbeddingCache loads the configured model."""
    assert encoder.model is not None
    assert encoder.model_name == "sentence-transformers/all-MiniLM-L6-v2"


def test_encode_text_shape_and_l2_normalization(encoder: CatalogEmbeddingCache):
    """Verify vector shape is 384-dimensional and unit L2 normalized."""
    sample_text = "precision 54mm magnetic dosing funnel"
    vector = encoder.encode_text(sample_text)

    assert isinstance(vector, np.ndarray)
    assert vector.shape == (384,)
    assert vector.dtype == np.float32

    # L2 norm must be approximately 1.0 (within float precision)
    l2_norm = float(np.linalg.norm(vector))
    assert l2_norm == pytest.approx(1.0, abs=1e-4)


def test_encode_text_empty_and_whitespace(encoder: CatalogEmbeddingCache):
    """Verify empty and whitespace strings return valid normalized vectors."""
    vec_empty = encoder.encode_text("")
    assert vec_empty.shape == (384,)
    assert float(np.linalg.norm(vec_empty)) == pytest.approx(1.0, abs=1e-4)

    vec_spaces = encoder.encode_text("   ")
    assert vec_spaces.shape == (384,)
    assert float(np.linalg.norm(vec_spaces)) == pytest.approx(1.0, abs=1e-4)


def test_encode_accessory_and_caching(encoder: CatalogEmbeddingCache, sample_54mm_accessory: AccessoryNode):
    """Verify accessory embedding is cached and returned on subsequent lookups."""
    initial_cache_size = encoder.accessory_cache_size

    # First lookup: computes and caches vector
    vector_first = encoder.encode_accessory(sample_54mm_accessory)
    assert vector_first.shape == (384,)
    assert encoder.accessory_cache_size == initial_cache_size + 1

    # Second lookup: returns the exact cached reference
    vector_second = encoder.encode_accessory(sample_54mm_accessory)
    assert np.array_equal(vector_first, vector_second)
    assert encoder.accessory_cache_size == initial_cache_size + 1


def test_encode_machine_and_caching(encoder: CatalogEmbeddingCache, sample_54mm_machine: MachineNode):
    """Verify machine embedding incorporates series and description and is cached."""
    initial_cache_size = encoder.machine_cache_size

    # First lookup: computes and caches vector
    vector_first = encoder.encode_machine(sample_54mm_machine)
    assert vector_first.shape == (384,)
    assert encoder.machine_cache_size == initial_cache_size + 1

    # Second lookup: returns the exact cached reference
    vector_second = encoder.encode_machine(sample_54mm_machine)
    assert np.array_equal(vector_first, vector_second)
    assert encoder.machine_cache_size == initial_cache_size + 1

    # Test machine with empty/None description
    machine_no_desc = MachineNode(
        id="M_NO_DESC",
        name="No Description Machine",
        sku="NODESC-01",
        series="Compact",
        price=399.0,
        specs={},
        description=None,
    )
    vec_no_desc = encoder.encode_machine(machine_no_desc)
    assert vec_no_desc.shape == (384,)


def test_precompute_catalog_embeddings(
    encoder: CatalogEmbeddingCache,
    sample_54mm_accessory: AccessoryNode,
    sample_58mm_accessory: AccessoryNode,
    sample_54mm_machine: MachineNode,
):
    """Verify precompute_catalog_embeddings populates both accessory and machine caches."""
    new_encoder = CatalogEmbeddingCache()
    assert new_encoder.accessory_cache_size == 0
    assert new_encoder.machine_cache_size == 0

    accessories = [sample_54mm_accessory, sample_58mm_accessory]
    machines = [sample_54mm_machine]

    # Precompute with accessories only (machines is None)
    new_encoder.precompute_catalog_embeddings(accessories=accessories)
    assert new_encoder.accessory_cache_size == 2
    assert new_encoder.machine_cache_size == 0

    # Precompute with both accessories and machines
    new_encoder.precompute_catalog_embeddings(accessories=accessories, machines=machines)
    assert new_encoder.accessory_cache_size == 2
    assert new_encoder.machine_cache_size == 1

    # Precompute with empty accessories list to verify branch
    new_encoder.precompute_catalog_embeddings(accessories=[])
    assert new_encoder.accessory_cache_size == 2


def test_resolve_model_path_existing_dir(tmp_path):
    """Verify _resolve_model_path returns directory path when directory exists."""
    assert CatalogEmbeddingCache._resolve_model_path(str(tmp_path)) == str(tmp_path)


def test_resolve_model_path_baked_dir_fallback(monkeypatch, tmp_path):
    """Verify fallback to SPECLOCK_MODEL_DIR when name_or_path is not a dir but baked dir exists."""
    monkeypatch.setenv("SPECLOCK_MODEL_DIR", str(tmp_path))
    result = CatalogEmbeddingCache._resolve_model_path("sentence-transformers/all-MiniLM-L6-v2")
    assert result == str(tmp_path)


def test_resolve_model_path_huggingface_id_when_no_dir(monkeypatch):
    """Verify returns model ID when neither name_or_path nor SPECLOCK_MODEL_DIR is a dir."""
    monkeypatch.setenv("SPECLOCK_MODEL_DIR", "/nonexistent/model/path")
    result = CatalogEmbeddingCache._resolve_model_path("sentence-transformers/all-MiniLM-L6-v2")
    assert result == "sentence-transformers/all-MiniLM-L6-v2"

