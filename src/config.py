"""
SpecLock: Central Configuration & Settings
"""

from pathlib import Path
import os
from pydantic import BaseModel, Field


class Settings(BaseModel):
    # Project Paths
    project_root: Path = Field(default_factory=lambda: Path(__file__).resolve().parent.parent)

    @property
    def raw_catalog_path(self) -> Path:
        return self.project_root / "data" / "raw" / "breville_catalog.json"

    # Stage 2 Ranker Weights (alpha: semantic similarity, beta: margin contribution)
    default_alpha: float = float(os.getenv("SPECLOCK_ALPHA", "0.7"))
    default_beta: float = float(os.getenv("SPECLOCK_BETA", "0.3"))

    # Neural Embedding Model
    model_name: str = os.getenv("SPECLOCK_MODEL", "sentence-transformers/all-MiniLM-L6-v2")
    embedding_dim: int = 384

    # Performance & SLA
    sla_max_latency_ms: float = 50.0

    # Primary Physical Specification Key (e.g. collar_diameter for espresso, tray_size for ovens, mount_type for cameras)
    primary_spec_key: str = os.getenv("SPECLOCK_PRIMARY_SPEC", "collar_diameter")

    # Data Source (see TODO.md for postgres / bigquery roadmap)
    data_source: str = os.getenv("SPECLOCK_DATA_SOURCE", "json")


settings = Settings()

