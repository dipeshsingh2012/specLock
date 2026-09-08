"""
SpecLock Stage 2: Probabilistic Semantic Ranker and Composite Scoring Engine.

Computes semantic affinity between user intent (or machine context) and compatible accessories,
combining semantic similarity with economic margin contribution:
    Score(u, i) = alpha * CosineSim(e_u, e_i) + beta * MarginRate(i)
"""

from dataclasses import dataclass
from typing import List, Optional
import numpy as np

from src.config import settings
from src.graph.schema import AccessoryNode, MachineNode
from src.ranker.encoder import CatalogEmbeddingCache


@dataclass(frozen=True)
class RankedAccessory:
    """
    Encapsulates a compatible accessory with its Stage 2 scoring components.
    """
    accessory: AccessoryNode
    semantic_similarity: float
    margin_rate: float
    composite_score: float


def calculate_cosine_similarity(vec_a: np.ndarray, vec_b: np.ndarray) -> float:
    """
    Computes cosine similarity between two dense embedding vectors.
    Since embeddings from CatalogEmbeddingCache are already L2-normalized to unit length,
    cosine similarity simplifies to the vector dot product:
        cos(theta) = (a . b) / (||a|| * ||b||) = a . b

    Guards against zero-norm vectors and floating point inaccuracies by clipping to [-1.0, 1.0].
    """
    norm_a = float(np.linalg.norm(vec_a))
    norm_b = float(np.linalg.norm(vec_b))

    if norm_a == 0.0 or norm_b == 0.0:
        return 0.0

    dot_product = float(np.dot(vec_a, vec_b) / (norm_a * norm_b))
    return float(np.clip(dot_product, -1.0, 1.0))


def calculate_composite_score(
    similarity: float,
    margin_rate: float,
    alpha: float = settings.default_alpha,
    beta: float = settings.default_beta,
) -> float:
    """
    Computes the composite recommendation score balancing relevance and profitability:
        Score(u, i) = alpha * CosineSim(u, i) + beta * MarginRate(i)
    """
    return float(alpha * similarity + beta * margin_rate)


def rank_compatible_accessories(
    machine: MachineNode,
    candidates: List[AccessoryNode],
    query: Optional[str] = None,
    top_k: Optional[int] = None,
    alpha: Optional[float] = None,
    beta: Optional[float] = None,
    encoder: Optional[CatalogEmbeddingCache] = None,
) -> List[RankedAccessory]:
    """
    Ranks physically/electrically compatible accessory candidates using semantic bi-encoder
    affinity and economic margin weighting.

    Context Resolution:
    - If `query` is provided and non-empty: embeds the search query text directly (e.g. "precision dosing funnel" or "milk pitcher").
    - If `query` is None or empty: retrieves the pre-computed machine embedding context
      (name + series + description) to rank accessories that complement machine attributes.
    """
    if not candidates:
        return []

    active_alpha = settings.default_alpha if alpha is None else alpha
    active_beta = settings.default_beta if beta is None else beta
    active_encoder = encoder if encoder is not None else CatalogEmbeddingCache()

    # Determine context embedding: explicit query vs zero-query PDP/cart machine context
    if query and query.strip():
        user_vector = active_encoder.encode_text(query.strip())
    else:
        user_vector = active_encoder.encode_machine(machine)

    ranked_items: List[RankedAccessory] = []
    for candidate in candidates:
        accessory_vector = active_encoder.encode_accessory(candidate)
        similarity = calculate_cosine_similarity(user_vector, accessory_vector)
        score = calculate_composite_score(
            similarity=similarity,
            margin_rate=candidate.margin_rate,
            alpha=active_alpha,
            beta=active_beta,
        )
        ranked_items.append(
            RankedAccessory(
                accessory=candidate,
                semantic_similarity=similarity,
                margin_rate=candidate.margin_rate,
                composite_score=score,
            )
        )

    # Sort descending by composite_score, then tie-break by margin_rate descending, then accessory id ascending
    ranked_items.sort(
        key=lambda item: (-item.composite_score, -item.margin_rate, item.accessory.id)
    )

    if top_k is not None:
        return ranked_items[:top_k]

    return ranked_items

