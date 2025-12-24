"""API package for LLM Serve Dashboard.

Contains FastAPI routers for health checks and control API endpoints.
"""

from dashboard.backend.api import health
from dashboard.backend.api import control

__all__ = ["health", "control"]
