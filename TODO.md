# SpecLock: Enterprise Data Ingestion & Storage Roadmap (TODO)

This document outlines the architectural plan, schema designs, and step-by-step implementation tasks to upgrade SpecLock from the current local JSON feed (`data/raw/breville_catalog.json`) to an enterprise-grade **BigQuery ➔ PostgreSQL ➔ Redis** data pipeline.

---

## 1. Architectural Overview

```
[ PIM / ERP / OMS ] (Product Specs, Inventory, COGS)
         │
         ▼
┌─────────────────────────────────────────────────────────────┐
│ 1. DATA WAREHOUSE (Google BigQuery)                         │
│ - Scheduled dbt transformation models                       │
│ - Joins raw PIM specs with ERP margin rates & historical CTR│
│ - Nightly export to Cloud Storage (Parquet / JSONL)         │
└──────────────────────────────┬──────────────────────────────┘
                               │ Batch Sync (Airflow / Cloud Run)
                               ▼
┌─────────────────────────────────────────────────────────────┐
│ 2. OPERATIONAL DATABASE (PostgreSQL)                        │
│ - Normalized relational schema for products & constraints   │
│ - Source of truth for merchandising updates & audits        │
└──────────────────────────────┬──────────────────────────────┘
                               │ Startup / CDC Hydration
                               ▼
┌─────────────────────────────────────────────────────────────┐
│ 3. SERVING LAYER & REAL-TIME MASKING                        │
│ - SpecLock In-Memory Graph (NetworkX) for <50ms P99 latency │
│ - Redis Stock Availability Cache for real-time OOS masking  │
└─────────────────────────────────────────────────────────────┘
```

---

## 2. Component Specifications

### 2.1 BigQuery Batch Pipeline (`src/speclock/storage/bigquery.py`)
- [ ] **dbt Model Definition:**
  Create a materialized view `analytics_catalog.dim_hardware_compatibility` joining:
  - `pim_products` (SKU, title, description, category)
  - `pim_specifications` (collar_diameter, voltage, group_head_type)
  - `erp_financials` (unit_cost, retail_price, gross_margin_rate)
- [ ] **Batch Export Job:**
  Airflow / Cloud Composer DAG exporting daily snapshots to Cloud Storage:
  `gs://speclock-catalog-snapshots/dt={YYYY-MM-DD}/catalog.parquet`
- [ ] **BigQuery Extractor Client:**
  Implement `BigQueryCatalogProvider` utilizing `google-cloud-bigquery` with federated query / Arrow extraction for fast ingestion.

### 2.2 PostgreSQL Operational Catalog (`src/speclock/storage/postgres.py`)
- [ ] **Relational DDL:**
  ```sql
  CREATE TABLE machines (
      id VARCHAR(64) PRIMARY KEY,
      name VARCHAR(255) NOT NULL,
      sku VARCHAR(64) UNIQUE NOT NULL,
      series VARCHAR(64) NOT NULL,
      price NUMERIC(10, 2) NOT NULL,
      voltage VARCHAR(16) NOT NULL,
      collar_diameter VARCHAR(16) NOT NULL,
      group_head_type VARCHAR(32) NOT NULL,
      created_at TIMESTAMPTZ DEFAULT NOW()
  );

  CREATE TABLE accessories (
      id VARCHAR(64) PRIMARY KEY,
      name VARCHAR(255) NOT NULL,
      sku VARCHAR(64) UNIQUE NOT NULL,
      category VARCHAR(64) NOT NULL,
      price NUMERIC(10, 2) NOT NULL,
      margin_rate NUMERIC(5, 4) NOT NULL,
      description TEXT NOT NULL,
      created_at TIMESTAMPTZ DEFAULT NOW()
  );

  CREATE TABLE accessory_compatibility_rules (
      id SERIAL PRIMARY KEY,
      accessory_id VARCHAR(64) REFERENCES accessories(id) ON DELETE CASCADE,
      spec_type VARCHAR(32) NOT NULL,  -- e.g. "collar_diameter", "voltage", "series"
      spec_value VARCHAR(64) NOT NULL  -- e.g. "54mm", "120V", "universal"
  );
  ```
- [ ] **ORM & Connection Pooling:**
  Use `SQLAlchemy` (async) or `asyncpg` with a pooled connection layer (`pool_size=10`).
- [ ] **Postgres Provider:**
  Implement `PostgresCatalogProvider` implementing the `CatalogRepository` interface.

### 2.3 Redis Real-Time Inventory & Out-of-Stock Masking (`src/speclock/storage/redis.py`)
- [ ] **Problem Addressed:** Prevent recommending accessories that are physically compatible but currently out of stock in the user's regional warehouse.
- [ ] **Redis Key Schema:**
  - `stock:active_skus:{region_id}` ➔ Redis `SET` containing all currently available SKUs.
  - Or Redis Bitmap: `SETBIT stock:mask:{region_id} {sku_index} 1`
- [ ] **Real-Time Event Ingestion:**
  Kafka / Debezium CDC consumer listening to `warehouse.inventory_level_changed` and updating Redis in $<2\text{ ms}$.
