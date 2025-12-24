"""LLM Serve Dashboard - FastAPI Application Entry Point."""

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from dashboard.backend.config import get_settings
from dashboard.backend.db.session import init_db, close_db
from dashboard.backend.logging_config import configure_logging, get_logger
from dashboard.backend.middleware import (
    RequestContextMiddleware,
    LoggingMiddleware,
    TimingMiddleware,
)
from dashboard.backend.api.health import router as health_router
from dashboard.backend.api.control import router as control_router
from dashboard.backend.api.websocket import router as websocket_router
from dashboard.backend.services import cluster_state, ui_manager


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan context manager."""
    settings = get_settings()
    logger = get_logger(__name__)

    # Startup
    configure_logging()
    logger.info("application_starting", version=settings.app_version)
    init_db()
    logger.info("database_initialized")

    # Set up UI update callback from ClusterState to UIManager
    cluster_state.set_ui_update_callback(ui_manager.broadcast_update)
    logger.info("ui_update_callback_configured")

    yield

    # Shutdown
    logger.info("application_shutting_down")
    await close_db()
    logger.info("database_closed")


settings = get_settings()

app = FastAPI(
    title=settings.app_name,
    description="Centralized control plane for LLM cluster management",
    version=settings.app_version,
    lifespan=lifespan,
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.get_allowed_origins(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Custom middleware (order matters - they execute in reverse order)
app.add_middleware(TimingMiddleware)
app.add_middleware(LoggingMiddleware)
app.add_middleware(RequestContextMiddleware)

# Include routers
app.include_router(health_router)  # /health
app.include_router(control_router)  # /api/*
app.include_router(websocket_router)  # /ws/*

# Mount static files if exists
static_path = Path(__file__).parent.parent / "static"
if static_path.exists():
    app.mount("/", StaticFiles(directory=str(static_path), html=True), name="static")
