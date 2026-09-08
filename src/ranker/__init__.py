"""
SpecLock Stage 2 Semantic Ranker and Business Scoring Subsystem:
- Vectorized bi-encoder text embeddings (sentence-transformers)
- In-memory catalog embedding caching
- Composite objective optimization: Score = alpha * CosineSim + beta * MarginRate
"""
from src.ranker.encoder import CatalogEmbeddingCache
from src.ranker.scoring import (
    RankedAccessory,
    calculate_cosine_similarity,
    calculate_composite_score,
    rank_compatible_accessories,
)

__all__ = [
    "CatalogEmbeddingCache",
    "RankedAccessory",
    "calculate_cosine_similarity",
    "calculate_composite_score",
    "rank_compatible_accessories",
]