- [ ] **Stage 1 Masking Integration:**
  After graph pruning returns candidate SKU IDs, perform an $O(1)$ set intersection with Redis active SKUs:
  $$\text{Final Candidates} = \text{GraphCandidates} \cap \text{InStockSKUs}$$

---

## 3. Ports & Adapters (Code Abstractions to Implement)

- [ ] **`src/speclock/storage/base.py`:**
  ```python
  from typing import Protocol, List, Set
  from speclock.graph.schema import MachineNode, AccessoryNode

  class CatalogRepository(Protocol):
      async def get_machines(self) -> List[MachineNode]: ...
      async def get_accessories(self) -> List[AccessoryNode]: ...

  class InventoryProvider(Protocol):
      async def get_in_stock_skus(self, region: str) -> Set[str]: ...
  ```
- [ ] **`src/speclock/storage/json_provider.py`:**
  Local implementation for testing and offline development (current active implementation).
- [ ] **`src/speclock/storage/factory.py`:**
  Factory reading `config.DATA_SOURCE` (`"json"`, `"postgres"`, `"bigquery"`) and instantiating the appropriate repository.

---

## 4. Migration & Rollout Checklist


---

## 5. Enterprise Graph Database: Neo4j Migration Blueprint

When catalog scale expands beyond 100,000 items, or when multi-tenant vendor catalogs require distributed concurrent writes and transactional ACID guarantees, migrate the in-memory NetworkX graph to an enterprise Neo4j cluster (or Neo4j AuraDB).

### 5.1 When to Trigger the Neo4j Migration
- **Catalog Scale:** Total active nodes exceed 100,000 or edge density exceeds 1,000,000 relationships.
- **Concurrent Merchandising Updates:** Multiple vendor portals / ERPs updating specs and fitment relationships simultaneously without taking down or restarting API pods.
- **Multi-Region Storefronts:** Deploying read-replicas in US-East, EU-Central, and AP-Southeast to ensure local $<15\text{ ms}$ graph lookups worldwide.

### 5.2 Labeled Property Graph Schema (Cypher DDL)

```cypher
// 1. Uniqueness Constraints & Indexes
CREATE CONSTRAINT machine_id_unique IF NOT EXISTS
FOR (m:Machine) REQUIRE m.id IS UNIQUE;

CREATE CONSTRAINT accessory_id_unique IF NOT EXISTS
FOR (a:Accessory) REQUIRE a.id IS UNIQUE;

CREATE CONSTRAINT spec_key_unique IF NOT EXISTS
FOR (s:Specification) REQUIRE (s.spec_type, s.spec_value) IS UNIQUE;

CREATE INDEX machine_sku_idx IF NOT EXISTS FOR (m:Machine) ON (m.sku);
CREATE INDEX accessory_sku_idx IF NOT EXISTS FOR (a:Accessory) ON (a.sku);

// 2. Sample Ingestion Cypher
MERGE (m:Machine {id: "M_BES870XL"})
SET m.name = "Barista Express", m.sku = "BES870XL", m.price = 749.95, m.series = "Barista";

MERGE (s1:Specification {spec_type: "collar_diameter", spec_value: "54mm"})
MERGE (s2:Specification {spec_type: "voltage", spec_value: "120V"})

MERGE (m)-[:REQUIRES_SPEC]->(s1)
MERGE (m)-[:REQUIRES_SPEC]->(s2);

MERGE (a:Accessory {id: "A_FUNNEL_MAG_54"})
SET a.name = "54mm Magnetic Dosing Funnel", a.sku = "ACC-DF-54-MAG", a.margin_rate = 0.62, a.price = 24.95;

MERGE (s_univ:Specification {spec_type: "voltage", spec_value: "universal"})
MERGE (a)-[:FITS_SPEC]->(s1)
MERGE (a)-[:FITS_SPEC]->(s_univ);
```

### 5.3 Stage 1 Cypher Deterministic Pruning Query
In Neo4j, deterministic pruning executes in a single declarative Cypher query:

```cypher
MATCH (m:Machine {id: $machine_id})-[:REQUIRES_SPEC]->(req:Specification)
WITH m, collect(req) AS required_specs

MATCH (a:Accessory)
// Enforce that every non-universal fit rule on the accessory matches one of the machine's required specs
WHERE ALL(fit_spec IN [(a)-[:FITS_SPEC]->(s) | s]
          WHERE fit_spec.spec_value = "universal" 
             OR fit_spec IN required_specs)
RETURN a.id AS candidate_id, a.name AS name, a.margin_rate AS margin_rate, a.price AS price;
```

### 5.4 Neo4j Migration Checklist
1. [ ] Add `neo4j>=5.18.0` to `pyproject.toml` under `[project.optional-dependencies] graph-enterprise`.
2. [ ] Add `NEO4J_URI`, `NEO4J_USER`, and `NEO4J_PASSWORD` to `src/config.py`.
3. [ ] Implement `src/graph/neo4j_engine.py` adhering to the `GraphEngine` protocol.
4. [ ] Create bulk loader script `scripts/seed_neo4j.py` to stream JSON / Postgres catalog records into Neo4j using APOC or batched Cypher unwinds.
5. [ ] Set `GRAPH_BACKEND=neo4j` in `.env` and verify all tests in `tests/test_graph_filter.py` pass identically with 0% fitment error.


