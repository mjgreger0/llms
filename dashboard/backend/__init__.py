"""LLM Serve Dashboard Backend Package.

Centralized control plane for LLM cluster management.

Modules:
    api: FastAPI routers for health and control endpoints
    config: Configuration management via environment variables
    db: Database session management and models
    logging_config: Structured logging configuration
    middleware: Request middleware for logging, timing, and request IDs
    models: SQLAlchemy models and Pydantic schemas
    services: Business logic services
"""

__version__ = "0.1.0"
