"""
FastAPI main application entry point for the SpecLock service.
Configures application lifespan, dependency initialization, and mounts routing modules.
"""

from contextlib import asynccontextmanager
from typing import AsyncGenerator, Dict
from fastapi import FastAPI, Depends, status
from fastapi.middleware.cors import CORSMiddleware

from api.endpoints import router, get_graph_engine
from api.schemas import HealthResponse, ErrorResponse
from graph.builder import build_graph, get_graph_summary
from graph.filter import InMemoryGraphEngine
from ranker.encoder import CatalogEmbeddingCache


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """
    Application lifespan context manager:
    Constructs the bipartite directed graph, initializes the in-memory
    compatibility engine, and pre-caches dense catalog embeddings once during startup.
    """
    graph = build_graph()
    engine = InMemoryGraphEngine(graph=graph)
    app.state.graph_engine = engine

    encoder = CatalogEmbeddingCache()
    encoder.precompute_catalog_embeddings(
        accessories=engine.get_all_accessories(),
        machines=engine.get_all_machines(),
    )
    app.state.encoder = encoder
    yield


tags_metadata = [
    {
        "name": "recommendations",
        "description": "Two-stage constrained hardware compatibility filtering and neural ranking.",
    },
    {
        "name": "system",
        "description": "System operational health checks, diagnostics, and catalog topology metrics.",
    },
]

app = FastAPI(
    title="SpecLock Recommendation Engine",
    version="0.1.0",
    description=(
        "Two-stage zero-error hardware compatibility recommendation engine "
        "combining deterministic graph pruning with neural semantic ranking."
    ),
    openapi_tags=tags_metadata,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    contact={
        "name": "Dipesh Singh",
        "url": "https://github.com/dipeshsingh2012/specLock",
    },
    license_info={
        "name": "MIT",
        "url": "https://opensource.org/licenses/MIT",
    },
    servers=[
        {
            "url": "/",
            "description": "Current Environment",
        },
    ],
    swagger_ui_parameters={
        "defaultModelsExpandDepth": 2,
        "docExpansion": "list",
        "filter": True,
        "showExtensions": True,
    },
    lifespan=lifespan,
)

# Enable CORS for Swagger UI and local development consumers
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount business recommendation endpoints strictly under versioned API prefix
app.include_router(router, prefix="/api/v1")


@app.get(
    "/",
    tags=["system"],
    operation_id="getRootInfo",
    summary="Service Metadata & Documentation Pointer",
)
async def get_root_info() -> Dict[str, str]:
    """Returns service metadata and interactive OpenAPI documentation link."""
    return {
        "service": "SpecLock",
        "version": "0.1.0",
        "docs_url": "/docs",
        "openapi_url": "/openapi.json",
    }


@app.get(
    "/health",
    response_model=HealthResponse,
    tags=["system"],
    operation_id="getSystemHealth",
    summary="Operational Service Health and Graph Diagnostics",
    responses={
        status.HTTP_200_OK: {
            "model": HealthResponse,
            "description": "System operational and graph topology statistics.",
        },
        status.HTTP_503_SERVICE_UNAVAILABLE: {
            "model": ErrorResponse,
            "description": "Graph compatibility engine is not initialized.",
        },
    },
)
async def get_health(
    engine: InMemoryGraphEngine = Depends(get_graph_engine),
) -> HealthResponse:
    """
    Root-level operational health probe returning runtime system status
    and live hardware catalog metrics.
    """
    summary = get_graph_summary(engine.graph)

    return HealthResponse(
        status="ok",
        brand=summary["brand"],
        total_machines=summary["machine_count"],
        total_accessories=summary["accessory_count"],
        total_specifications=summary["specification_count"],
    )


