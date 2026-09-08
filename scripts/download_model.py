#!/usr/bin/env python3
"""
Pre-downloads and caches the sentence-transformers model weights during Docker build.
Ensures zero-network cold starts and immunity to external outages in production.
"""

import os
import sys
from typing import Optional
from sentence_transformers import SentenceTransformer


def download_model(
    model_name: str = "sentence-transformers/all-MiniLM-L6-v2",
    target_dir: Optional[str] = None,
) -> str:
    target_path = target_dir or os.getenv("SPECLOCK_MODEL_DIR", "/app/models/all-MiniLM-L6-v2")
    print(f"--> Pre-downloading model '{model_name}' and saving to '{target_path}'...")
    os.makedirs(target_path, exist_ok=True)
    model = SentenceTransformer(model_name)
    model.save(target_path)
    print(f"--> Successfully saved model to '{target_path}'.")
    return target_path


if __name__ == "__main__":
    name = sys.argv[1] if len(sys.argv) > 1 else "sentence-transformers/all-MiniLM-L6-v2"
    target = sys.argv[2] if len(sys.argv) > 2 else None
    download_model(name, target)
