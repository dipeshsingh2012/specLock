# SpecLock: Constrained Hybrid Retrieval & Zero-Error Compatibility Engine

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.110+-009688.svg?logo=fastapi)](https://fastapi.tiangolo.com)
[![OpenAPI 3.1](https://img.shields.io/badge/OpenAPI-3.1.0-6BA539.svg?logo=openapi-initiative)](http://localhost:8000/docs)
[![Swagger UI](https://img.shields.io/badge/Swagger-UI-85EA2D.svg?logo=swagger)](http://localhost:8000/docs)
[![NetworkX](https://img.shields.io/badge/NetworkX-3.1+-orange.svg)](https://networkx.org/)
[![Coverage](https://img.shields.io/badge/coverage-100%25-brightgreen.svg)](#)
[![Fitment Accuracy](https://img.shields.io/badge/Fitment%20Accuracy-100%25%20Guaranteed-success.svg)](#)
[![P99 Latency](https://img.shields.io/badge/P99%20Latency-%3C50ms-brightgreen.svg)](#)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

```
+-----------------------------------------------------------------------------------+
| Architecture: Two-Stage Hybrid Recommendation Pipeline                            |
| Target Metric: 100% Fitment Accuracy (Zero Compatibility Returns) + Sub-50ms P99  |
| Stack: Python 3.11+, NetworkX, Sentence-Transformers, FastAPI, OpenAPI 3.1        |
+-----------------------------------------------------------------------------------+
```

---

## 1. Executive Summary

Standard collaborative filtering and vector search algorithms operate probabilistically. In high-ticket consumer hardware e-commerce (such as Breville espresso machines and precision kitchen hardware), pure machine learning causes costly return rates by recommending physically incompatible accessories (e.g., suggesting a 58 mm portafilter for a 54 mm group head).

**SpecLock** implements a **Two-Stage Constrained Hybrid Recommender**:

1. **Stage 1 (Deterministic Graph Pruning):** Filters catalog candidates using strict bipartite graph relations (physical collar diameter, series, voltage) to guarantee **0% false-positive compatibility**.
2. **Stage 2 (Probabilistic Semantic Ranker):** Leverages a bi-encoder neural ranking model (`sentence-transformers/all-MiniLM-L6-v2`) to score and personalize the valid candidate pool based on user intent, basket context, and gross margin weights.

---

## 2. System Architecture & Flow

```
[ Cart Event / User Query ]
            │
            ▼
[ Ingestion & Context Parser ] ── (Machine SKU, User Persona, Regional Spec)
            │
            ▼
┌─────────────────────────────────────────────────────────────┐
│ STAGE 1: Deterministic Constraint Masking (Graph Engine)   │
│ - Traverse: (Machine)-[:REQUIRES_SPEC]->(Spec)<-[:FITS]-(Acc)
│ - Enforce: Exact physical diameter, series, voltage        │
│ - Output: Hard-Filtered Candidate Subgraph (Zero Incompat) │
└─────────────────────────────┬───────────────────────────────┘
                              │ Valid IDs Only
                              ▼
┌─────────────────────────────────────────────────────────────┐
│ STAGE 2: Probabilistic Semantic Ranking (Vector Engine)     │
│ - Embeddings: Sentence-Transformers (Context + Item Docs)   │
│ - Scoring: Cosine Similarity + Business Margin Weights     │
│ - Output: Top-K Ranked Compatible Recommendations           │
└─────────────────────────────┬───────────────────────────────┘
                              │
                              ▼
[ Fast JSON Delivery (<50ms P99) ] ──> Storefront / Cart Drawer
```

---

## 3. Data Schema & Graph Formulation

### Nodes
* **`Machine`** (`id`, `name`, `sku`, `price`, `voltage`, `specs`, `description`)
* **`Accessory`** (`id`, `name`, `sku`, `category`, `price`, `margin_rate`, `fits`, `description`)
* **`Specification`** (`type`, `value`) *(e.g., `type: "collar_diameter"`, `value: "54mm"`)*

### Edges
* `(:Machine)-[:REQUIRES_SPEC]->(:Specification)`
* `(:Accessory)-[:FITS_SPEC]->(:Specification)`

---

## 4. Scoring Objective Function

The stage 2 ranker combines dense vector semantic similarity with business unit economics:

$$\text{Score}(u, i) = \alpha \cdot \text{CosineSim}(\mathbf{e}_u, \mathbf{e}_i) + \beta \cdot \text{MarginRate}(i)$$

Where:
* $\mathbf{e}_u$ is the dense embedding of the user's search query or the target machine's context (when query is absent).
* $\mathbf{e}_i$ is the pre-computed embedding of candidate accessory $i$.
* $\alpha$ balances contextual relevance (default: $0.7$).
* $\beta$ prioritizes catalog gross margin contribution (default: $0.3$).

---

## 5. OpenAPI 3.1 & Swagger Documentation

SpecLock includes native **OpenAPI 3.1** specification and interactive **Swagger UI** / **ReDoc** documentation:

* **Interactive Swagger UI**: [`http://localhost:8000/docs`](http://localhost:8000/docs)
* **ReDoc Documentation**: [`http://localhost:8000/redoc`](http://localhost:8000/redoc)
* **OpenAPI 3.1 Schema (JSON)**: [`http://localhost:8000/openapi.json`](http://localhost:8000/openapi.json)

### Static Specification Export
Export the static OpenAPI specification to `openapi.json` and `openapi.yaml` without starting the server:

```bash
python scripts/export_openapi.py
```

---

## 6. API Reference

### `GET /api/v1/recommend/compatible`
Executes two-stage recommendation: deterministic graph filtering followed by semantic + gross margin ranking.

#### Query Parameters
| Parameter | Type | Required | Default | Description |
| :--- | :--- | :--- | :--- | :--- |
| `machine_id` | `string` | **Yes** | — | Target machine identifier (e.g., `M_BES870XL`) |
| `query` | `string` | No | `null` | Search intent or product query for Stage 2 semantic ranking |
| `target_voltage` | `string` | No | `null` | Regional checkout voltage override (e.g., `120V`, `240V`) |
| `category` | `string` | No | `null` | Taxonomy category filter (e.g., `portafilters`) |
| `primary_spec_key`| `string` | No | `collar_diameter` | Primary physical specification key |
| `top_k` | `integer`| No | `null` | Maximum number of ranked recommendations to return |
| `alpha` | `float` | No | `0.7` | Semantic relevance weight ($0.0 \le \alpha \le 1.0$) |
| `beta` | `float` | No | `0.3` | Gross margin rate weight ($0.0 \le \beta \le 1.0$) |
| `stage2` | `boolean`| No | `true` | Set to `false` to return raw unranked Stage 1 candidates |

#### Sample Request (Search Intent Query)
```bash
curl -X GET "http://localhost:8000/api/v1/recommend/compatible?machine_id=M_BES870XL&query=dosing%20funnel&top_k=2"
```

#### Sample Response
```json
{
  "machine_id": "M_BES870XL",
  "target_voltage": null,
  "category": null,
  "query": "dosing funnel",
  "alpha": 0.7,
  "beta": 0.3,
  "total_compatible": 28,
  "total_evaluated": 29,
  "total_rejected": 1,
  "latency_ms": 0.068,
  "items": [
    {
      "id": "A_FUNNEL_PRESS_54",
      "name": "54mm Grinder Trigger Dosing Funnel",
      "sku": "ACC-DF-54-TRIG",
      "category": "workflow_tools",
      "price": 29.95,
      "margin_rate": 0.58,
      "fits": {
        "collar_diameter": "54mm",
        "voltage": "universal"
      },
      "description": "Hands-free dosing funnel that activates the integrated grinder cradle on Barista Express and Barista Pro 54mm machines.",
      "semantic_similarity": 0.6125,
      "composite_score": 0.6028
    }
  ]
}
```

### `GET /health`
Operational health probe returning runtime system status and live catalog topology counts:
```bash
curl -X GET "http://localhost:8000/health"
```

---

## 7. Interactive Graph Visualizer

Open [`graph_visualization.html`](graph_visualization.html) in any web browser to explore the bipartite knowledge graph:
* **Blue Nodes**: Espresso Machines
* **Purple Nodes**: Hardware Specifications (Collar diameters, voltages, series)
* **Green Nodes**: Accessories

---

## 8. Repository Structure

```text
specLock/
├── data/
│   └── raw/
│       └── breville_catalog.json    # Catalog feed with machines, accessories & constraints
├── scripts/
│   └── export_openapi.py            # Static OpenAPI 3.1 JSON/YAML exporter
├── src/
│   ├── __init__.py
│   ├── config.py                    # Global configuration & ranking hyperparameters
│   ├── api/
│   │   ├── __init__.py
│   │   ├── endpoints.py             # GET /api/v1/recommend/compatible endpoint
│   │   ├── main.py                  # FastAPI entry point, lifespan pre-caching, docs
│   │   └── schemas.py               # Pydantic v2 schemas with OpenAPI examples
│   ├── graph/
│   │   ├── __init__.py
│   │   ├── base.py                  # GraphEngine protocol & FilterResult dataclass
│   │   ├── builder.py               # NetworkX bipartite graph constructor
│   │   ├── filter.py                # Deterministic constraint pruning engine
│   │   └── schema.py                # Node & catalog data models
│   └── ranker/
│       ├── __init__.py
│       ├── encoder.py               # Dense vector embedding cache (Sentence-Transformers)
│       └── scoring.py               # Cosine similarity & composite margin scoring
├── tests/
│   ├── conftest.py                  # Pytest fixtures & session catalog initialization
│   ├── test_config.py               # Configuration tests
│   ├── api/
│   │   ├── conftest.py              # TestClient with lifespan management
│   │   ├── test_endpoints.py        # HTTP API integration tests & ranking assertions
│   │   ├── test_main.py             # Swagger UI, ReDoc, OpenAPI schema, lifespan tests
│   │   └── test_schemas.py          # Schema bounds, validations, OpenAPI examples
│   ├── graph/
│   │   ├── test_builder.py          # Bipartite topology, edge directions, summary tests
│   │   ├── test_filter.py           # 0% fit error assertion, voltage/diameter isolation
│   │   └── test_schema.py           # Node validation & catalog loader tests
│   └── ranker/
│       ├── test_encoder.py          # Embedding normalization & cache tests
│       └── test_scoring.py          # Cosine similarity, margin weighting, tie-breaking
├── graph_visualization.html         # Interactive vis-network graph visualization
├── openapi.json                     # Exported OpenAPI 3.1 specification (JSON)
├── openapi.yaml                     # Exported OpenAPI 3.1 specification (YAML)
├── pyproject.toml                   # Project metadata, dependencies & pytest coverage config
├── TODO.md                          # Enterprise data ingestion roadmap (BigQuery, Postgres, Redis)
└── README.md
```

---

## 9. Quick Start

### Installation

```bash
# Clone the repository
git clone https://github.com/dipeshsingh2012/specLock.git
cd specLock

# Create virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install dependencies in editable mode
pip install -e ".[dev]"
```

### Run Tests & Coverage
Enforces 100% statement and branch coverage:
```bash
pytest tests/ -v
```

### Start API Server
```bash
PYTHONPATH=src uvicorn api.main:app --reload --port 8000
```
Then visit [`http://localhost:8000/docs`](http://localhost:8000/docs) in your browser for the interactive Swagger UI.

---

## 🤝 Contributing & Conventional Commits

This repository enforces the [Conventional Commits v1.0.0](https://www.conventionalcommits.org/en/v1.0.0/) specification for all commits (`<type>(<scope>): <description>`).

### Setup Local Git Hooks
Enable automatic commit message linting via the repository's native git hook:
```bash
git config core.hooksPath .githooks
```
Or via the `pre-commit` framework:
```bash
pip install -e ".[dev]"
pre-commit install --hook-type commit-msg
```

See [CONTRIBUTING.md](CONTRIBUTING.md) for full guidelines, allowed types, and SpecLock-specific scopes (`api`, `graph`, `ranker`, `catalog`, `config`, `deps`, `tests`, `docs`).

