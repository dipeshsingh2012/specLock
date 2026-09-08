# ==============================================================================
# SpecLock Production Dockerfile (Optimized for GCP Cloud Run)
# - Base: Official Python 3.11 Debian Slim
# - Size optimization: CPU-only PyTorch wheels (~180MB vs ~2.8GB CUDA)
# - Latency optimization: Pre-baked sentence-transformers weights (zero-network boot)
# - Cloud Run compatibility: Dynamic $PORT binding, single-worker execution
# ==============================================================================

FROM python:3.11-slim

# Prevent Python from writing .pyc files and enable unbuffered stdout/stderr
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app/src \
    HF_HOME=/app/model_cache \
    PORT=8080

WORKDIR /app

# Install minimal system dependencies (curl for container health checks)
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# 1. Install lightweight CPU-only PyTorch first (drastically slims image from ~3.5GB to ~500MB)
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir "torch>=2.0.0" --index-url https://download.pytorch.org/whl/cpu

# 2. Install project dependencies from pyproject.toml
COPY pyproject.toml /app/
RUN pip install --no-cache-dir .

# 3. Pre-download sentence-transformers weights into image layer (eliminates cold starts)
COPY scripts/download_model.py /app/scripts/
RUN python3 /app/scripts/download_model.py "sentence-transformers/all-MiniLM-L6-v2"

# Enforce offline mode in production container runtime
ENV TRANSFORMERS_OFFLINE=1 \
    HF_HUB_OFFLINE=1

# 4. Copy application source code and hardware catalog
COPY src/ /app/src/
COPY data/ /app/data/

# Expose default Cloud Run port
EXPOSE 8080

# Container Health Check querying SpecLock's health endpoint
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:${PORT:-8080}/health || exit 1

# Launch production Uvicorn server: dynamic $PORT binding, 1 worker (optimal for Cloud Run container-level scaling)
CMD ["sh", "-c", "exec uvicorn api.main:app --host 0.0.0.0 --port ${PORT:-8080} --workers 1"]
