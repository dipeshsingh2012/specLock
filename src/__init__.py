"""
SpecLock: Constrained Hybrid Retrieval & Zero-Error Compatibility Engine.

Two-stage recommendation pipeline:
- Stage 1: Deterministic bipartite graph pruning (NetworkX) guaranteeing 0% compatibility errors.
- Stage 2: Bi-encoder semantic ranking (Sentence-Transformers) with gross margin weighting.
"""

__version__ = "0.1.0"

