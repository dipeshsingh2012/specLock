"""
FastAPI APIRouter defining SpecLock compatibility and system health endpoints:
- GET /health: Graph topology statistics and system health
- GET /recommend/compatible: Stage 1 deterministic constraint filtering and Stage 2 neural ranking
"""

from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, Query, Request, status

from api.schemas import AccessoryItem, RecommendationResponse, ErrorResponse
from config import settings
from graph.base import FilterResult
from graph.filter import InMemoryGraphEngine
from ranker.encoder import CatalogEmbeddingCache
from ranker.scoring import rank_compatible_accessories, RankedAccessory


router = APIRouter(tags=["recommendations"])


def get_graph_engine(request: Request) -> InMemoryGraphEngine:
    """
    Dependency provider to access the singleton InMemoryGraphEngine
    initialized during application lifespan startup.
    """
    engine: Optional[InMemoryGraphEngine] = getattr(request.app.state, "graph_engine", None)
    if engine is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Graph compatibility engine is not initialized.",
        )
    return engine


def get_encoder(request: Request) -> CatalogEmbeddingCache:
    """
    Dependency provider to access the singleton CatalogEmbeddingCache
    initialized during application lifespan startup.
    """
    encoder: Optional[CatalogEmbeddingCache] = getattr(request.app.state, "encoder", None)
    if encoder is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Embedding ranking encoder is not initialized.",
        )
    return encoder


@router.get(
    "/recommend/compatible",
    response_model=RecommendationResponse,
    operation_id="getCompatibleRecommendations",
    summary="Two-Stage Hardware Fitment Filtering and Neural Ranking",
    responses={
        status.HTTP_200_OK: {
            "model": RecommendationResponse,
            "description": "Compatibility constraints evaluated and accessories ranked successfully.",
        },
        status.HTTP_404_NOT_FOUND: {
            "model": ErrorResponse,
            "description": "Specified machine_id not found in compatibility graph.",
        },
        status.HTTP_503_SERVICE_UNAVAILABLE: {
            "model": ErrorResponse,
            "description": "Graph compatibility engine or ranking encoder is not initialized.",
        },
    },
)
async def get_compatible_recommendations(
    machine_id: str = Query(
        ...,
        description="Identifier of the target machine (e.g., 'M_BES870XL')",
        examples=["M_BES870XL"],
    ),
    query: Optional[str] = Query(
        None,
        description="Optional free-form user search intent query applied during Stage 2 semantic ranking",
    ),
    target_voltage: Optional[str] = Query(
        None,
        description="Regional checkout voltage override (e.g., '120V', '240V')",
    ),
    category: Optional[str] = Query(
        None,
        description="Optional product taxonomy category filter (e.g., 'portafilters')",
    ),
    primary_spec_key: Optional[str] = Query(
        None,
        description="Primary physical specification key (defaults to settings.primary_spec_key)",
    ),
    top_k: Optional[int] = Query(
        None,
        ge=1,
        description="Maximum number of top-ranked recommendations to return",
    ),
    alpha: Optional[float] = Query(
        None,
        ge=0.0,
        le=1.0,
        description="Stage 2 semantic relevance weight (default 0.7)",
    ),
    beta: Optional[float] = Query(
        None,
        ge=0.0,
        le=1.0,
        description="Stage 2 margin weight (default 0.3)",
    ),
    stage2: bool = Query(
        True,
        description="Whether to execute Stage 2 ranking (True) or return raw unranked Stage 1 candidates (False)",
    ),
    engine: InMemoryGraphEngine = Depends(get_graph_engine),
    encoder: CatalogEmbeddingCache = Depends(get_encoder),
) -> RecommendationResponse:
    """
    Executes Two-Stage Hybrid Recommendation:
    1. Stage 1: Deterministic graph traversal returning 100% physically and electrically
       compatible accessories for the specified machine.
    2. Stage 2: Probabilistic neural bi-encoder ranking with economic gross margin weighting.
    """
    try:
        filter_result: FilterResult = engine.filter_compatible_accessories(
            machine_id=machine_id,
            target_voltage=target_voltage,
            category=category,
            primary_spec_key=primary_spec_key,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc

    target_machine = engine.get_machine(machine_id)
    accessory_items: List[AccessoryItem] = []

    active_alpha: Optional[float] = None
    active_beta: Optional[float] = None

    if stage2:
        active_alpha = alpha if alpha is not None else settings.default_alpha
        active_beta = beta if beta is not None else settings.default_beta

        if filter_result.compatible_accessories:
            ranked_accessories: List[RankedAccessory] = rank_compatible_accessories(
                machine=target_machine,
                candidates=filter_result.compatible_accessories,
                query=query,
                top_k=top_k,
                alpha=active_alpha,
                beta=active_beta,
                encoder=encoder,
            )

            for ranked in ranked_accessories:
                acc = ranked.accessory
                item = AccessoryItem(
                    id=acc.id,
                    name=acc.name,
                    sku=acc.sku,
                    category=acc.category,
                    price=acc.price,
                    margin_rate=acc.margin_rate,
                    fits=acc.fits,
                    description=acc.description,
                    semantic_similarity=round(ranked.semantic_similarity, 4),
                    composite_score=round(ranked.composite_score, 4),
                )
                accessory_items.append(item)
    else:
        candidates = filter_result.compatible_accessories
        if top_k is not None:
            candidates = candidates[:top_k]

        for accessory in candidates:
            item = AccessoryItem(
                id=accessory.id,
                name=accessory.name,
                sku=accessory.sku,
                category=accessory.category,
                price=accessory.price,
                margin_rate=accessory.margin_rate,
                fits=accessory.fits,
                description=accessory.description,
            )
            accessory_items.append(item)

    return RecommendationResponse(
        machine_id=filter_result.machine_id,
        target_voltage=target_voltage,
        category=category,
        query=query,
        alpha=active_alpha,
        beta=active_beta,
        total_compatible=filter_result.total_passed,
        total_evaluated=filter_result.total_evaluated,
        total_rejected=filter_result.total_rejected,
        latency_ms=filter_result.latency_ms,
        items=accessory_items,
    )

