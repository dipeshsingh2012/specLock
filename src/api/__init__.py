"""
SpecLock REST API package providing deterministic compatibility recommendations
and health diagnostics over HTTP.
"""

from api.main import app
from api.endpoints import router

__all__ = ["app", "router"]
