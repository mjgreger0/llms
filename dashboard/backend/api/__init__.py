"""API package for LLM Serve Dashboard.

Contains FastAPI routers for health checks, control API endpoints, and WebSocket handlers.
"""

from dashboard.backend.api import health
from dashboard.backend.api import control
from dashboard.backend.api import websocket

__all__ = ["health", "control", "websocket"]
