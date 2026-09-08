#!/usr/bin/env python3
"""
Pre-downloads and caches the sentence-transformers model weights during Docker build.
Ensures zero-network cold starts and immunity to external outages in production.
"""

import os
import sys
from sentence_transformers import SentenceTransformer


def download_model(model_name: str = "sentence-transformers/all-MiniLM-L6-v2") -> None:
    cache_dir = os.getenv("HF_HOME", "/app/model_cache")
    print(f"--> Pre-downloading model '{model_name}' into '{cache_dir}'...")
    SentenceTransformer(model_name, cache_folder=cache_dir)
    print(f"--> Successfully cached '{model_name}'.")


if __name__ == "__main__":
    name = sys.argv[1] if len(sys.argv) > 1 else "sentence-transformers/all-MiniLM-L6-v2"
    download_model(name)
