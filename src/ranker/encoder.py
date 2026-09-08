"""
Bi-encoder dense vector embedding and catalog caching for SpecLock Stage 2:
- Loads pre-trained sentence-transformers model (all-MiniLM-L6-v2)
- Encodes user queries, machine contexts, and accessory metadata into 384-d vectors
- Pre-computes and caches normalized embeddings for O(1) runtime lookup
"""

from typing import Dict, List, Optional
import numpy as np
from sentence_transformers import SentenceTransformer

from config import settings
from graph.schema import AccessoryNode, MachineNode


class CatalogEmbeddingCache:
    """
    High-performance in-memory cache of normalized dense vectors for
    machines and accessories in the hardware catalog.
    """

    def __init__(self, model_name: Optional[str] = None):
        self.model_name = model_name or settings.model_name
        self.model = SentenceTransformer(self.model_name)
        self._accessory_cache: Dict[str, np.ndarray] = {}
        self._machine_cache: Dict[str, np.ndarray] = {}

    def encode_text(self, text: str) -> np.ndarray:
        """
        Encodes an arbitrary string into a normalized 1D float32 numpy vector.
        Normalization ensures cosine similarity equals the vector dot product.
        """
        clean_text = text.strip() if text else ""
        embedding = self.model.encode(
            clean_text,
            convert_to_numpy=True,
            normalize_embeddings=True,
        )
        return np.asarray(embedding, dtype=np.float32)

    def encode_accessory(self, accessory: AccessoryNode) -> np.ndarray:
        """
        Retrieves or computes the normalized dense embedding for an accessory item.
        Representation combines name, category, and marketing description.
        """
        if accessory.id in self._accessory_cache:
            return self._accessory_cache[accessory.id]

        text_content = (
            f"{accessory.name} | Category: {accessory.category} | {accessory.description}"
        )
        vector = self.encode_text(text_content)
        self._accessory_cache[accessory.id] = vector
        return vector

    def encode_machine(self, machine: MachineNode) -> np.ndarray:
        """
        Retrieves or computes the normalized dense embedding for a machine.
        Used when query is absent to find accessories complementing machine features.
        """
        if machine.id in self._machine_cache:
            return self._machine_cache[machine.id]

        description = machine.description or ""
        text_content = f"{machine.name} | Series: {machine.series} | {description}"
        vector = self.encode_text(text_content)
        self._machine_cache[machine.id] = vector
        return vector

    def precompute_catalog_embeddings(
        self,
        accessories: List[AccessoryNode],
        machines: Optional[List[MachineNode]] = None,
    ) -> None:
        """
        Pre-populates the cache for all accessories and machines in the catalog.
        Executed during application startup to guarantee sub-millisecond retrieval.
        """
        if accessories:
            for accessory in accessories:
                self.encode_accessory(accessory)

        if machines:
            for machine in machines:
                self.encode_machine(machine)

    @property
    def accessory_cache_size(self) -> int:
        """Returns the number of cached accessory embeddings."""
        return len(self._accessory_cache)

    @property
    def machine_cache_size(self) -> int:
        """Returns the number of cached machine embeddings."""
        return len(self._machine_cache)

